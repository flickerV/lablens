from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ReferenceRange:
    low: float
    high: float
    unit: str
    sex: Optional[str] = None


# ─── CBC ───────────────────────────────────────────────────────────────────

CBC_GROUPS: List[Dict[str, object]] = [
    {"title": "Red Blood Cells", "fields": ["hemoglobin", "rbc", "hematocrit", "mcv", "mch", "mchc"]},
    {"title": "White Blood Cells", "fields": ["wbc", "neutrophils", "lymphocytes", "monocytes", "eosinophils", "basophils"]},
    {"title": "Platelets", "fields": ["platelets"]},
]

CBC_PARAMETERS: Dict[str, Dict[str, object]] = {
    "hemoglobin": {
        "label": "Hemoglobin", "unit": "g/dL", "group": "Red Blood Cells",
        "aliases": ["hemoglobin", "haemoglobin", "hb", "hgb"],
        "ranges": [ReferenceRange(13.5, 17.5, "g/dL", sex="male"), ReferenceRange(12.0, 15.5, "g/dL", sex="female")],
    },
    "rbc": {
        "label": "RBC", "unit": "million/uL", "group": "Red Blood Cells",
        "aliases": ["rbc", "red blood cells", "red blood cell count"],
        "ranges": [ReferenceRange(4.7, 6.1, "million/uL", sex="male"), ReferenceRange(4.2, 5.4, "million/uL", sex="female")],
    },
    "hematocrit": {
        "label": "Hematocrit", "unit": "%", "group": "Red Blood Cells",
        "aliases": ["hematocrit", "haematocrit", "hct", "pcv"],
        "ranges": [ReferenceRange(41.0, 53.0, "%", sex="male"), ReferenceRange(36.0, 46.0, "%", sex="female")],
    },
    "mcv": {
        "label": "MCV", "unit": "fL", "group": "Red Blood Cells",
        "aliases": ["mcv", "mean corpuscular volume"], "ranges": [ReferenceRange(80.0, 100.0, "fL")],
    },
    "mch": {
        "label": "MCH", "unit": "pg", "group": "Red Blood Cells",
        "aliases": ["mch", "mean corpuscular hemoglobin"], "ranges": [ReferenceRange(27.0, 33.0, "pg")],
    },
    "mchc": {
        "label": "MCHC", "unit": "g/dL", "group": "Red Blood Cells",
        "aliases": ["mchc", "mean corpuscular hemoglobin concentration"], "ranges": [ReferenceRange(32.0, 36.0, "g/dL")],
    },
    "wbc": {
        "label": "WBC", "unit": "/uL", "display_unit": "x10^3/uL", "display_divisor": 1000.0, "group": "White Blood Cells",
        "aliases": ["wbc", "white blood cells", "white blood cell count", "total leucocyte count", "tlc"],
        "ranges": [ReferenceRange(4000.0, 11000.0, "/uL")],
    },
    "neutrophils": {
        "label": "Neutrophils", "unit": "%", "group": "White Blood Cells",
        "aliases": ["neutrophils", "neutrophil", "neu"], "ranges": [ReferenceRange(40.0, 70.0, "%")],
    },
    "lymphocytes": {
        "label": "Lymphocytes", "unit": "%", "group": "White Blood Cells",
        "aliases": ["lymphocytes", "lymphocyte", "lym"], "ranges": [ReferenceRange(20.0, 40.0, "%")],
    },
    "monocytes": {
        "label": "Monocytes", "unit": "%", "group": "White Blood Cells",
        "aliases": ["monocytes", "monocyte", "mono"], "ranges": [ReferenceRange(2.0, 8.0, "%")],
    },
    "eosinophils": {
        "label": "Eosinophils", "unit": "%", "group": "White Blood Cells",
        "aliases": ["eosinophils", "eosinophil", "eos"], "ranges": [ReferenceRange(1.0, 6.0, "%")],
    },
    "basophils": {
        "label": "Basophils", "unit": "%", "group": "White Blood Cells",
        "aliases": ["basophils", "basophil", "baso"], "ranges": [ReferenceRange(0.0, 2.0, "%")],
    },
    "platelets": {
        "label": "Platelets", "unit": "/uL", "display_unit": "x10^3/uL", "display_divisor": 1000.0, "group": "Platelets",
        "aliases": ["platelet count", "platelets", "plt", "platelet"], "ranges": [ReferenceRange(150000.0, 450000.0, "/uL")],
    },
}

