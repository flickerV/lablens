from __future__ import annotations

import io
import logging
import re
import unicodedata
from typing import Any, BinaryIO, Dict, List, Optional, Tuple

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None

try:
    import fitz
except ImportError:  # pragma: no cover
    fitz = None

try:
    import pytesseract
except ImportError:  # pragma: no cover
    pytesseract = None

try:
    from pdf2image import convert_from_bytes
except ImportError:  # pragma: no cover
    convert_from_bytes = None

try:
    from PyPDF2 import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None

from config import (
    ABSOLUTE_COUNT_FIELDS,
    DEFAULT_REPORT_TYPE,
    OVERALL_BANNERS,
    PARAMETERS,
    REPORT_TYPES,
    SEVERITY_RANK,
)
from rules import RULES


logger = logging.getLogger(__name__)


def normalize_sex(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"male", "female"}:
        return normalized
    return None


def _widen_for_child(low: float, high: float, age: Optional[float]) -> Tuple[float, float]:
    if age is None or age >= 12:
        return low, high
    spread = high - low
    widen_by = spread * 0.08
    return low - widen_by, high + widen_by


def get_parameters(report_type: str) -> Dict[str, Dict[str, Any]]:
    return REPORT_TYPES.get(report_type, REPORT_TYPES[DEFAULT_REPORT_TYPE])["parameters"]


def get_reference_range(metric: str, sex: Optional[str], age: Optional[float], report_type: str = DEFAULT_REPORT_TYPE) -> Dict[str, Any]:
    parameters = get_parameters(report_type)
    definitions = parameters[metric]["ranges"]
    normalized_sex = normalize_sex(sex)

    matched = None
    for ref in definitions:
        if ref.sex is None:
            matched = ref
            break
        if ref.sex == normalized_sex:
            matched = ref
            break

    if matched is None:
        matched = definitions[0]

    low, high = _widen_for_child(matched.low, matched.high, age)
    return {"low": round(low, 2), "high": round(high, 2), "unit": matched.unit}


def normalize_numeric_inputs(values: Dict[str, Any], report_type: str = DEFAULT_REPORT_TYPE) -> Dict[str, Any]:
    parameters = get_parameters(report_type)
    normalized = dict(values)
    for field in parameters:
        raw = values.get(field)
        if raw in (None, ""):
            normalized[field] = None
            continue
        number = float(raw)
        if field in ABSOLUTE_COUNT_FIELDS and number < 1000:
            number = number * 1000.0
        normalized[field] = round(number, 2)
    return normalized


def classify_value(value: Optional[float], low: float, high: float) -> str:
    if value is None:
        return "missing"
    if value < low:
        return "low"
    if value > high:
        return "high"
    return "normal"


def deviation_score(value: Optional[float], low: float, high: float) -> float:
    if value is None:
        return 0.0
    if value < low:
        return (low - value) / max(low, 1e-6)
    if value > high:
        return (value - high) / max(high, 1e-6)
    return 0.0


def evaluate_parameters(values: Dict[str, Any], age: Optional[float], sex: Optional[str], report_type: str = DEFAULT_REPORT_TYPE) -> Dict[str, Dict[str, Any]]:
    parameters = get_parameters(report_type)
    results: Dict[str, Dict[str, Any]] = {}
    for key, definition in parameters.items():
        reference = get_reference_range(key, sex=sex, age=age, report_type=report_type)
        value = values.get(key)
        status = classify_value(value, reference["low"], reference["high"])
        results[key] = {
            "key": key,
            "label": definition["label"],
            "group": definition["group"],
            "unit": definition["unit"],
            "display_unit": definition.get("display_unit", definition["unit"]),
            "display_divisor": definition.get("display_divisor", 1.0),
            "value": value,
            "status": status,
            "reference_range": reference,
            "deviation": deviation_score(value, reference["low"], reference["high"]),
        }
    return results


def _condition_matches(condition: Dict[str, Any], parameter_results: Dict[str, Dict[str, Any]]) -> bool:
    metric = condition["metric"]
    expected_status = condition["status"]
    if metric not in parameter_results:
        return False
    return parameter_results[metric]["status"] == expected_status