# ─── Lipid Profile ───────────────────────────────────────────────────────────

LIPID_GROUPS: List[Dict[str, object]] = [
    {"title": "Lipid Profile", "fields": ["total_cholesterol", "ldl", "hdl", "triglycerides", "vldl"]},
]

LIPID_PARAMETERS: Dict[str, Dict[str, object]] = {
    "total_cholesterol": {
        "label": "Total Cholesterol", "unit": "mg/dL", "group": "Lipid Profile",
        "aliases": ["total cholesterol", "cholesterol total", "cholesterol"],
        "ranges": [ReferenceRange(125.0, 200.0, "mg/dL")],
    },
    "ldl": {
        "label": "LDL Cholesterol", "unit": "mg/dL", "group": "Lipid Profile",
        "aliases": ["ldl cholesterol", "ldl-c", "ldl"], "ranges": [ReferenceRange(0.0, 100.0, "mg/dL")],
    },
    "hdl": {
        "label": "HDL Cholesterol", "unit": "mg/dL", "group": "Lipid Profile",
        "aliases": ["hdl cholesterol", "hdl-c", "hdl"],
        "ranges": [ReferenceRange(40.0, 60.0, "mg/dL", sex="male"), ReferenceRange(50.0, 60.0, "mg/dL", sex="female")],
    },
    "triglycerides": {
        "label": "Triglycerides", "unit": "mg/dL", "group": "Lipid Profile",
        "aliases": ["triglycerides", "tgl", "tg"], "ranges": [ReferenceRange(0.0, 150.0, "mg/dL")],
    },
    "vldl": {
        "label": "VLDL Cholesterol", "unit": "mg/dL", "group": "Lipid Profile",
        "aliases": ["vldl cholesterol", "vldl-c", "vldl"], "ranges": [ReferenceRange(5.0, 40.0, "mg/dL")],
    },
}

# ─── Liver Function Test ────────────────────────────────────────────────────

LFT_GROUPS: List[Dict[str, object]] = [
    {"title": "Bilirubin", "fields": ["total_bilirubin", "direct_bilirubin"]},
    {"title": "Liver Enzymes", "fields": ["sgot", "sgpt", "alp"]},
    {"title": "Proteins", "fields": ["total_protein", "albumin", "globulin"]},
]

LFT_PARAMETERS: Dict[str, Dict[str, object]] = {
    "total_bilirubin": {
        "label": "Total Bilirubin", "unit": "mg/dL", "group": "Bilirubin",
        "aliases": ["total bilirubin", "bilirubin total", "bilirubin"], "ranges": [ReferenceRange(0.3, 1.2, "mg/dL")],
    },
    "direct_bilirubin": {
        "label": "Direct Bilirubin", "unit": "mg/dL", "group": "Bilirubin",
        "aliases": ["direct bilirubin", "conjugated bilirubin"], "ranges": [ReferenceRange(0.0, 0.3, "mg/dL")],
    },
    "sgot": {
        "label": "SGOT (AST)", "unit": "U/L", "group": "Liver Enzymes",
        "aliases": ["sgot", "ast", "aspartate aminotransferase", "aspartate transaminase"], "ranges": [ReferenceRange(5.0, 40.0, "U/L")],
    },
    "sgpt": {
        "label": "SGPT (ALT)", "unit": "U/L", "group": "Liver Enzymes",
        "aliases": ["sgpt", "alt", "alanine aminotransferase", "alanine transaminase"], "ranges": [ReferenceRange(7.0, 56.0, "U/L")],
    },
    "alp": {
        "label": "Alkaline Phosphatase", "unit": "U/L", "group": "Liver Enzymes",
        "aliases": ["alkaline phosphatase", "alp"], "ranges": [ReferenceRange(44.0, 147.0, "U/L")],
    },
    "total_protein": {
        "label": "Total Protein", "unit": "g/dL", "group": "Proteins",
        "aliases": ["total protein", "serum total protein"], "ranges": [ReferenceRange(6.0, 8.3, "g/dL")],
    },
    "albumin": {
        "label": "Albumin", "unit": "g/dL", "group": "Proteins",
        "aliases": ["albumin", "serum albumin"], "ranges": [ReferenceRange(3.5, 5.0, "g/dL")],
    },
    "globulin": {
        "label": "Globulin", "unit": "g/dL", "group": "Proteins",
        "aliases": ["globulin", "serum globulin"], "ranges": [ReferenceRange(2.0, 3.5, "g/dL")],
    },
}

# ─── Kidney Function Test ───────────────────────────────────────────────────

KFT_GROUPS: List[Dict[str, object]] = [
    {"title": "Renal Markers", "fields": ["blood_urea", "creatinine", "uric_acid"]},
    {"title": "Electrolytes", "fields": ["sodium", "potassium", "chloride"]},
]

KFT_PARAMETERS: Dict[str, Dict[str, object]] = {
    "blood_urea": {
        "label": "Blood Urea", "unit": "mg/dL", "group": "Renal Markers",
        "aliases": ["blood urea", "urea", "serum urea"], "ranges": [ReferenceRange(15.0, 45.0, "mg/dL")],
    },
    "creatinine": {
        "label": "Serum Creatinine", "unit": "mg/dL", "group": "Renal Markers",
        "aliases": ["serum creatinine", "creatinine"],
        "ranges": [ReferenceRange(0.7, 1.3, "mg/dL", sex="male"), ReferenceRange(0.6, 1.1, "mg/dL", sex="female")],
    },
    "uric_acid": {
        "label": "Uric Acid", "unit": "mg/dL", "group": "Renal Markers",
        "aliases": ["uric acid", "serum uric acid"],
        "ranges": [ReferenceRange(3.4, 7.0, "mg/dL", sex="male"), ReferenceRange(2.4, 6.0, "mg/dL", sex="female")],
    },
    "sodium": {
        "label": "Sodium", "unit": "mEq/L", "group": "Electrolytes",
        "aliases": ["sodium", "serum sodium", "na+", "na"], "ranges": [ReferenceRange(135.0, 145.0, "mEq/L")],
    },
    "potassium": {
        "label": "Potassium", "unit": "mEq/L", "group": "Electrolytes",
        "aliases": ["potassium", "serum potassium", "k+"], "ranges": [ReferenceRange(3.5, 5.1, "mEq/L")],
    },
    "chloride": {
        "label": "Chloride", "unit": "mEq/L", "group": "Electrolytes",
        "aliases": ["chloride", "serum chloride", "cl-"], "ranges": [ReferenceRange(96.0, 106.0, "mEq/L")],
    },
}

# ─── Thyroid Panel ───────────────────────────────────────────────────────────

THYROID_GROUPS: List[Dict[str, object]] = [
    {"title": "Thyroid Panel", "fields": ["tsh", "t3", "t4"]},
]

THYROID_PARAMETERS: Dict[str, Dict[str, object]] = {
    "tsh": {
        "label": "TSH", "unit": "mIU/L", "group": "Thyroid Panel",
        "aliases": ["tsh", "thyroid stimulating hormone"], "ranges": [ReferenceRange(0.4, 4.0, "mIU/L")],
    },
    "t3": {
        "label": "T3 (Triiodothyronine)", "unit": "ng/dL", "group": "Thyroid Panel",
        "aliases": ["t3", "triiodothyronine", "total t3"], "ranges": [ReferenceRange(80.0, 200.0, "ng/dL")],
    },
    "t4": {
        "label": "T4 (Thyroxine)", "unit": "ug/dL", "group": "Thyroid Panel",
        "aliases": ["t4", "thyroxine", "total t4"], "ranges": [ReferenceRange(5.1, 14.1, "ug/dL")],
    },
}

# ─── Blood Sugar / Diabetes Profile ─────────────────────────────────────────

SUGAR_GROUPS: List[Dict[str, object]] = [
    {"title": "Blood Sugar", "fields": ["fasting_sugar", "pp_sugar", "hba1c"]},
]