def detect_patterns(parameter_results: Dict[str, Dict[str, Any]], report_type: str = DEFAULT_REPORT_TYPE) -> List[Dict[str, Any]]:
    patterns: List[Dict[str, Any]] = []
    seen_ids: set = set()

    for rule in RULES:
        if rule.get("report_type", "cbc") != report_type:
            continue

        matched = False
        if "conditions" in rule:
            matched = all(_condition_matches(item, parameter_results) for item in rule["conditions"])
        elif "conditions_any" in rule:
            matched = any(_condition_matches(item, parameter_results) for item in rule["conditions_any"])

        if matched:
            rule_id = rule["id"]
            # Deduplicate: skip more generic rules if a specific rule already matched on the same metrics
            if rule_id == "platelet_disorder" and ("thrombocytopenia" in seen_ids or "thrombocytosis" in seen_ids):
                continue
            if rule_id == "possible_infection" and "leukocytosis_bacterial" in seen_ids:
                continue
            if rule_id == "microcytic_anemia" and "microcytic_hypochromic_anemia" in seen_ids:
                continue
            if rule_id == "prediabetes_pattern" and "diabetes_pattern" in seen_ids:
                continue
            if rule_id == "elevated_hba1c" and ("diabetes_pattern" in seen_ids or "prediabetes_pattern" in seen_ids):
                continue
            if rule_id == "isolated_ldl_elevation" and "atherogenic_dyslipidemia" in seen_ids:
                continue
            if rule_id == "isolated_hyperbilirubinemia" and "cholestatic_pattern" in seen_ids:
                continue
            if rule_id == "mild_alt_elevation" and "hepatocellular_pattern" in seen_ids:
                continue
            if rule_id == "isolated_urea_elevation" and "renal_impairment_pattern" in seen_ids:
                continue

            seen_ids.add(rule_id)
            patterns.append(
                {
                    "id": rule_id,
                    "name": rule["name"],
                    "explanation": rule["explanation"],
                    "simple_explanation": rule["simple_explanation"],
                    "possible_causes": list(rule["possible_causes"]),
                    "actions": list(rule["actions"]),
                    "severity": rule["severity"],
                }
            )

    return sorted(patterns, key=lambda item: SEVERITY_RANK[item["severity"]], reverse=True)


def _overall_status_from_abnormalities(parameter_results: Dict[str, Dict[str, Any]], patterns: List[Dict[str, Any]]) -> str:
    abnormal = [item for item in parameter_results.values() if item["status"] in {"low", "high"}]
    if not abnormal and not patterns:
        return "Normal"

    count = len(abnormal)
    max_deviation = max((item["deviation"] for item in abnormal), default=0.0)
    max_pattern = max((SEVERITY_RANK[item["severity"]] for item in patterns), default=0)

    if count >= 4 or max_deviation >= 0.35 or max_pattern >= 3:
        return "Significant Concern"
    if count >= 2 or max_deviation >= 0.18 or max_pattern >= 2:
        return "Moderate Abnormality"
    return "Mild Abnormality"


def _severity_statement(overall_status: str) -> str:
    if overall_status == "Normal":
        return "This appears to be within the expected reference range overall."
    if overall_status == "Mild Abnormality":
        return "This appears to be a mild abnormality and should be reviewed in clinical context."
    if overall_status == "Moderate Abnormality":
        return "This appears to be a moderate abnormality and should be evaluated further."
    return "This appears to be a significant concern and timely medical review is recommended."


def build_clinical_summary(parameter_results: Dict[str, Dict[str, Any]], patterns: List[Dict[str, Any]], overall_status: str, report_type: str = DEFAULT_REPORT_TYPE) -> Dict[str, Any]:
    report_label = REPORT_TYPES.get(report_type, REPORT_TYPES[DEFAULT_REPORT_TYPE])["label"]
    abnormal_labels = [item["label"] for item in parameter_results.values() if item["status"] in {"low", "high"}]
    lead_pattern = patterns[0] if patterns else None

    if lead_pattern:
        overview = f"Your {report_label} shows a pattern consistent with {lead_pattern['name']}."
        explanation = lead_pattern["simple_explanation"]
        possible_causes = lead_pattern["possible_causes"]
        actions = lead_pattern["actions"]
        for secondary in patterns[1:3]:
            for action in secondary["actions"]:
                if action not in actions:
                    actions.append(action)
    elif abnormal_labels:
        overview = f"Your {report_label} shows abnormalities involving {', '.join(abnormal_labels[:4])}."
        explanation = "Some values are outside the expected range, which may reflect a temporary change or an underlying medical issue."
        possible_causes = [
            "Recent illness or inflammation",
            "Nutritional or lifestyle factors",
            "Individual variation that may need follow-up",
        ]
        actions = [
            "Review these results with your doctor.",
            "Compare with prior results if available.",
            "Repeat testing if clinically advised.",
        ]
    else:
        overview = f"Your {report_label} is broadly within the expected reference ranges."
        explanation = "The measured values appear generally balanced for the provided age and biological sex."
        possible_causes = ["No major pattern abnormalities were detected."]
        actions = [
            "Maintain routine preventive care.",
            "Continue a balanced diet and hydration.",
            "Follow your clinician's advice if symptoms are present despite normal results.",
        ]

    return {
        "overview": overview,
        "explanation": explanation,
        "possible_causes": possible_causes,
        "what_you_can_do": actions,
        "severity_statement": _severity_statement(overall_status),
    }


def analyze_report(payload: Dict[str, Any], report_type: str = DEFAULT_REPORT_TYPE) -> Dict[str, Any]:
    if report_type not in REPORT_TYPES:
        report_type = DEFAULT_REPORT_TYPE
    normalized = normalize_numeric_inputs(payload, report_type=report_type)
    age = normalized.get("age")
    sex = normalized.get("sex")
    parameter_results = evaluate_parameters(normalized, age=age, sex=sex, report_type=report_type)
    patterns = detect_patterns(parameter_results, report_type=report_type)
    overall_status = _overall_status_from_abnormalities(parameter_results, patterns)
    summary = build_clinical_summary(parameter_results, patterns, overall_status, report_type=report_type)

    return {
        "report_type": report_type,
        "patient": {
            "name": normalized.get("name"),
            "age": age,
            "sex": sex,
            "weight": normalized.get("weight"),
        },
        "normalized_input": normalized,
        "overall_status": overall_status,
        "overall_banner": OVERALL_BANNERS[overall_status],
        "parameters": parameter_results,
        "patterns": patterns,
        "clinical_summary": summary,
    }


# Backward-compatible alias — existing callers using analyze_cbc still work.
def analyze_cbc(payload: Dict[str, Any]) -> Dict[str, Any]:
    return analyze_report(payload, report_type="cbc")


# ─── PDF EXTRACTION ──────────────────────────────────────────────────────────

def _extract_text_with_pymupdf(file_bytes: bytes) -> str:
    if fitz is None:
        return ""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages = [page.get_text("text") or "" for page in doc]
        text = "\n".join(part for part in pages if part)
        logger.debug("PyMuPDF extracted %s characters", len(text))
        return text
    except Exception as exc:  # pragma: no cover
        logger.warning("PyMuPDF extraction failed: %s", exc)
        return ""


def _extract_text_with_secondary_parsers(file_bytes: bytes) -> str:
    chunks: List[str] = []
    if pdfplumber is not None:
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    chunks.append(page.extract_text() or "")
        except Exception as exc:  # pragma: no cover
            logger.warning("pdfplumber extraction failed: %s", exc)

    if not "".join(chunks).strip() and PdfReader is not None:
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                chunks.append(page.extract_text() or "")
        except Exception as exc:  # pragma: no cover
            logger.warning("PyPDF2 extraction failed: %s", exc)
    return "\n".join(part for part in chunks if part)


def _extract_text_with_ocr(file_bytes: bytes) -> str:
    if convert_from_bytes is None or pytesseract is None:
        logger.info("OCR fallback unavailable: pdf2image or pytesseract missing")
        return ""
    try:
        images = convert_from_bytes(file_bytes)
        text_chunks = [pytesseract.image_to_string(image) or "" for image in images]
        text = "\n".join(part for part in text_chunks if part)
        logger.debug("OCR extracted %s characters", len(text))
        return text
    except Exception as exc:  # pragma: no cover
        logger.warning("OCR fallback failed: %s", exc)
        return ""


def clean_ocr_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    return text


def extract_text_from_pdf(file_bytes: bytes) -> str:
    text = _extract_text_with_pymupdf(file_bytes)
    if len(text.strip()) >= 40:
        return text

    if text.strip():
        logger.info("PyMuPDF text was sparse; trying secondary parsers")
    else:
        logger.info("PyMuPDF returned little or no text; possible scanned PDF")

    fallback_text = _extract_text_with_secondary_parsers(file_bytes)
    combined = "\n".join(part for part in [text, fallback_text] if part).strip()
    if len(combined) >= 40:
        return combined

    logger.info("Text extraction still sparse; attempting OCR fallback")
    ocr_text = _extract_text_with_ocr(file_bytes)
    return "\n".join(part for part in [combined, ocr_text] if part).strip()


def _read_pdf_bytes(file: bytes | BinaryIO) -> bytes:
    if isinstance(file, bytes):
        return file
    if hasattr(file, "seek"):
        file.seek(0)
    file_bytes = file.read()
    if hasattr(file, "seek"):
        file.seek(0)
    return file_bytes