SUGAR_PARAMETERS: Dict[str, Dict[str, object]] = {
    "fasting_sugar": {
        "label": "Fasting Blood Sugar", "unit": "mg/dL", "group": "Blood Sugar",
        "aliases": ["fasting blood sugar", "fasting glucose", "fbs", "blood glucose fasting", "glucose fasting"],
        "ranges": [ReferenceRange(70.0, 100.0, "mg/dL")],
    },
    "pp_sugar": {
        "label": "Post-Prandial Blood Sugar", "unit": "mg/dL", "group": "Blood Sugar",
        "aliases": ["post prandial blood sugar", "postprandial blood sugar", "ppbs", "pp blood sugar", "glucose post prandial"],
        "ranges": [ReferenceRange(70.0, 140.0, "mg/dL")],
    },
    "hba1c": {
        "label": "HbA1c", "unit": "%", "group": "Blood Sugar",
        "aliases": ["hba1c", "glycosylated hemoglobin", "glycated hemoglobin", "a1c"],
        "ranges": [ReferenceRange(4.0, 5.6, "%")],
    },
}

# ─── Unified report-type registry ───────────────────────────────────────────

REPORT_TYPES: Dict[str, Dict[str, object]] = {
    "cbc": {
        "key": "cbc", "label": "Complete Blood Count", "short_label": "CBC", "icon": "🩸",
        "detection_keywords": ["complete blood count", "cbc", "hemoglobin", "haemoglobin", "hematocrit",
                                "platelet count", "total leucocyte count", "differential count", "packed cell volume"],
        "groups": CBC_GROUPS, "parameters": CBC_PARAMETERS,
    },
    "lipid": {
        "key": "lipid", "label": "Lipid Profile", "short_label": "Lipid", "icon": "🫀",
        "detection_keywords": ["lipid profile", "cholesterol", "triglycerides", "hdl", "ldl", "vldl"],
        "groups": LIPID_GROUPS, "parameters": LIPID_PARAMETERS,
    },
    "lft": {
        "key": "lft", "label": "Liver Function Test", "short_label": "LFT", "icon": "🟠",
        "detection_keywords": ["liver function test", "lft", "bilirubin", "sgot", "sgpt", "alkaline phosphatase", "alt", "ast"],
        "groups": LFT_GROUPS, "parameters": LFT_PARAMETERS,
    },
    "kft": {
        "key": "kft", "label": "Kidney Function Test", "short_label": "KFT", "icon": "🫘",
        "detection_keywords": ["kidney function test", "kft", "renal function test", "rft", "blood urea",
                                "serum creatinine", "uric acid"],
        "groups": KFT_GROUPS, "parameters": KFT_PARAMETERS,
    },
    "thyroid": {
        "key": "thyroid", "label": "Thyroid Panel", "short_label": "Thyroid", "icon": "🦋",
        "detection_keywords": ["thyroid profile", "thyroid function test", "tsh", "triiodothyronine", "thyroxine", "t3", "t4"],
        "groups": THYROID_GROUPS, "parameters": THYROID_PARAMETERS,
    },
    "blood_sugar": {
        "key": "blood_sugar", "label": "Blood Sugar / Diabetes Profile", "short_label": "Blood Sugar", "icon": "🩹",
        "detection_keywords": ["blood glucose", "fasting blood sugar", "hba1c", "glycosylated hemoglobin",
                                "postprandial", "random blood sugar", "diabetes profile"],
        "groups": SUGAR_GROUPS, "parameters": SUGAR_PARAMETERS,
    },
}

DEFAULT_REPORT_TYPE = "cbc"

# Backward-compatible aliases (existing code that imports these still works, defaults to CBC)
PARAMETER_GROUPS = CBC_GROUPS
PARAMETERS = CBC_PARAMETERS

STATUS_COLORS = {
    "normal": {"text": "#166534", "bg": "#ecfdf3"},
    "low": {"text": "#1d4ed8", "bg": "#eaf2ff"},
    "high": {"text": "#b42318", "bg": "#fef2f2"},
    "missing": {"text": "#667085", "bg": "#f3f4f6"},
}

OVERALL_BANNERS = {
    "Normal": {"text": "#166534", "bg": "#ecfdf3"},
    "Mild Abnormality": {"text": "#9a6700", "bg": "#fff8db"},
    "Moderate Abnormality": {"text": "#b45309", "bg": "#fff1e6"},
    "Significant Concern": {"text": "#991b1b", "bg": "#fef2f2"},
}

SEVERITY_RANK = {"mild": 1, "moderate": 2, "significant": 3}

ABSOLUTE_COUNT_FIELDS = {"wbc", "platelets"}

DOCUMENT_TYPES = [
    "X-Ray", "MRI", "CT Scan", "Ultrasound", "Prescription", "Discharge Summary",
    "Vaccination Record", "Lab Report (Other)", "Other",
]