def normalize_extracted_text(text: str) -> str:
    normalized = text.lower()
    normalized = normalized.replace("\n", " ").replace("\r", " ")
    normalized = re.sub(r"[^a-z0-9.%/\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def detect_report_type(text: str) -> Tuple[str, Dict[str, int]]:
    """Score the extracted text against each report type's detection keywords
    and return the best-guess report_type key plus the full score breakdown,
    so the UI can show/confirm the guess rather than silently trusting it."""
    normalized_text = normalize_extracted_text(text)
    scores: Dict[str, int] = {}
    for key, definition in REPORT_TYPES.items():
        score = 0
        for keyword in definition["detection_keywords"]:
            if keyword.lower() in normalized_text:
                score += 1
        scores[key] = score
    best_key = max(scores, key=scores.get)
    if scores[best_key] == 0:
        return DEFAULT_REPORT_TYPE, scores
    return best_key, scores


def _extract_value_by_regex(normalized_text: str, keywords: List[str]) -> Optional[float]:
    for keyword in keywords:
        pattern = re.compile(rf"{re.escape(keyword.lower())}[^0-9]{{0,20}}([\d]+\.?[\d]*)")
        match = pattern.search(normalized_text)
        if match:
            try:
                value = float(match.group(1))
                logger.debug("Regex extraction matched %s -> %s", keyword, value)
                return value
            except ValueError:
                continue
    return None


def _extract_value_from_line(line: str, keywords: List[str]) -> Optional[float]:
    lowered = line.lower()
    for keyword in keywords:
        if keyword.lower() not in lowered:
            continue

        direct = re.search(rf"{re.escape(keyword.lower())}[^0-9]{{0,20}}([\d]+\.?[\d]*)", lowered)
        if direct:
            try:
                return float(direct.group(1))
            except ValueError:
                pass

        pieces = [part.strip() for part in re.split(r"\s{2,}|\t| {1,}\| {1,}", lowered) if part.strip()]
        for index, piece in enumerate(pieces):
            if keyword.lower() in piece:
                for candidate in pieces[index:index + 3]:
                    number_match = re.search(r"([\d]+\.?[\d]*)", candidate)
                    if number_match:
                        try:
                            return float(number_match.group(1))
                        except ValueError:
                            continue

        all_numbers = re.findall(r"([\d]+\.?[\d]*)", lowered)
        if all_numbers:
            try:
                return float(all_numbers[0])
            except ValueError:
                continue
    return None


def _extract_from_lines(raw_text: str, keywords: List[str]) -> Optional[float]:
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        value = _extract_value_from_line(line, keywords)
        if value is not None:
            logger.debug("Line extraction matched %s -> %s", keywords[0], value)
            return value
    return None


def _normalize_extracted_parameter_value(metric: str, value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    if metric in ABSOLUTE_COUNT_FIELDS and value > 1000:
        return round(value / 1000.0, 2)
    return round(value, 2)


def extract_values_from_text(text: str, report_type: str = DEFAULT_REPORT_TYPE) -> Dict[str, Optional[float]]:
    parameters = get_parameters(report_type)
    normalized_text = normalize_extracted_text(text)
    extracted: Dict[str, Optional[float]] = {}

    for key, definition in parameters.items():
        keywords = list(definition.get("aliases", [key]))
        # Longest/most specific alias first, so "total bilirubin" is tried before "bilirubin".
        keywords.sort(key=len, reverse=True)
        value = _extract_value_by_regex(normalized_text, keywords)
        if value is None:
            value = _extract_from_lines(text, keywords)
        extracted[key] = _normalize_extracted_parameter_value(key, value)

    logger.info(
        "%s extraction completed with %s/%s values found",
        report_type,
        sum(value is not None for value in extracted.values()),
        len(extracted),
    )
    return extracted


# Backward-compatible alias
def extract_cbc_values_from_text(text: str) -> Dict[str, Optional[float]]:
    return extract_values_from_text(text, report_type="cbc")


def extract_report_from_pdf(file: bytes | BinaryIO, report_type: Optional[str] = None) -> Dict[str, Any]:
    file_bytes = _read_pdf_bytes(file)
    text = extract_text_from_pdf(file_bytes)
    if len(text.strip()) < 50:
        logger.info("Using OCR fallback from extract_report_from_pdf")
        ocr_text = _extract_text_with_ocr(file_bytes)
        text = clean_ocr_text(ocr_text) or text
    logger.info("Final extracted text length: %s characters", len(text))

    detected_type, detection_scores = detect_report_type(text)
    resolved_type = report_type or detected_type
    if resolved_type not in REPORT_TYPES:
        resolved_type = DEFAULT_REPORT_TYPE

    values = extract_values_from_text(text, report_type=resolved_type)
    missing = [key for key, value in values.items() if value is None]
    return {
        "text": text,
        "report_type": resolved_type,
        "detected_report_type": detected_type,
        "detection_scores": detection_scores,
        "values": values,
        "missing_fields": missing,
        "is_partial": bool(missing),
    }


# Backward-compatible alias
def extract_cbc_from_pdf(file: bytes | BinaryIO) -> Dict[str, Any]:
    return extract_report_from_pdf(file, report_type="cbc")
