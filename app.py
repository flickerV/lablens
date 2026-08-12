from __future__ import annotations

import base64
import io
import json
import logging
import urllib.parse
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
from PIL import Image
import streamlit.components.v1 as components

try:
    import cv2
    import numpy as np
except ImportError:  # pragma: no cover
    cv2 = None
    np = None

try:
    from pyzbar.pyzbar import decode as pyzbar_decode
except ImportError:  # pragma: no cover
    pyzbar_decode = None

from config import (
    DEFAULT_REPORT_TYPE,
    DOCUMENT_TYPES,
    OVERALL_BANNERS,
    PARAMETER_GROUPS,
    PARAMETERS,
    REPORT_TYPES,
    STATUS_COLORS,
)
from engine import analyze_report, detect_report_type, extract_report_from_pdf


st.set_page_config(
    page_title="LabLens",
    page_icon="⚕",
    layout="wide",
    initial_sidebar_state="expanded",
)

logger_qr = logging.getLogger("qr_decode")

NAV_ITEMS = ["Add Report", "Results", "History", "Trends", "Insights", "Vault"]
LEGACY_NAV_MAP = {
    "➕ Add Report": "Add Report",
    "📊 Results": "Results",
    "📁 History": "History",
    "📈 Trends": "Trends",
    "🧠 Insights": "Insights",
    "🗄 Vault": "Vault",
}

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
  --bg: #faf8f5;
  --ink: #1c1712;
  --muted: #6b6560;
  --line: #e5ded6;
  --card: #ffffff;
  --accent: #c8401a;
  --accent-dark: #9c3313;
  --accent2: #0f7a5c;
  --accent3: #1a7f5a;
  --warm: #f6f0e8;
  --warm-strong: #f2e4d3;
  --input-bg: #ffffff;
  --input-border: #cdc3b8;
  --green-bg: #e9f6ee;
  --green-text: #14603f;
  --amber-bg: #fef6e6;
  --amber-text: #8a5a06;
  --orange-bg: #fdeee0;
  --orange-text: #a1470f;
  --red-bg: #fceeed;
  --red-text: #a3241d;
  --blue-bg: #e6f1fb;
  --blue-text: #0c447c;
  --shadow-sm: 0 1px 3px rgba(28,23,18,.06), 0 4px 12px rgba(28,23,18,.05);
  --shadow-md: 0 2px 10px rgba(28,23,18,.08), 0 14px 34px rgba(28,23,18,.09);
  --radius: 14px;
  --radius-sm: 9px;
}

/* ── Base ── */
html, body, .stApp {
  background: var(--bg) !important;
  font-family: 'Inter', sans-serif;
  color: var(--ink);
  font-size: 15.5px;
}
.block-container {
  max-width: 1180px;
  padding-top: .6rem;
  padding-bottom: 3rem;
}

/* ── Typography ── */
h1, h2, h3, .serif {
  font-family: 'Inter', sans-serif !important;
  font-weight: 700 !important;
  letter-spacing: -.01em;
  color: var(--ink);
}
h2 { font-size: 1.55rem; margin: 1.4rem 0 .8rem; }
h3 { font-size: 1.15rem; margin: 1rem 0 .5rem; }
p, span, div { line-height: 1.55; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
  background: #201a14 !important;
  border-right: 1px solid #352b21 !important;
}
section[data-testid="stSidebar"] * { color: #e4dcd2 !important; }
section[data-testid="stSidebar"] .sidebar-brand {
  padding: 1.2rem 1rem 0.6rem;
  border-bottom: 1px solid #352b21;
  margin-bottom: .6rem;
}
section[data-testid="stSidebar"] .sidebar-brand-name {
  font-family: 'Inter', sans-serif;
  font-weight: 700;
  font-size: 1.25rem;
  color: #fff !important;
  letter-spacing: -.01em;
}
section[data-testid="stSidebar"] .sidebar-profile {
  padding: .6rem 1rem;
  font-size: .86rem;
  color: #a89a8a !important;
}
section[data-testid="stSidebar"] .stRadio label {
  padding: .6rem .75rem;
  border-radius: var(--radius-sm);
  margin: .12rem 0;
  display: flex;
  align-items: center;
  gap: .5rem;
  transition: background .15s;
  cursor: pointer;
  font-size: .95rem;
  font-weight: 500;
}
section[data-testid="stSidebar"] .stRadio label:has(input:checked) {
  background: rgba(200,64,26,.25) !important;
  color: #f5b699 !important;
}
section[data-testid="stSidebar"] .stButton > button {
  background: #352b21 !important;
  color: #e4dcd2 !important;
  border: 1px solid #4a3c2e !important;
  border-radius: var(--radius-sm) !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
  background: #4a3c2e !important;
}

/* ── Cards ── */
.card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  padding: 1.25rem 1.3rem;
  margin-bottom: .85rem;
}
.card-sm {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-sm);
  padding: .85rem 1rem;
}
.card:hover, .card-sm:hover {
  box-shadow: var(--shadow-md);
  border-color: #d6cbbf;
  transition: all .2s ease;
}
.card-title {
  font-family: 'Inter', sans-serif; font-weight: 700;
  font-size: 1.08rem;
  color: var(--ink);
  margin-bottom: .3rem;
}
.card-sub { font-size: .88rem; color: var(--muted); line-height: 1.55; }

/* ── Status banner ── */
.status-banner {
  border-radius: var(--radius);
  padding: 1.3rem 1.6rem;
  margin-bottom: .5rem;
  display: flex;
  align-items: center;
  gap: 1.2rem;
  border: 1px solid rgba(0,0,0,.07);
}
.status-banner-dot {
  width: 15px; height: 15px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status-banner-label {
  font-size: .78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .09em;
  opacity: .75;
  margin-bottom: .2rem;
}
.status-banner-value {
  font-family: 'Inter', sans-serif; font-weight: 700;
  font-size: 1.9rem;
  line-height: 1.1;
}
.status-note {
  font-size: .92rem;
  color: var(--muted);
  padding: 0 .2rem;
  margin-bottom: 1.1rem;
  line-height: 1.6;
}

/* ── Metric cards ── */
.metric-card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 1.1rem 1.2rem 1rem;
  position: relative;
  overflow: hidden;
  transition: all .2s ease;
}
.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}
.metric-card-accent {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  border-radius: var(--radius) var(--radius) 0 0;
}
.metric-label { font-size: .82rem; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; margin-bottom: .35rem; }
.metric-value-large { font-family: 'Inter', sans-serif; font-weight: 700; font-size: 1.9rem; line-height: 1.1; margin-bottom: .2rem; }
.metric-ref { font-size: .78rem; color: var(--muted); margin-top: .25rem; }

/* ── Gauge bar ── */
.gauge-wrap { margin: .5rem 0 .2rem; }
.gauge-track {
  height: 7px;
  background: #ece3d8;
  border-radius: 999px;
  position: relative;
  overflow: visible;
}
.gauge-fill {
  height: 100%;
  border-radius: 999px;
  position: absolute;
  top: 0; left: 0;
  transition: width .4s ease;
}
.gauge-needle {
  width: 11px; height: 11px;
  border-radius: 50%;
  background: var(--ink);
  position: absolute;
  top: -2px;
  transform: translateX(-50%);
  box-shadow: 0 0 0 2px white;
  z-index: 2;
}
.gauge-labels {
  display: flex;
  justify-content: space-between;
  font-size: .72rem;
  color: var(--muted);
  margin-top: .35rem;
}

/* ── Status badge ── */
.badge {
  display: inline-block;
  padding: .25rem .7rem;
  border-radius: 999px;
  font-size: .76rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .05em;
}

/* ── Pattern cards ── */
.pattern-card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 1.2rem 1.3rem;
  margin-bottom: .75rem;
  border-left: 4px solid var(--accent);
}
.pattern-name {
  font-family: 'Inter', sans-serif; font-weight: 700;
  font-size: 1.15rem;
  margin-bottom: .4rem;
}
.pattern-body { color: var(--ink); font-size: .92rem; line-height: 1.6; }
.pattern-causes, .pattern-actions { margin-top: .7rem; font-size: .88rem; }
.pattern-causes-title, .pattern-actions-title {
  font-weight: 700;
  font-size: .78rem;
  text-transform: uppercase;
  letter-spacing: .06em;
  color: var(--muted);
  margin-bottom: .3rem;
}
.pattern-item { padding: .2rem 0; display: flex; gap: .5rem; }
.pattern-item::before { content: '\\2192'; color: var(--accent); flex-shrink: 0; }

/* ── Summary blocks ── */
.summary-block {
  background: var(--warm);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  padding: 1.05rem 1.15rem;
  margin-bottom: .6rem;
}
.summary-block-title {
  font-weight: 700;
  font-size: .8rem;
  text-transform: uppercase;
  letter-spacing: .07em;
  color: var(--accent-dark);
  margin-bottom: .4rem;
}
.summary-block-body { color: var(--ink); font-size: .93rem; line-height: 1.65; }

/* ── List blocks (replaces repeated duplicate cards) ── */
.list-block {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 1.2rem 1.3rem;
  margin-bottom: .85rem;
}
.list-block-title {
  font-weight: 700;
  font-size: 1.02rem;
  color: var(--ink);
  margin-bottom: .7rem;
  display: flex;
  align-items: center;
  gap: .5rem;
}
.list-block-title::before {
  content: '';
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--accent3);
  flex-shrink: 0;
}
.list-block ul { margin: 0; padding-left: 1.15rem; }
.list-block li { font-size: .93rem; color: var(--ink); line-height: 1.75; }

/* ── Profile strip ── */
.profile-strip {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 1rem 1.3rem;
  display: flex;
  align-items: center;
  gap: 2rem;
  margin-bottom: 1.25rem;
  flex-wrap: wrap;
}
.profile-chip { display: flex; flex-direction: column; gap: .1rem; }
.profile-chip-label { font-size: .72rem; font-weight: 700; text-transform: uppercase; letter-spacing: .07em; color: var(--muted); }
.profile-chip-value { font-family: 'Inter', sans-serif; font-weight: 700; font-size: 1.05rem; }

/* ── History cards ── */
.history-card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 1rem 1.2rem;
  margin-bottom: .65rem;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  transition: all .18s ease;
}
.history-card:hover {
  box-shadow: var(--shadow-md);
  border-color: #d6cbbf;
}
.history-date { font-weight: 700; font-size: .96rem; margin-bottom: .2rem; }
.history-patterns { font-size: .83rem; color: var(--muted); }

/* ── Identity screen ── */
.identity-wrap {
  min-height: calc(100vh - 1.2rem);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: .5rem 1rem 1.2rem;
}
.identity-card {
  background: linear-gradient(180deg, #ffffff 0%, #fbf7f2 100%);
  border: 1px solid var(--line);
  border-radius: 18px;
  box-shadow: var(--shadow-md);
  padding: 1.8rem 1.8rem 1.55rem;
  max-width: 920px;
  width: 100%;
}
.identity-eyebrow {
  display: inline-block;
  background: var(--orange-bg);
  color: var(--accent-dark);
  font-size: .76rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .09em;
  padding: .3rem .85rem;
  border-radius: 999px;
  margin-bottom: 1rem;
}
.identity-headline {
  font-family: 'Inter', sans-serif; font-weight: 700;
  font-size: 2.2rem;
  line-height: 1.15;
  margin-bottom: .7rem;
}
.identity-body {
  color: var(--muted);
  font-size: .97rem;
  line-height: 1.7;
  max-width: 560px;
  margin-bottom: 1.25rem;
}
.identity-divider {
  height: 1px;
  background: var(--line);
  margin: 1.15rem 0 1rem;
}
.trust-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: .6rem;
  margin-bottom: 1rem;
}
.trust-pill {
  background: var(--warm);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  padding: .65rem .8rem;
  font-size: .8rem;
  color: var(--muted);
  line-height: 1.4;
}
.trust-pill strong {
  display: block;
  color: var(--ink);
  font-size: .82rem;
  margin-bottom: .14rem;
}
.disclaimer-note {
  max-width: 920px;
  width: 100%;
  margin: .9rem auto 0;
  padding: .75rem 1rem;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--card);
  color: var(--muted);
  font-size: .76rem;
  line-height: 1.55;
  text-align: center;
}
.stTextInput label p, .stNumberInput label p, .stSelectbox label p,
.stTextArea label p, .stDateInput label p {
  font-size: .92rem !important;
  font-weight: 600 !important;
  color: var(--ink) !important;
}

/* ── Input section (parameter group banners) ── */
.input-section {
  background: var(--warm-strong);
  border: 1px solid #e8d5bd;
  border-radius: var(--radius);
  padding: .85rem 1.2rem;
  margin-bottom: 1rem;
}
.input-section-title {
  font-weight: 800;
  font-size: 1.02rem;
  letter-spacing: .01em;
  color: var(--accent-dark);
  display: flex;
  align-items: center;
  gap: .5rem;
}
.mode-card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 1rem;
  min-height: 92px;
  box-shadow: var(--shadow-sm);
}
.mode-card-title {
  font-weight: 800;
  color: var(--ink);
  font-size: .96rem;
  margin-bottom: .25rem;
}
.mode-card-copy {
  color: var(--muted);
  font-size: .8rem;
  line-height: 1.45;
}
.doctor-brief {
  background: var(--warm);
  border: 1px solid #e8d5bd;
  border-radius: var(--radius);
  padding: 1.25rem 1.35rem;
  box-shadow: var(--shadow-sm);
}
.doctor-brief-title {
  font-family: 'Inter', sans-serif; font-weight: 700;
  font-size: 1.35rem;
  color: var(--ink);
  margin-bottom: .25rem;
}
.brief-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: .75rem;
  margin-top: 1rem;
}
.brief-box {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  padding: .9rem .95rem;
}
.brief-box-title {
  font-weight: 800;
  font-size: .8rem;
  text-transform: uppercase;
  letter-spacing: .07em;
  color: var(--accent-dark);
  margin-bottom: .45rem;
}
.brief-box-body {
  font-size: .89rem;
  color: var(--ink);
  line-height: 1.6;
}
.lifestyle-card {
  background: #f6faf7;
  border: 1px solid #d3e8da;
  border-radius: var(--radius);
  padding: 1.2rem 1.3rem;
}
.lifestyle-title {
  font-weight: 800;
  font-size: 1.02rem;
  color: var(--green-text);
  margin-bottom: .7rem;
  display: flex;
  align-items: center;
  gap: .5rem;
}
.lifestyle-title::before {
  content: '';
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--green-text);
  flex-shrink: 0;
}
.lifestyle-card ul { margin: 0; padding-left: 1.15rem; }
.lifestyle-card li { font-size: .93rem; color: var(--ink); line-height: 1.8; }

/* ── Report type picker ── */
.type-tile {
  background: var(--card);
  border: 1.5px solid var(--line);
  border-radius: var(--radius);
  padding: 1.1rem 1rem;
  text-align: center;
  cursor: pointer;
  transition: all .15s ease;
}
.type-tile:hover { border-color: var(--accent); box-shadow: var(--shadow-md); transform: translateY(-2px); }
.type-tile-label { font-weight: 700; font-size: .95rem; color: var(--ink); }
.type-tile-desc { font-size: .74rem; color: var(--muted); margin-top: .2rem; }

/* ── Trend selector ── */
.trend-tab {
  display: inline-block;
  padding: .4rem .9rem;
  border-radius: 999px;
  font-size: .85rem;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid var(--line);
  margin: 0 .2rem .4rem 0;
  background: var(--card);
  color: var(--muted);
  transition: all .15s;
}
.trend-tab.active {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}

/* ── Streamlit overrides ── */
.stButton > button {
  border-radius: var(--radius-sm) !important;
  font-weight: 600 !important;
  font-family: 'Inter', sans-serif !important;
  font-size: .95rem !important;
  border: 1.5px solid var(--input-border) !important;
  background: var(--card) !important;
  color: var(--ink) !important;
  box-shadow: var(--shadow-sm) !important;
  transition: all .15s ease !important;
}
.stButton > button:hover {
  border-color: var(--accent) !important;
  color: var(--accent-dark) !important;
  transform: translateY(-1px) !important;
  box-shadow: var(--shadow-md) !important;
}
.stButton > button[kind="primary"] {
  background: var(--accent) !important;
  color: #fff !important;
  border-color: var(--accent) !important;
}
.stButton > button[kind="primary"]:hover {
  background: var(--accent-dark) !important;
  border-color: var(--accent-dark) !important;
  color: #fff !important;
}
.stDownloadButton > button {
  border-radius: var(--radius-sm) !important;
  font-weight: 600 !important;
  font-family: 'Inter', sans-serif !important;
  border: 1.5px solid var(--input-border) !important;
}

/* Text / number / date inputs — explicit fill + visible border, fixes low-contrast bug */
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stDateInput"] input,
div[data-testid="stTextArea"] textarea {
  background: var(--input-bg) !important;
  border: 1.5px solid var(--input-border) !important;
  border-radius: var(--radius-sm) !important;
  color: var(--ink) !important;
  font-family: 'Inter', sans-serif !important;
  font-size: .96rem !important;
  padding: .55rem .7rem !important;
}
div[data-testid="stTextInput"] input::placeholder,
div[data-testid="stNumberInput"] input::placeholder,
div[data-testid="stTextArea"] textarea::placeholder {
  color: #9a9088 !important;
  opacity: 1 !important;
}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stNumberInput"] input:focus,
div[data-testid="stDateInput"] input:focus,
div[data-testid="stTextArea"] textarea:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px rgba(200,64,26,.14) !important;
}
/* Selectbox (BaseWeb dropdown, not a native <select>) — style the actual
   BaseWeb control itself and strip any nested div borders so nothing conflicts */
div[data-testid="stSelectbox"] div[data-baseweb="select"] {
  background: var(--input-bg) !important;
  border: 1.5px solid var(--input-border) !important;
  border-radius: var(--radius-sm) !important;
  color: var(--ink) !important;
  min-height: 2.6rem !important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
  border: none !important;
  background: transparent !important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"] span,
div[data-testid="stSelectbox"] div[data-baseweb="select"] div { color: var(--ink) !important; font-size: .96rem !important; }
div[data-testid="stSelectbox"] div[data-baseweb="select"]:focus-within {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px rgba(200,64,26,.14) !important;
}
ul[data-testid="stSelectboxVirtualDropdown"] { background: var(--input-bg) !important; }
ul[data-testid="stSelectboxVirtualDropdown"] li { color: var(--ink) !important; }

div[data-testid="stFileUploader"] section {
  border: 2px dashed var(--input-border) !important;
  border-radius: var(--radius) !important;
  background: var(--warm) !important;
}
div[data-testid="stFileUploader"] section button {
  border: 1.5px solid var(--input-border) !important;
  background: #fff !important;
}
div[data-testid="stCameraInput"] section {
  border: 1.5px solid var(--input-border) !important;
  border-radius: var(--radius) !important;
  background: var(--warm) !important;
}
.stDataFrame {
  border-radius: var(--radius-sm) !important;
  border: 1px solid var(--line) !important;
  overflow: hidden !important;
}
.stTabs [data-baseweb="tab-list"] {
  gap: .5rem;
  background: transparent;
  border-bottom: 1.5px solid var(--line);
}
.stTabs [data-baseweb="tab"] {
  border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important;
  font-family: 'Inter', sans-serif !important;
  font-weight: 600 !important;
  font-size: .96rem !important;
  color: var(--muted) !important;
}
.stTabs [data-baseweb="tab"] p,
.stTabs [data-baseweb="tab"] div {
  color: inherit !important;
}
.stTabs [data-baseweb="tab"]:hover {
  color: var(--accent-dark) !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
  color: var(--accent) !important;
}
.stTabs [data-baseweb="tab-highlight"] {
  background-color: var(--accent) !important;
}
.stAlert {
  border-radius: var(--radius-sm) !important;
  font-size: .92rem !important;
}
div[data-testid="stExpander"] {
  border: 1.5px solid var(--line) !important;
  border-radius: var(--radius) !important;
  background: var(--card) !important;
}
@media (max-width: 760px) {
  .identity-wrap { align-items: flex-start; padding: .25rem .4rem 1rem; }
  .identity-card { padding: 1.2rem; border-radius: 14px; }
  .identity-headline { font-size: 1.65rem; }
  .trust-row, .brief-grid { grid-template-columns: 1fr; }
}
</style>
"""


# ── Data helpers ──────────────────────────────────────────────────────────────

def load_history_store() -> Dict[str, List[Dict[str, Any]]]:
    """Session-only storage: each visitor gets their own private, in-memory
    history that resets when their session ends. This is intentional for a
    public deployment — nothing is written to shared disk, so no visitor can
    ever see another visitor's reports, and there's nothing sensitive sitting
    in a file on the server."""
    if "history_store" not in st.session_state:
        st.session_state.history_store = {}
    return st.session_state.history_store


def save_history_store(store: Dict[str, List[Dict[str, Any]]]) -> None:
    st.session_state.history_store = store


# ── Vault storage (unified medical history: any file, no analysis) ────────────

def load_vault_store() -> Dict[str, List[Dict[str, Any]]]:
    """Session-only, for the same reason as load_history_store above."""
    if "vault_store" not in st.session_state:
        st.session_state.vault_store = {}
    return st.session_state.vault_store


def save_vault_store(store: Dict[str, List[Dict[str, Any]]]) -> None:
    st.session_state.vault_store = store


def get_vault_documents(profile_id: str) -> List[Dict[str, Any]]:
    if not profile_id.strip():
        return []
    return sorted(
        load_vault_store().get(profile_id.strip(), []),
        key=lambda item: item["uploaded_at"],
        reverse=True,
    )


def save_vault_document(profile_id: str, doc_type: str, doc_date: str, notes: str, uploaded_file) -> None:
    store = load_vault_store()
    file_bytes = uploaded_file.getvalue()
    record = {
        "id": f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "profile_id": profile_id,
        "doc_type": doc_type,
        "doc_date": doc_date,
        "notes": notes.strip(),
        "filename": uploaded_file.name,
        "mime": uploaded_file.type or "application/octet-stream",
        "size_bytes": len(file_bytes),
        "data_b64": base64.b64encode(file_bytes).decode("ascii"),
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    store.setdefault(profile_id, []).append(record)
    save_vault_store(store)


def delete_vault_document(profile_id: str, doc_id: str) -> None:
    store = load_vault_store()
    if profile_id in store:
        store[profile_id] = [d for d in store[profile_id] if d["id"] != doc_id]
        save_vault_store(store)


def initialize_state() -> None:
    defaults = {
        "current_page": "identity",
        "dashboard_tab": "Add Report",
        "report_type": DEFAULT_REPORT_TYPE,
        "input_method": "manual",
        "pdf_values": {},
        "qr_values": {},
        "qr_payload_text": "",
        "qr_last_image_id": None,
        "qr_detected_type": None,
        "last_uploaded_name": None,
        "last_result": None,
        "last_report_date": None,
        "show_success_actions": False,
        "selected_report_index": None,
        "trend_metric": "hemoglobin",
        "profile": {"name": "", "age_raw": "", "gender": None, "weight_raw": "", "profile_id": ""},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def current_profile() -> Dict[str, Any]:
    return st.session_state.profile


def profile_payload() -> Dict[str, Any]:
    p = current_profile()
    return {
        "name": p["name"].strip(),
        "age_raw": p["age_raw"].strip(),
        "sex": p["gender"],
        "weight_raw": p["weight_raw"].strip(),
        "profile_id": p["profile_id"].strip(),
    }


def parse_optional_number(raw: str) -> Any:
    return None if raw is None or str(raw).strip() == "" else float(raw)


def parse_required_age(raw: str) -> Any:
    return None if raw is None or str(raw).strip() == "" else float(raw)


def field_key(report_type: str, field: str) -> str:
    return f"field_{report_type}_{field}"


def clear_parameter_fields(report_type: Optional[str] = None) -> None:
    report_type = report_type or st.session_state.get("report_type", DEFAULT_REPORT_TYPE)
    parameters = REPORT_TYPES[report_type]["parameters"]
    for field in parameters:
        st.session_state[field_key(report_type, field)] = ""


def set_parameter_fields(values: Dict[str, Any], report_type: Optional[str] = None) -> None:
    report_type = report_type or st.session_state.get("report_type", DEFAULT_REPORT_TYPE)
    parameters = REPORT_TYPES[report_type]["parameters"]
    for field in parameters:
        value = values.get(field)
        st.session_state[field_key(report_type, field)] = "" if value in {None, ""} else f"{float(value):g}"


def parse_qr_payload(raw: str, report_type: Optional[str] = None) -> Tuple[Dict[str, Any], str]:
    """Parses QR payload text. Returns (values, resolved_report_type).
    The payload may declare its own report_type (e.g. {"report_type":"lipid","values":{...}}),
    which takes priority — otherwise falls back to the currently selected report type."""
    text = (raw or "").strip()
    if not text:
        raise ValueError("The QR code did not contain readable report data.")

    if text.startswith("http://") or text.startswith("https://"):
        parsed = urllib.parse.urlparse(text)
        query = urllib.parse.parse_qs(parsed.query)
        encoded = query.get("report", query.get("cbc", query.get("data", [""])))[0]
        if encoded:
            padded = encoded + "=" * (-len(encoded) % 4)
            text = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8")

    payload = json.loads(text)
    resolved_type = payload.get("report_type") if isinstance(payload, dict) else None
    if resolved_type not in REPORT_TYPES:
        resolved_type = report_type or st.session_state.get("report_type", DEFAULT_REPORT_TYPE)

    if isinstance(payload, dict) and "values" in payload:
        payload = payload["values"]

    parameters = REPORT_TYPES[resolved_type]["parameters"]
    payload_lower = {str(k).strip().lower(): v for k, v in payload.items()} if isinstance(payload, dict) else {}
    values: Dict[str, Any] = {}
    for field, definition in parameters.items():
        candidates = [field] + list(definition.get("aliases", []))
        found = None
        for candidate in candidates:
            candidate_key = candidate.strip().lower()
            if candidate_key in payload_lower and payload_lower[candidate_key] not in {None, ""}:
                found = payload_lower[candidate_key]
                break
        values[field] = float(found) if found is not None else None
    return values, resolved_type


def _qr_image_variants(image: "Image.Image") -> List["Image.Image"]:
    """Build a handful of preprocessed variants of the source image so a real,
    slightly blurry/angled/poorly-lit camera photo has a realistic chance of
    decoding — a single raw-frame attempt (the old behavior) fails constantly
    on real-world photos even when the QR code is perfectly scannable."""
    from PIL import ImageEnhance, ImageOps

    variants = [image]

    gray = ImageOps.grayscale(image)
    variants.append(gray)

    # Autocontrast helps with poor lighting / low-contrast prints.
    try:
        autocontrasted = ImageOps.autocontrast(gray, cutoff=2)
        variants.append(autocontrasted)
    except Exception:
        autocontrasted = gray

    # Sharpen + boost contrast — helps slightly blurry or low-res phone photos.
    sharpened = None
    try:
        sharpened = ImageEnhance.Sharpness(autocontrasted).enhance(2.2)
        sharpened = ImageEnhance.Contrast(sharpened).enhance(1.7)
        variants.append(sharpened)
    except Exception:
        pass

    # Upscale — unconditional, not just for small images. A QR that occupies
    # only a small corner of a large photographed page is still effectively
    # low-resolution even though the overall image is large.
    w, h = image.size
    base_for_scaling = sharpened or autocontrasted or gray
    for factor in (1.6, 2.4):
        try:
            variants.append(base_for_scaling.resize((int(w * factor), int(h * factor)), Image.LANCZOS))
        except Exception:
            pass

    # Ensure at least a reasonably-sized version exists even without the above.
    if max(w, h) < 700:
        scale = 700 / max(w, h)
        try:
            variants.append(gray.resize((int(w * scale), int(h * scale)), Image.LANCZOS))
        except Exception:
            pass

    return variants


def decode_qr_image(image_bytes: bytes) -> Optional[str]:
    try:
        base_image = Image.open(io.BytesIO(image_bytes))
        base_image = ImageOps_exif_transpose(base_image)
        base_image = base_image.convert("RGB")
    except Exception:
        return None

    for variant in _qr_image_variants(base_image):
        if pyzbar_decode is not None:
            try:
                decoded = pyzbar_decode(variant)
                if decoded:
                    return decoded[0].data.decode("utf-8")
            except Exception as exc:  # pragma: no cover
                logger_qr.debug("pyzbar decode failed on a variant: %s", exc)

        if cv2 is not None and np is not None:
            try:
                arr = cv2.cvtColor(np.array(variant.convert("RGB")), cv2.COLOR_RGB2BGR)
                detector = cv2.QRCodeDetector()
                data, _, _ = detector.detectAndDecode(arr)
                if data:
                    return data
                ok, decoded_list, _, _ = detector.detectAndDecodeMulti(arr)
                if ok:
                    for item in decoded_list:
                        if item:
                            return item
            except Exception as exc:  # pragma: no cover
                logger_qr.debug("cv2 decode failed on a variant: %s", exc)

    return None


def ImageOps_exif_transpose(image: "Image.Image") -> "Image.Image":
    """Correct orientation using EXIF data — phone camera photos are very
    commonly stored rotated, which silently breaks QR detection."""
    from PIL import ImageOps

    try:
        return ImageOps.exif_transpose(image) or image
    except Exception:
        return image


def qr_decoder_available() -> bool:
    return pyzbar_decode is not None or (cv2 is not None and np is not None)


# ── Display helpers ───────────────────────────────────────────────────────────

def to_display_value(metric: Dict[str, Any], value: Any) -> str:
    if value is None:
        return "—"
    divisor = float(metric.get("display_divisor", 1.0))
    return f"{value / divisor:g} {metric.get('display_unit', metric['unit'])}"


def to_display_range(metric: Dict[str, Any]) -> str:
    ref = metric["reference_range"]
    divisor = float(metric.get("display_divisor", 1.0))
    unit = metric.get("display_unit", ref["unit"])
    return f"{ref['low'] / divisor:g} – {ref['high'] / divisor:g} {unit}"


def pretty_status(status: str) -> str:
    return {"high": "High ↑", "low": "Low ↓", "normal": "Normal", "missing": "—"}.get(status, status.title())


def status_badge_style(status: str) -> Dict[str, str]:
    return {
        "normal":  {"bg": "#e9f6ee", "text": "#14603f"},
        "low":     {"bg": "#e6f1fb", "text": "#0c447c"},
        "high":    {"bg": "#fceeed", "text": "#a3241d"},
        "missing": {"bg": "#eef1f4", "text": "#5f6b7a"},
    }.get(status, {"bg": "#eef1f4", "text": "#5f6b7a"})


def status_chip_style(status: str) -> Dict[str, str]:
    if status == "Normal":
        return {"bg": "#e9f6ee", "text": "#14603f"}
    if status == "Mild Abnormality":
        return {"bg": "#fef6e6", "text": "#8a5a06"}
    if status == "Moderate Abnormality":
        return {"bg": "#fdeee0", "text": "#a1470f"}
    return {"bg": "#fceeed", "text": "#a3241d"}


def severity_border_color(severity: str) -> str:
    return {"mild": "#c99a1a", "moderate": "#185fa5", "significant": "#a3241d"}.get(severity, "#185fa5")


def gauge_position(value: Optional[float], low: float, high: float) -> float:
    """Returns 0.0–1.0 representing where on the full gauge track the needle sits."""
    if value is None:
        return 0.5
    spread = high - low
    margin = spread * 0.35
    track_low = low - margin
    track_high = high + margin
    clamped = max(track_low, min(track_high, value))
    return (clamped - track_low) / (track_high - track_low)


def abnormal_parameters_first(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    order = {"high": 0, "low": 1, "normal": 2, "missing": 3}
    return sorted(list(result["parameters"].values()), key=lambda item: (order[item["status"]], item["label"]))


def abnormal_only(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [item for item in abnormal_parameters_first(result) if item["status"] in {"low", "high"}]


def lifestyle_recommendations(result: Dict[str, Any]) -> List[Dict[str, str]]:
    if result.get("report_type", "cbc") != "cbc":
        summary = result["clinical_summary"]
        cards = [{"title": "What you can do", "body": item} for item in summary["what_you_can_do"]]
        if not cards:
            cards.append({"title": "Keep the baseline strong", "body": "These values look broadly reassuring. Keep this report as a baseline for future comparisons."})
        return cards

    params = result["parameters"]
    cards: List[Dict[str, str]] = []
    if params["hemoglobin"]["status"] == "low":
        cards.append({
            "title": "Support iron and blood building",
            "body": "Add iron-rich foods like spinach, beans, lentils, eggs, fish, or lean meat. Pair iron meals with vitamin C foods like lemon, amla, guava, or oranges.",
        })
    if params["mcv"]["status"] == "low" or params["mch"]["status"] == "low":
        cards.append({
            "title": "Ask about iron deficiency",
            "body": "Small red blood cells can go with low iron. Ask whether ferritin, B12, folate, or iron studies are needed.",
        })
    if params["wbc"]["status"] == "high":
        cards.append({
            "title": "Give the body recovery support",
            "body": "Hydrate well, rest, and note fever, cough, burning urine, pain, or any infection symptoms to discuss with a clinician.",
        })
    if params["wbc"]["status"] == "low" or params["neutrophils"]["status"] == "low":
        cards.append({
            "title": "Reduce infection exposure",
            "body": "Wash hands often, avoid close contact with sick people, and seek medical advice quickly if fever develops.",
        })
    if params["platelets"]["status"] == "low":
        cards.append({
            "title": "Be gentle until reviewed",
            "body": "Avoid unnecessary painkillers or blood-thinning medicines unless prescribed. Watch for easy bruising, nosebleeds, or gum bleeding.",
        })
    if params["platelets"]["status"] == "high":
        cards.append({
            "title": "Discuss clotting risk",
            "body": "Stay hydrated and ask the doctor whether inflammation, iron deficiency, or repeat platelet testing should be checked.",
        })
    if not cards:
        cards.append({
            "title": "Keep the baseline strong",
            "body": "Your provided CBC values look broadly reassuring. Keep regular meals, sleep, hydration, movement, and compare future reports with this baseline.",
        })
    return cards


def plain_language_overview(result: Dict[str, Any]) -> str:
    abnormalities = abnormal_only(result)
    if not abnormalities and not result["patterns"]:
        return "Most checked values are within the expected range. Keep this report as a useful baseline for future visits."
    names = ", ".join(item["label"] for item in abnormalities[:4])
    suffix = " and a few others" if len(abnormalities) > 4 else ""
    return f"The main values to review are {names}{suffix}. This does not diagnose a condition, but it gives your doctor a focused starting point."


def doctor_brief(result: Dict[str, Any]) -> Dict[str, List[str]]:
    abnormalities = abnormal_only(result)

    if result.get("report_type", "cbc") != "cbc":
        changed = (
            [f"{item['label']}: {to_display_value(item, item['value'])} ({pretty_status(item['status'])})" for item in abnormalities[:5]]
            or ["No abnormal values were detected from the values entered."]
        )
        questions = [f"What does the {p['name']} pattern mean for me?" for p in result["patterns"][:2]] or [
            "How often should I repeat this panel if I feel well?"
        ]
        foods = result["clinical_summary"]["what_you_can_do"][:3]
        return {"changed": changed, "questions": questions, "foods": foods}

    changed = []
    if abnormalities:
        for item in abnormalities[:5]:
            changed.append(f"{item['label']}: {to_display_value(item, item['value'])} ({pretty_status(item['status'])})")
    else:
        changed.append("No abnormal CBC parameters were detected from the values entered.")

    questions = []
    params = result["parameters"]
    if params["hemoglobin"]["status"] == "low":
        questions.append("Could this be iron, B12, folate, or blood-loss related?")
    if params["wbc"]["status"] in {"low", "high"}:
        questions.append("Does the WBC pattern fit infection, inflammation, medicine effect, or something else?")
    if params["platelets"]["status"] in {"low", "high"}:
        questions.append("Should platelets be repeated or checked with a peripheral smear?")
    if result["patterns"]:
        questions.append("Which detected pattern matters most for my symptoms and history?")
    if not questions:
        questions.append("How often should I repeat CBC tracking if I feel well?")

    foods = [card["body"] for card in lifestyle_recommendations(result)[:3]]
    return {"changed": changed, "questions": questions, "foods": foods}


# ── History/trend helpers ─────────────────────────────────────────────────────

def result_to_record(profile_id: str, result: Dict[str, Any], stamp: str) -> Dict[str, Any]:
    return {
        "profile_id": profile_id,
        "timestamp": stamp,
        "report_type": result.get("report_type", DEFAULT_REPORT_TYPE),
        "values": result["normalized_input"],
        "results": result,
        "severity": result["overall_status"],
        "patterns": [item["name"] for item in result["patterns"]],
    }


def load_sample_data() -> None:
    """Populates a sample profile with a handful of pre-analyzed reports so a
    first-time visitor (recruiter, professor, anyone clicking the link cold)
    sees a populated app immediately instead of an empty History/Trends tab."""
    profile_id = "sample_demo"
    st.session_state.profile = {
        "name": "Sample Patient",
        "age_raw": "29",
        "gender": "Female",
        "weight_raw": "58",
        "profile_id": profile_id,
    }
    st.session_state.report_type = "cbc"

    samples = [
        (30, "cbc", {
            "age": 29, "sex": "female", "hemoglobin": 10.6, "rbc": 4.1, "hematocrit": 34,
            "mcv": 72, "mch": 24, "mchc": 31, "wbc": 7200, "neutrophils": 56, "lymphocytes": 33,
            "monocytes": 6, "eosinophils": 4, "basophils": 1, "platelets": 295000,
        }),
        (14, "cbc", {
            "age": 29, "sex": "female", "hemoglobin": 11.8, "rbc": 4.3, "hematocrit": 37,
            "mcv": 78, "mch": 26, "mchc": 32, "wbc": 7000, "neutrophils": 55, "lymphocytes": 34,
            "monocytes": 6, "eosinophils": 4, "basophils": 1, "platelets": 300000,
        }),
        (1, "cbc", {
            "age": 29, "sex": "female", "hemoglobin": 12.6, "rbc": 4.5, "hematocrit": 39,
            "mcv": 82, "mch": 27, "mchc": 33, "wbc": 6900, "neutrophils": 54, "lymphocytes": 35,
            "monocytes": 6, "eosinophils": 4, "basophils": 1, "platelets": 305000,
        }),
        (7, "lipid", {
            "age": 29, "sex": "female", "total_cholesterol": 238, "ldl": 152, "hdl": 42,
            "triglycerides": 210, "vldl": 34,
        }),
        (7, "lft", {
            "age": 29, "sex": "female", "total_bilirubin": 0.8, "direct_bilirubin": 0.2,
            "sgot": 32, "sgpt": 38, "alp": 95, "total_protein": 7.1, "albumin": 4.3, "globulin": 2.8,
        }),
    ]

    store = load_history_store()
    records = []
    for days_ago, report_type, payload in samples:
        result = analyze_report(payload, report_type)
        stamp = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M")
        records.append(result_to_record(profile_id, result, stamp))
    store[profile_id] = records
    save_history_store(store)

    latest = sorted(records, key=lambda r: r["timestamp"])[-1]
    st.session_state.last_result = latest["results"]
    st.session_state.last_report_date = latest["timestamp"]
    st.session_state.dashboard_tab = "Results"


def save_report_history(profile_id: str, result: Dict[str, Any]) -> str:
    store = load_history_store()
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    store.setdefault(profile_id, []).append(result_to_record(profile_id, result, stamp))
    save_history_store(store)
    return stamp


def get_profile_reports(profile_id: str) -> List[Dict[str, Any]]:
    if not profile_id.strip():
        return []
    return sorted(
        load_history_store().get(profile_id.strip(), []),
        key=lambda item: item["timestamp"],
        reverse=True,
    )


def delete_report(profile_id: str, timestamp: str) -> None:
    store = load_history_store()
    if profile_id in store:
        store[profile_id] = [r for r in store[profile_id] if r["timestamp"] != timestamp]
        save_history_store(store)


def build_trend_frame(reports: List[Dict[str, Any]], metric_key: str, report_type: str = DEFAULT_REPORT_TYPE) -> pd.DataFrame:
    parameters = REPORT_TYPES[report_type]["parameters"]
    divisor = float(parameters[metric_key].get("display_divisor", 1.0))
    rows = []
    for idx, report in enumerate(sorted(reports, key=lambda item: item["timestamp"]), start=1):
        value = report["values"].get(metric_key)
        if value is None:
            continue
        value = value / divisor
        rows.append({
            "Visit": idx,
            "Date": datetime.strptime(report["timestamp"], "%Y-%m-%d %H:%M").strftime("%d %b"),
            parameters[metric_key]["label"]: round(value, 2),
        })
    return pd.DataFrame(rows)


def trend_insight(reports: List[Dict[str, Any]], metric_key: str, report_type: str = DEFAULT_REPORT_TYPE) -> str:
    parameters = REPORT_TYPES[report_type]["parameters"]
    values = [
        float(r["values"][metric_key])
        for r in sorted(reports, key=lambda i: i["timestamp"])
        if r["values"].get(metric_key) is not None
    ]
    label = parameters[metric_key]["label"]
    if len(values) < 2:
        return f"{label} trend needs at least two data points."
    first, last = values[0], values[-1]
    if first == 0:
        return f"{label} trend is difficult to assess."
    ratio = (last - first) / abs(first)
    threshold = 0.08 if parameters[metric_key].get("display_divisor", 1.0) != 1.0 else 0.05
    if ratio > threshold:
        return f"{label} is increasing {'slightly ' if ratio < threshold * 2 else ''}over time."
    if ratio < -threshold:
        return f"{label} is decreasing {'slightly ' if abs(ratio) < threshold * 2 else ''}over time."
    return f"{label} appears stable across reports."


def summarize_cross_trends(reports: List[Dict[str, Any]], report_type: str = DEFAULT_REPORT_TYPE) -> str:
    if len(reports) < 2:
        return "Add at least two reports to start seeing trajectory-level trend summaries."
    groups = REPORT_TYPES[report_type]["groups"]
    headline_fields = groups[0]["fields"][:3] if groups else []
    parts = [trend_insight(reports, key, report_type) for key in headline_fields]
    return "  ·  ".join(parts)


def classify_overall_trend(reports: List[Dict[str, Any]]) -> str:
    if len(reports) < 2:
        return "Stable"
    ordered = sorted(reports, key=lambda item: item["timestamp"])
    rank = {"Normal": 0, "Mild Abnormality": 1, "Moderate Abnormality": 2, "Significant Concern": 3}
    prev, curr = ordered[-2]["results"]["overall_status"], ordered[-1]["results"]["overall_status"]
    if rank[curr] < rank[prev]:
        return "Improving"
    if rank[curr] > rank[prev]:
        return "Worsening"
    return "Stable"


def risk_signals_from_result(result: Dict[str, Any]) -> List[str]:
    report_type = result.get("report_type", DEFAULT_REPORT_TYPE)
    report_label = REPORT_TYPES.get(report_type, REPORT_TYPES[DEFAULT_REPORT_TYPE])["short_label"]
    if result["patterns"]:
        return [f"{p['name']}: {p['simple_explanation']}" for p in result["patterns"]]
    abnormalities = abnormal_only(result)
    if abnormalities:
        return [
            f"{item['label']} is {pretty_status(item['status']).lower()} ({to_display_value(item, item['value'])})."
            for item in abnormalities[:5]
        ]
    return [f"No immediate {report_label} risk signals detected from the latest report."]


def next_steps_from_reports(reports: List[Dict[str, Any]]) -> List[str]:
    if not reports:
        return ["Add a report to start getting timeline recommendations."]
    latest = reports[0]["results"]
    report_type = latest.get("report_type", DEFAULT_REPORT_TYPE)
    if latest["patterns"]:
        steps: List[str] = []
        for pattern in latest["patterns"]:
            for action in pattern["actions"]:
                if action not in steps:
                    steps.append(action)
        return steps[:5]
    return [f"Continue periodic {REPORT_TYPES.get(report_type, REPORT_TYPES[DEFAULT_REPORT_TYPE])['short_label']} tracking and compare future reports against this baseline."]


def metric_change_text(previous: Optional[float], current: Optional[float], key: str, report_type: str = DEFAULT_REPORT_TYPE) -> str:
    parameters = REPORT_TYPES[report_type]["parameters"]
    if previous is None or current is None:
        return f"{parameters[key]['label']}: incomplete data."
    divisor = float(parameters[key].get("display_divisor", 1.0))
    prev = previous / divisor
    curr = current / divisor
    unit = parameters[key].get("display_unit", parameters[key]["unit"])
    if curr > prev:
        arrow, color = "↑", "#1a6644"
    elif curr < prev:
        arrow, color = "↓", "#a3241d"
    else:
        arrow, color = "→", "#5f6b7a"
    diff = abs(curr - prev)
    return f"<span style='color:{color};font-weight:700'>{arrow} {parameters[key]['label']}</span>: {prev:g} → {curr:g} {unit} &nbsp;<span style='color:{color};font-size:.8rem'>(Δ {diff:g})</span>"


def trajectory_sections(reports: List[Dict[str, Any]]) -> List[str]:
    sections = []
    for idx, report in enumerate(sorted(reports, key=lambda item: item["timestamp"]), start=1):
        report_type = report.get("report_type", DEFAULT_REPORT_TYPE)
        parameters = REPORT_TYPES.get(report_type, REPORT_TYPES[DEFAULT_REPORT_TYPE])["parameters"]
        headline_fields = REPORT_TYPES.get(report_type, REPORT_TYPES[DEFAULT_REPORT_TYPE])["groups"][0]["fields"][:3]
        values = report["values"]
        narrative = []
        for field in headline_fields:
            val = values.get(field)
            if val is None:
                continue
            divisor = float(parameters[field].get("display_divisor", 1.0))
            display = val / divisor
            narrative.append(f"{parameters[field]['label']} {display:g}")
        pattern_text = ", ".join(report["patterns"]) if report["patterns"] else "no pattern detected"
        pretty = datetime.strptime(report["timestamp"], "%Y-%m-%d %H:%M").strftime("%d %b %Y")
        sections.append(f"<strong>Visit {idx}</strong> ({pretty}): {', '.join(narrative) or '—'}. Status: {report['severity']}. Pattern: {pattern_text}.")
    return sections


# ── Validation ────────────────────────────────────────────────────────────────

def validate_numeric_inputs(patient: Dict[str, Any], fields: Dict[str, Any], report_type: str = DEFAULT_REPORT_TYPE) -> Optional[str]:
    parameters = REPORT_TYPES[report_type]["parameters"]
    if not patient["name"].strip():
        return "Name is required."
    if not patient["profile_id"].strip():
        return "Profile ID is required."
    if parse_required_age(patient["age_raw"]) is None:
        return "Age is required."
    if patient["sex"] is None:
        return "Please select gender."
    try:
        parse_required_age(patient["age_raw"])
    except ValueError:
        return "Age must be a valid number."
    if str(patient["weight_raw"]).strip():
        try:
            parse_optional_number(patient["weight_raw"])
        except ValueError:
            return "Weight must be a valid number."
    for field, raw in fields.items():
        if raw is None or str(raw).strip() == "":
            continue
        try:
            float(raw)
        except ValueError:
            return f"{parameters[field]['label']} must be a valid number."
    if all(raw is None or str(raw).strip() == "" for raw in fields.values()):
        return "Enter at least one value before analyzing — an empty report can't be meaningfully assessed."
    return None


def normalize_payload(patient: Dict[str, Any], fields: Dict[str, Any], report_type: str = DEFAULT_REPORT_TYPE) -> Dict[str, Any]:
    parameters = REPORT_TYPES[report_type]["parameters"]
    payload = {
        "name": patient["name"].strip() or None,
        "age": parse_required_age(patient["age_raw"]),
        "sex": patient["sex"].lower() if patient["sex"] else None,
        "weight": parse_optional_number(patient["weight_raw"]),
    }
    for field in parameters:
        raw = fields.get(field)
        payload[field] = None if raw is None or str(raw).strip() == "" else float(raw)
    return payload


def build_csv_export(reports: List[Dict[str, Any]]) -> str:
    rows = []
    for r in sorted(reports, key=lambda x: x["timestamp"]):
        report_type = r.get("report_type", DEFAULT_REPORT_TYPE)
        parameters = REPORT_TYPES.get(report_type, REPORT_TYPES[DEFAULT_REPORT_TYPE])["parameters"]
        row: Dict[str, Any] = {
            "date": r["timestamp"],
            "report_type": REPORT_TYPES.get(report_type, REPORT_TYPES[DEFAULT_REPORT_TYPE])["short_label"],
            "severity": r["severity"],
        }
        for key in parameters:
            val = r["values"].get(key)
            row[parameters[key]["label"]] = val if val is not None else ""
        row["patterns"] = "; ".join(r["patterns"]) if r["patterns"] else ""
        rows.append(row)
    return pd.DataFrame(rows).to_csv(index=False)



# ── UI Rendering ──────────────────────────────────────────────────────────────

def render_gauge(value: Optional[float], low: float, high: float, status: str, display_divisor: float = 1.0) -> str:
    pos = gauge_position(value, low, high) if value is not None else 0.5
    pct = round(pos * 100, 1)
    colors = {
        "low": "#185fa5",
        "high": "#185fa5",
        "normal": "#1a7f5a",
        "missing": "#b0a8a0",
    }
    color = colors.get(status, "#b0a8a0")
    # Normal zone
    spread = high - low
    margin = spread * 0.35
    track_low = low - margin
    track_high = high + margin
    normal_start = round((low - track_low) / (track_high - track_low) * 100, 1)
    normal_end = round((high - track_low) / (track_high - track_low) * 100, 1)
    low_disp = f"{low / display_divisor:g}"
    high_disp = f"{high / display_divisor:g}"

    return f"""
    <div class="gauge-wrap">
      <div class="gauge-track">
        <div style="position:absolute;top:0;left:{normal_start}%;width:{normal_end - normal_start}%;height:100%;background:rgba(26,127,90,.15);border-radius:999px;"></div>
        <div class="gauge-needle" style="left:{pct}%;background:{color};"></div>
      </div>
      <div class="gauge-labels"><span>Low</span><span>Normal {low_disp}–{high_disp}</span><span>High</span></div>
    </div>
    """


def render_metric_card(item: Dict[str, Any]) -> None:
    status = item["status"]
    style = status_badge_style(status)
    ref = item["reference_range"]
    divisor = float(item.get("display_divisor", 1.0))
    accent_colors = {"low": "#185fa5", "high": "#185fa5", "normal": "#1a7f5a", "missing": "#dfe3e8"}
    accent = accent_colors.get(status, "#dfe3e8")
    val_str = to_display_value(item, item["value"])
    ref_str = to_display_range(item)
    gauge_html = render_gauge(item["value"], ref["low"], ref["high"], status, divisor) if item["value"] is not None else ""
    badge = f"<span class='badge' style='background:{style['bg']};color:{style['text']};'>{pretty_status(status)}</span>"
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-card-accent" style="background:{accent};"></div>
      <div class="metric-label">{item['label']} &nbsp;·&nbsp; {item['group']}</div>
      <div class="metric-value-large" style="color:{accent};">{val_str}</div>
      {badge}
      {gauge_html}
      <div class="metric-ref">Reference: {ref_str}</div>
    </div>
    """, unsafe_allow_html=True)


def render_pattern_card(pattern: Dict[str, Any]) -> None:
    border = severity_border_color(pattern["severity"])
    sev_colors = {"mild": "#fef6e6", "moderate": "#fdeee0", "significant": "#fceeed"}
    sev_text = {"mild": "#8a5a06", "moderate": "#a1470f", "significant": "#a3241d"}
    bg = sev_colors.get(pattern["severity"], "#fff")
    tc = sev_text.get(pattern["severity"], "#333")
    causes_html = "".join(f"<div class='pattern-item'>{c}</div>" for c in pattern["possible_causes"])
    actions_html = "".join(f"<div class='pattern-item'>{a}</div>" for a in pattern["actions"])
    st.markdown(f"""
    <div class="pattern-card" style="border-left-color:{border};">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:.8rem;flex-wrap:wrap;margin-bottom:.5rem;">
        <div class="pattern-name">{pattern['name']}</div>
        <span class="badge" style="background:{bg};color:{tc};flex-shrink:0;">{pattern['severity'].capitalize()}</span>
      </div>
      <div class="pattern-body">{pattern['simple_explanation']}</div>
      <div class="pattern-causes">
        <div class="pattern-causes-title">Possible Causes</div>
        {causes_html}
      </div>
      <div class="pattern-actions">
        <div class="pattern-actions-title">What To Do</div>
        {actions_html}
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_summary_blocks(summary: Dict[str, Any]) -> None:
    items = [
        ("Overview", summary["overview"]),
        ("Explanation", summary["explanation"]),
        ("Possible Causes", "<br>".join(f"· {x}" for x in summary["possible_causes"])),
        ("Recommended Actions", "<br>".join(f"· {x}" for x in summary["what_you_can_do"])),
        ("Severity Note", summary["severity_statement"]),
    ]
    for heading, content in items:
        st.markdown(f"""
        <div class="summary-block">
          <div class="summary-block-title">{heading}</div>
          <div class="summary-block-body">{content}</div>
        </div>
        """, unsafe_allow_html=True)


# ── Page renders ──────────────────────────────────────────────────────────────

def render_lifestyle_guidance(result: Dict[str, Any]) -> None:
    st.markdown(f"<div class='status-note'>{plain_language_overview(result)}</div>", unsafe_allow_html=True)

    cards = lifestyle_recommendations(result)
    items_html = "".join(f"<li>{card['body']}</li>" for card in cards)
    st.markdown(f"""
    <div class="lifestyle-card">
      <div class="lifestyle-title">What You Can Do</div>
      <ul>{items_html}</ul>
    </div>
    """, unsafe_allow_html=True)


def render_doctor_brief(result: Dict[str, Any]) -> None:
    brief = doctor_brief(result)
    changed = "<br>".join(f"- {item}" for item in brief["changed"])
    questions = "<br>".join(f"- {item}" for item in brief["questions"])
    foods = "<br>".join(f"- {item}" for item in brief["foods"])
    st.markdown(f"""
    <div class="doctor-brief">
      <div class="doctor-brief-title">Before You See the Doctor</div>
      <div class="card-sub">A short summary to bring up at your next visit.</div>
      <div class="brief-grid">
        <div class="brief-box">
          <div class="brief-box-title">What changed</div>
          <div class="brief-box-body">{changed}</div>
        </div>
        <div class="brief-box">
          <div class="brief-box-title">What to ask</div>
          <div class="brief-box-body">{questions}</div>
        </div>
        <div class="brief-box">
          <div class="brief-box-title">What to eat / do</div>
          <div class="brief-box-body">{foods}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_identity_screen() -> None:
    st.markdown('<div class="identity-wrap">', unsafe_allow_html=True)
    st.markdown("""
    <div class="identity-card">
      <div class="identity-eyebrow">Rule-Based Lab Report Interpretation</div>
      <div class="identity-headline">LabLens</div>
      <div class="identity-body">
        Upload or enter values from CBC, Lipid, Liver, Kidney, Thyroid, or Blood Sugar reports and get an
        instant, explainable breakdown — powered by a transparent, rule-based interpretation engine, not a black-box model.
      </div>
      <div class="trust-row">
        <div class="trust-pill"><strong>PDF Auto-Extract</strong>Upload any standard lab report PDF — the type is auto-detected.</div>
        <div class="trust-pill"><strong>QR Import</strong>Scan a report QR code from camera or uploaded image.</div>
        <div class="trust-pill"><strong>Report Vault</strong>Keep X-rays, MRIs, prescriptions and more in one place.</div>
      </div>
      <div class="identity-divider"></div>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        col1, col2 = st.columns(2, gap="medium")
        with col1:
            name = st.text_input("Full Name", placeholder="Your name")
            age_raw = st.text_input("Age", placeholder="e.g. 28")
            profile_id = st.text_input("Profile ID", placeholder="Create a unique ID, e.g. rohan_1")
        with col2:
            gender = st.selectbox(
                "Biological Sex",
                [None, "Male", "Female"],
                format_func=lambda v: "Select" if v is None else v,
            )
            weight_raw = st.text_input("Weight (optional)", placeholder="kg")
            st.markdown("<div style='height:1.9rem'></div>", unsafe_allow_html=True)
            if st.button("Continue →", use_container_width=True, type="primary"):
                if not name.strip() or not age_raw.strip() or gender is None or not profile_id.strip():
                    st.error("Name, Age, Biological Sex, and Profile ID are required.")
                else:
                    st.session_state.profile = {
                        "name": name.strip(),
                        "age_raw": age_raw.strip(),
                        "gender": gender,
                        "weight_raw": weight_raw.strip(),
                        "profile_id": profile_id.strip(),
                    }
                    st.session_state.current_page = "dashboard"
                    st.rerun()

        st.markdown("<div style='height:.3rem'></div>", unsafe_allow_html=True)
        if st.button("Or, load sample data to explore →", use_container_width=True):
            load_sample_data()
            st.session_state.current_page = "dashboard"
            st.rerun()

    st.markdown("""
    <div class="disclaimer-note">
      LabLens is an educational project for exploring patterns in lab report data. It is not a medical
      device, does not provide a diagnosis, and is not a substitute for advice from a qualified healthcare
      professional. Reference ranges shown are configured defaults and may differ from the range printed on
      your actual lab report — always check with the reporting lab.
    </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_sidebar() -> None:
    with st.sidebar:
        profile = current_profile()
        st.markdown(f"""
        <div class="sidebar-brand">
          <div class="sidebar-brand-name">LabLens</div>
        </div>
        <div class="sidebar-profile">Profile: <strong style="color:#f5b699!important">{profile['profile_id']}</strong></div>
        """, unsafe_allow_html=True)

        current_tab = LEGACY_NAV_MAP.get(st.session_state.dashboard_tab, st.session_state.dashboard_tab)
        if current_tab not in NAV_ITEMS:
            current_tab = NAV_ITEMS[0]

        nav_icons = {"Add Report": "＋", "Results": "◈", "History": "◷", "Trends": "↗", "Insights": "◎", "Vault": "▤"}
        nav_labels = [f"{nav_icons.get(n, '')}  {n}" for n in NAV_ITEMS]
        selected_idx = NAV_ITEMS.index(current_tab)
        selection = st.radio("Navigation", nav_labels, index=selected_idx, label_visibility="collapsed")
        clean = selection.split("  ", 1)[-1].strip() if "  " in selection else selection
        st.session_state.dashboard_tab = clean

        st.divider()

        reports = get_profile_reports(profile["profile_id"])
        n = len(reports)
        if n > 0:
            last_sev = reports[0]["severity"]
            sty = status_chip_style(last_sev)
            st.markdown(f"""
            <div style="padding:.5rem .2rem;font-size:.8rem;color:#8a8480;">
              <div>{n} report{'s' if n != 1 else ''} saved</div>
              <div style="margin-top:.3rem;">Last: <span style="color:{sty['text']};font-weight:700">{last_sev}</span></div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown('<div style="padding:.5rem .2rem;font-size:.8rem;color:#8a8480;">No reports yet</div>', unsafe_allow_html=True)

        st.divider()
        if st.button("Switch Profile", use_container_width=True):
            st.session_state.current_page = "identity"
            st.rerun()


def render_profile_strip() -> None:
    p = current_profile()
    reports = get_profile_reports(p["profile_id"])
    report_count = len(reports)
    st.markdown(f"""
    <div class="profile-strip">
      <div class="profile-chip">
        <span class="profile-chip-label">Name</span>
        <span class="profile-chip-value">{p['name']}</span>
      </div>
      <div class="profile-chip">
        <span class="profile-chip-label">Age</span>
        <span class="profile-chip-value">{p['age_raw']} yrs</span>
      </div>
      <div class="profile-chip">
        <span class="profile-chip-label">Sex</span>
        <span class="profile-chip-value">{p['gender']}</span>
      </div>
      <div class="profile-chip">
        <span class="profile-chip-label">Profile ID</span>
        <span class="profile-chip-value">{p['profile_id']}</span>
      </div>
      <div class="profile-chip" style="margin-left:auto;">
        <span class="profile-chip-label">Reports Saved</span>
        <span class="profile-chip-value">{report_count}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)


def handle_qr_scan() -> None:
    report_type = st.session_state.report_type
    st.markdown(f"""
    <div class="input-section">
      <div class="input-section-title">QR Report Scan</div>
      <div class="card-sub">Use the camera or upload a QR image of a real {REPORT_TYPES[report_type]['label']} report. Values will fill the review form below.</div>
    </div>
    """, unsafe_allow_html=True)

    if not qr_decoder_available():
        st.warning("Live QR decoding needs `opencv-python-headless` or `pyzbar` installed (see requirements.txt / packages.txt).")

    cam_col, upload_col = st.columns(2, gap="medium")
    with cam_col:
        captured = st.camera_input("Scan report QR with camera")
    with upload_col:
        qr_image = st.file_uploader("Upload QR image", type=["png", "jpg", "jpeg"], key="qr_image_upload")

    image_source = captured or qr_image
    if image_source is not None:
        image_bytes = image_source.getvalue()
        image_id = f"{getattr(image_source, 'name', 'camera')}:{len(image_bytes)}"
        if image_id != st.session_state.qr_last_image_id:
            st.session_state.qr_last_image_id = image_id
            with st.spinner("Reading QR code…"):
                payload_text = decode_qr_image(image_bytes)
            if not payload_text:
                st.warning("QR code was not detected clearly. Try better lighting, hold it flatter to the camera, or use manual entry below.")
            else:
                try:
                    values, resolved_type = parse_qr_payload(payload_text, report_type=report_type)
                    if resolved_type != report_type:
                        st.session_state.report_type = resolved_type
                        clear_parameter_fields(resolved_type)
                        report_type = resolved_type
                        st.info(f"This QR code is for a {REPORT_TYPES[resolved_type]['label']} report — switched the form to match.")
                    st.session_state.qr_payload_text = payload_text
                    st.session_state.qr_values = values
                    set_parameter_fields(values, report_type)
                    found = sum(1 for v in values.values() if v is not None)
                    st.success(f"QR scanned successfully. Filled {found}/{len(REPORT_TYPES[report_type]['parameters'])} values.")
                except Exception as exc:
                    st.error(f"QR data could not be read: {exc}")

    with st.expander("Enter QR data manually"):
        pasted = st.text_area(
            "QR payload (JSON)",
            value=st.session_state.get("qr_payload_text", ""),
            placeholder='{"report_type":"cbc","values":{"hemoglobin":11.2,"rbc":4.1,"wbc":7200,"platelets":310000}}',
            height=90,
        )
        if st.button("Use This Data", use_container_width=True):
            try:
                values, resolved_type = parse_qr_payload(pasted, report_type=report_type)
                if resolved_type != report_type:
                    st.session_state.report_type = resolved_type
                    clear_parameter_fields(resolved_type)
                    report_type = resolved_type
                st.session_state.qr_payload_text = pasted
                st.session_state.qr_values = values
                set_parameter_fields(values, report_type)
                found = sum(1 for v in values.values() if v is not None)
                st.success(f"QR payload accepted. Filled {found}/{len(REPORT_TYPES[report_type]['parameters'])} values.")
            except Exception as exc:
                st.error(f"QR payload is not valid: {exc}")


def handle_pdf_upload() -> None:
    st.markdown("""
    <div class="input-section">
      <div class="input-section-title">PDF Auto-Extract</div>
      <div class="card-sub">Upload any standard lab report PDF — the report type is auto-detected from its contents.</div>
    </div>
    """, unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload report PDF", type=["pdf"], label_visibility="collapsed")
    if uploaded_file is not None and uploaded_file.name != st.session_state.last_uploaded_name:
        with st.spinner("Extracting values from PDF…"):
            extracted = extract_report_from_pdf(uploaded_file.read())
        resolved_type = extracted["report_type"]
        if resolved_type != st.session_state.report_type:
            st.session_state.report_type = resolved_type
            clear_parameter_fields(resolved_type)
        st.session_state.pdf_values = extracted["values"]
        st.session_state.last_uploaded_name = uploaded_file.name
        for key, value in extracted["values"].items():
            st.session_state[field_key(resolved_type, key)] = "" if value is None else f"{value:g}"
        found = sum(1 for v in extracted["values"].items() if v[1] is not None)
        total = len(extracted["values"])
        detected_label = REPORT_TYPES[resolved_type]["label"]
        st.info(f"Detected report type: **{detected_label}** — change the report type above if this looks wrong.")
        if found > 0:
            st.success(f"Extraction complete: **{found}/{total} parameters found.**")
        else:
            st.warning("No values could be extracted automatically. Please enter manually.")

        parameters = REPORT_TYPES[resolved_type]["parameters"]
        extraction_rows = [
            {
                "Parameter": parameters[key]["label"],
                "Extracted Value": f"{value:g} {parameters[key].get('display_unit', parameters[key]['unit'])}" if value is not None else "—",
                "Status": "Found" if value is not None else "Missing — enter manually",
            }
            for key, value in extracted["values"].items()
        ]
        with st.expander(f"Extraction report ({found}/{total} found)", expanded=found < total):
            st.dataframe(pd.DataFrame(extraction_rows), use_container_width=True, hide_index=True)
        if found < total:
            st.caption(f"{total - found} parameter{'s' if total - found != 1 else ''} require manual entry below.")
    elif uploaded_file is not None and any(v is None for v in st.session_state.pdf_values.values()):
        st.info("Some values couldn't be extracted — fill them in manually below.")


def render_parameter_inputs(prefill: Dict[str, Any], report_type: str) -> Dict[str, Any]:
    values: Dict[str, Any] = {}
    groups = REPORT_TYPES[report_type]["groups"]
    parameters = REPORT_TYPES[report_type]["parameters"]
    for section in groups:
        st.markdown(f"""
        <div class="input-section">
          <div class="input-section-title">{section['title']}</div>
        </div>
        """, unsafe_allow_html=True)
        cols = st.columns(3, gap="medium")
        for idx, field in enumerate(section["fields"]):
            definition = parameters[field]
            key = field_key(report_type, field)
            with cols[idx % 3]:
                if key not in st.session_state:
                    st.session_state[key] = "" if prefill.get(field) is None else f"{prefill[field]:g}"
                values[field] = st.text_input(
                    f"{definition['label']}",
                    key=key,
                    placeholder=f"{definition.get('display_unit', definition['unit'])}",
                    help=f"Unit: {definition.get('display_unit', definition['unit'])}",
                )
    return values


@st.dialog("Select Report Type")
def _report_type_dialog() -> None:
    st.caption("Choose which lab report you're adding. You can switch anytime from this screen.")
    type_keys = list(REPORT_TYPES.keys())
    cols = st.columns(3, gap="medium")
    descriptions = {
        "cbc": "Hemoglobin, RBC, WBC, platelets and more.",
        "lipid": "Cholesterol, LDL, HDL, triglycerides.",
        "lft": "Liver enzymes, bilirubin, proteins.",
        "kft": "Kidney markers and electrolytes.",
        "thyroid": "TSH, T3, T4.",
        "blood_sugar": "Fasting sugar, PP sugar, HbA1c.",
    }
    for idx, key in enumerate(type_keys):
        info = REPORT_TYPES[key]
        with cols[idx % 3]:
            st.markdown(f"""
            <div class="type-tile">
              <div class="type-tile-label">{info['short_label']}</div>
              <div class="type-tile-desc">{descriptions.get(key, '')}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Select", key=f"dialog_pick_{key}", use_container_width=True):
                st.session_state.report_type = key
                st.session_state.pdf_values = {}
                st.session_state.qr_values = {}
                st.session_state.last_uploaded_name = None
                clear_parameter_fields(key)
                st.rerun()


def render_add_report() -> None:
    st.markdown("## Add Report")

    report_type = st.session_state.report_type
    type_info = REPORT_TYPES[report_type]
    top_a, top_b = st.columns([4, 1], gap="medium")
    with top_a:
        st.markdown(f"""
        <div class="card-sm" style="display:flex;align-items:center;gap:.6rem;">
          <div>
            <div style="font-size:.76rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);">Report Type</div>
            <div style="font-weight:700;font-size:1.05rem;">{type_info['label']}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    with top_b:
        if st.button("Change", use_container_width=True):
            _report_type_dialog()

    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)

    # Mode selector
    col_a, col_b, col_c = st.columns(3, gap="medium")
    with col_a:
        manual_active = st.session_state.input_method == "manual"
        if st.button(
            "Manual Entry",
            use_container_width=True,
            type="primary" if manual_active else "secondary",
        ):
            st.session_state.input_method = "manual"
            st.session_state.pdf_values = {}
            st.session_state.last_uploaded_name = None
            clear_parameter_fields(report_type)
            st.rerun()
    with col_b:
        pdf_active = st.session_state.input_method == "pdf"
        if st.button(
            "Upload PDF",
            use_container_width=True,
            type="primary" if pdf_active else "secondary",
        ):
            st.session_state.input_method = "pdf"
            st.session_state.pdf_values = {}
            st.session_state.last_uploaded_name = None
            clear_parameter_fields(report_type)
            st.rerun()

    with col_c:
        qr_active = st.session_state.input_method == "qr"
        if st.button(
            "QR Report",
            use_container_width=True,
            type="primary" if qr_active else "secondary",
        ):
            st.session_state.input_method = "qr"
            st.session_state.pdf_values = {}
            st.session_state.qr_values = {}
            st.session_state.last_uploaded_name = None
            clear_parameter_fields(report_type)
            st.rerun()

    if st.session_state.input_method == "pdf":
        handle_pdf_upload()
    elif st.session_state.input_method == "qr":
        handle_qr_scan()

    report_type = st.session_state.report_type  # may have changed inside pdf/qr handlers (auto-detect)

    if st.session_state.input_method == "pdf":
        prefill = st.session_state.pdf_values
    elif st.session_state.input_method == "qr":
        prefill = st.session_state.qr_values
    else:
        prefill = {}
    field_values = render_parameter_inputs(prefill, report_type)
    patient = profile_payload()

    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

    if st.button("Analyze Report", use_container_width=True, type="primary"):
        error = validate_numeric_inputs(patient, field_values, report_type)
        if error:
            st.error(error)
        else:
            with st.spinner("Analyzing…"):
                result = analyze_report(normalize_payload(patient, field_values, report_type), report_type)
            stamp = save_report_history(patient["profile_id"], result)
            st.session_state.last_result = result
            st.session_state.last_report_date = stamp
            st.session_state.show_success_actions = True
            st.toast("Report analyzed and saved.")

    if st.session_state.show_success_actions:
        st.success("Report analyzed and saved. Where would you like to go?")
        a, b = st.columns(2, gap="medium")
        with a:
            if st.button("View Results →", use_container_width=True, type="primary"):
                st.session_state.dashboard_tab = "Results"
                st.session_state.show_success_actions = False
                st.rerun()
        with b:
            if st.button("View History →", use_container_width=True):
                st.session_state.dashboard_tab = "History"
                st.session_state.show_success_actions = False
                st.rerun()


def render_results() -> None:
    result = st.session_state.last_result
    if not result:
        st.info("Analyze a report first to view results.")
        return

    report_type = result.get("report_type", DEFAULT_REPORT_TYPE)
    report_label = REPORT_TYPES.get(report_type, REPORT_TYPES[DEFAULT_REPORT_TYPE])["label"]

    # Overall status banner
    banner = OVERALL_BANNERS[result["overall_status"]]
    dot_colors = {
        "Normal": "#1a7f5a",
        "Mild Abnormality": "#c99a1a",
        "Moderate Abnormality": "#185fa5",
        "Significant Concern": "#a3241d",
    }
    dot = dot_colors.get(result["overall_status"], "#888")
    date_str = st.session_state.last_report_date or ""
    st.markdown(f"""
    <div class="status-banner" style="background:{banner['bg']}; color:{banner['text']};">
      <div class="status-banner-dot" style="background:{dot};box-shadow:0 0 0 3px {dot}33;"></div>
      <div>
        <div class="status-banner-label">Overall {report_label} Status · {date_str}</div>
        <div class="status-banner-value">{result['overall_status']}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    tabs = st.tabs(["Patterns", "Parameters", "Clinical Summary", "All Values", "Guidance"])

    with tabs[0]:
        if result["patterns"]:
            for pattern in result["patterns"]:
                render_pattern_card(pattern)
        else:
            st.markdown("""
            <div class="summary-block">
              <div class="summary-block-title">No Major Pattern Detected</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"<div class='status-note'>No rule-based {report_label} pattern was triggered. This may indicate normal ranges or an atypical combination.</div>", unsafe_allow_html=True)

    with tabs[1]:
        abnormalities = abnormal_only(result)
        if abnormalities:
            st.markdown(f"**{len(abnormalities)} abnormal parameter{'s' if len(abnormalities) != 1 else ''}** detected:")
            cols_per_row = 3
            for start in range(0, len(abnormalities), cols_per_row):
                cols = st.columns(cols_per_row, gap="medium")
                for idx, metric in enumerate(abnormalities[start:start + cols_per_row]):
                    with cols[idx]:
                        render_metric_card(metric)
        else:
            st.markdown("""
            <div class="summary-block">
              <div class="summary-block-title">No Abnormal Parameters</div>
              <div class="summary-block-body">All provided parameters are within the configured reference range.</div>
            </div>
            """, unsafe_allow_html=True)

    with tabs[2]:
        render_summary_blocks(result["clinical_summary"])

    with tabs[3]:
        rows = [
            {
                "Parameter": item["label"],
                "Value": to_display_value(item, item["value"]),
                "Status": pretty_status(item["status"]),
                "Reference Range": to_display_range(item),
                "Group": item["group"],
            }
            for item in abnormal_parameters_first(result)
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with tabs[4]:
        st.markdown("### Diet & Lifestyle Guidance")
        render_lifestyle_guidance(result)
        st.markdown("<div style='height:.9rem'></div>", unsafe_allow_html=True)
        st.markdown("### Before You See the Doctor")
        render_doctor_brief(result)


def render_history() -> None:
    profile_id = current_profile()["profile_id"]
    reports = get_profile_reports(profile_id)
    st.markdown("## Report History")

    if not reports:
        st.info("No saved reports yet. Add a report to start tracking.")
        return

    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

    for idx, report in enumerate(reports):
        sty = status_chip_style(report["severity"])
        report_type = report.get("report_type", DEFAULT_REPORT_TYPE)
        type_info = REPORT_TYPES.get(report_type, REPORT_TYPES[DEFAULT_REPORT_TYPE])
        try:
            pretty_date = datetime.strptime(report["timestamp"], "%Y-%m-%d %H:%M").strftime("%d %b %Y, %I:%M %p")
        except Exception:
            pretty_date = report["timestamp"]

        patterns_text = ", ".join(report["patterns"]) if report["patterns"] else "No pattern detected"
        st.markdown(f"""
        <div class="history-card">
          <div>
            <div class="history-date">{type_info['icon']} {type_info['short_label']} · {pretty_date}</div>
            <div class="history-patterns">Patterns: {patterns_text}</div>
          </div>
          <span class="badge" style="background:{sty['bg']};color:{sty['text']};flex-shrink:0;">
            {report['severity']}
          </span>
        </div>
        """, unsafe_allow_html=True)

        c1, c2 = st.columns([3, 1], gap="small")
        with c1:
            if st.button("Open Report", key=f"open_{idx}", use_container_width=True):
                st.session_state.last_result = report["results"]
                st.session_state.last_report_date = report["timestamp"]
                st.session_state.dashboard_tab = "Results"
                st.rerun()
        with c2:
            if st.button("Delete", key=f"del_{idx}", use_container_width=True):
                delete_report(profile_id, report["timestamp"])
                st.toast("Report deleted.")
                st.rerun()


def render_trends() -> None:
    all_reports = get_profile_reports(current_profile()["profile_id"])
    st.markdown("## Trends")

    if not all_reports:
        st.info("Add at least one report to start tracking trends.")
        return

    available_types = sorted({r.get("report_type", DEFAULT_REPORT_TYPE) for r in all_reports}, key=list(REPORT_TYPES.keys()).index)
    type_labels = [REPORT_TYPES[t]["label"] for t in available_types]
    default_index = available_types.index(st.session_state.report_type) if st.session_state.report_type in available_types else 0
    selected_type_label = st.selectbox("Report type", type_labels, index=default_index)
    report_type = available_types[type_labels.index(selected_type_label)]
    reports = [r for r in all_reports if r.get("report_type", DEFAULT_REPORT_TYPE) == report_type]

    # Metric selector — all trackable metrics for the chosen report type
    parameters = REPORT_TYPES[report_type]["parameters"]
    options = list(parameters.keys())
    labels = [parameters[k]["label"] for k in options]
    metric_state_key = f"trend_metric_{report_type}"
    default_metric = st.session_state.get(metric_state_key, options[0])
    if default_metric not in options:
        default_metric = options[0]

    selected_label = st.selectbox("Select parameter to trend", labels, index=options.index(default_metric))
    selected_key = options[labels.index(selected_label)]
    st.session_state[metric_state_key] = selected_key

    frame = build_trend_frame(reports, selected_key, report_type)

    if frame.empty:
        st.info(f"No {selected_label} values found across your {REPORT_TYPES[report_type]['short_label']} reports.")
    else:
        col_chart, col_info = st.columns([3, 1], gap="large")
        with col_chart:
            st.line_chart(frame.set_index("Visit")[[parameters[selected_key]["label"]]], use_container_width=True)
        with col_info:
            st.markdown(f"""
            <div class="card-sm" style="margin-top:.5rem;">
              <div class="card-title">{selected_label}</div>
              <div class="card-sub" style="margin-top:.5rem;">{trend_insight(reports, selected_key, report_type)}</div>
              <div class="card-sub" style="margin-top:.8rem;">
                Visits: {', '.join(frame['Date'].tolist())}
              </div>
            </div>
            """, unsafe_allow_html=True)

    if len(reports) >= 2:
        st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
        headline_fields = REPORT_TYPES[report_type]["groups"][0]["fields"][:3]
        headline_labels = " · ".join(parameters[f]["label"] for f in headline_fields)
        st.markdown(f"""
        <div class="summary-block">
          <div class="summary-block-title">Trend Overview ({headline_labels})</div>
        """, unsafe_allow_html=True)
        st.markdown(f"<div class='summary-block-body'>{summarize_cross_trends(reports, report_type)}</div></div>", unsafe_allow_html=True)


def render_insights() -> None:
    all_reports = get_profile_reports(current_profile()["profile_id"])
    st.markdown("## Insights")

    if not all_reports:
        st.info("Add reports to generate insights.")
        return

    available_types = sorted({r.get("report_type", DEFAULT_REPORT_TYPE) for r in all_reports}, key=list(REPORT_TYPES.keys()).index)
    type_labels = [REPORT_TYPES[t]["label"] for t in available_types]
    default_index = available_types.index(st.session_state.report_type) if st.session_state.report_type in available_types else 0
    selected_type_label = st.selectbox("Report type", type_labels, index=default_index, key="insights_type_select")
    report_type = available_types[type_labels.index(selected_type_label)]
    reports = [r for r in all_reports if r.get("report_type", DEFAULT_REPORT_TYPE) == report_type]
    parameters = REPORT_TYPES[report_type]["parameters"]

    # Overall trajectory badge
    classification = classify_overall_trend(reports)
    traj_colors = {"Improving": "#1a7f5a", "Stable": "#5f6b7a", "Worsening": "#a3241d"}
    traj_bg = {"Improving": "#e9f6ee", "Stable": "#eef1f4", "Worsening": "#fceeed"}
    tc = traj_colors.get(classification, "#333")
    bg = traj_bg.get(classification, "#f9f9f9")
    st.markdown(f"""
    <div class="status-banner" style="background:{bg};color:{tc};">
      <div class="status-banner-dot" style="background:{tc};box-shadow:0 0 0 3px {tc}33;"></div>
      <div>
        <div class="status-banner-label">Overall Trend across {len(reports)} report{'s' if len(reports) != 1 else ''}</div>
        <div class="status-banner-value">{classification}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    tabs = st.tabs(["What Changed", "Risk Signals", "Visit Timeline", "Next Steps"])

    with tabs[0]:
        if len(reports) < 2:
            st.info("At least two reports are needed to compare changes.")
        else:
            ordered = sorted(reports, key=lambda item: item["timestamp"])
            prev_vals, curr_vals = ordered[-2]["values"], ordered[-1]["values"]
            prev_date = datetime.strptime(ordered[-2]["timestamp"], "%Y-%m-%d %H:%M").strftime("%d %b")
            curr_date = datetime.strptime(ordered[-1]["timestamp"], "%Y-%m-%d %H:%M").strftime("%d %b")
            st.markdown(f"<div style='font-size:.85rem;color:var(--muted);margin-bottom:.75rem'>Comparing <strong>{prev_date}</strong> → <strong>{curr_date}</strong></div>", unsafe_allow_html=True)

            # Show changes for all parameters that have values in both reports
            for key in parameters:
                prev_v = prev_vals.get(key)
                curr_v = curr_vals.get(key)
                if prev_v is not None and curr_v is not None:
                    change = metric_change_text(prev_v, curr_v, key, report_type)
                    st.markdown(f"<div class='summary-block'><div class='summary-block-body'>{change}</div></div>", unsafe_allow_html=True)

    with tabs[1]:
        # reports are sorted by timestamp descending, so index 0 is the latest
        latest_result = reports[0]["results"]
        signals = risk_signals_from_result(latest_result)
        for sig in signals:
            st.markdown(f"""
            <div class="summary-block">
              <div class="summary-block-body">{sig}</div>
            </div>
            """, unsafe_allow_html=True)

    with tabs[2]:
        for phase in trajectory_sections(reports):
            st.markdown(f"<div class='summary-block'><div class='summary-block-body'>{phase}</div></div>", unsafe_allow_html=True)

    with tabs[3]:
        steps = next_steps_from_reports(reports)
        for step in steps:
            st.markdown(f"""
            <div class="summary-block">
              <div class="summary-block-body">{step}</div>
            </div>
            """, unsafe_allow_html=True)


def render_vault() -> None:
    profile_id = current_profile()["profile_id"]
    st.markdown("## Medical Vault")
    st.caption("Everything for this profile in one place — uploaded files (X-rays, MRIs, prescriptions) alongside every analyzed lab report.")

    if "vault_form_version" not in st.session_state:
        st.session_state.vault_form_version = 0
    v = st.session_state.vault_form_version

    with st.expander("Add to Vault", expanded=not get_vault_documents(profile_id)):
        doc_type = st.selectbox("Document type", DOCUMENT_TYPES, key=f"vault_doc_type_{v}")
        doc_date = st.date_input("Document date", value=datetime.now(), key=f"vault_doc_date_{v}")
        notes = st.text_area("Notes (optional)", placeholder="e.g. Left knee X-ray, Dr. Rao's follow-up", key=f"vault_notes_{v}")
        uploaded_file = st.file_uploader(
            "Upload file", type=["pdf", "png", "jpg", "jpeg", "webp"],
            key=f"vault_uploader_{v}",
        )
        if st.button("Save to Vault", type="primary", use_container_width=True):
            if uploaded_file is None:
                st.error("Please choose a file to upload.")
            else:
                save_vault_document(profile_id, doc_type, str(doc_date), notes, uploaded_file)
                # Bump the version so next run creates fresh, empty widgets under new
                # keys — mutating the current keys post-instantiation isn't allowed.
                st.session_state.vault_form_version += 1
                st.toast("Saved to your Medical Vault.")
                st.rerun()

    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

    documents = get_vault_documents(profile_id)
    reports = get_profile_reports(profile_id)

    entries: List[Dict[str, Any]] = []
    for doc in documents:
        entries.append({"kind": "document", "sort_key": doc["uploaded_at"], "data": doc})
    for report in reports:
        entries.append({"kind": "report", "sort_key": report["timestamp"], "data": report})
    entries.sort(key=lambda e: e["sort_key"], reverse=True)

    if not entries:
        st.info("Nothing saved yet. Use the panel above to add your first file, or analyze a report to see it here.")
        return

    for entry in entries:
        if entry["kind"] == "document":
            doc = entry["data"]
            try:
                pretty_doc_date = datetime.strptime(doc["doc_date"], "%Y-%m-%d").strftime("%d %b %Y")
            except Exception:
                pretty_doc_date = doc["doc_date"]
            notes_html = f"<div class='history-patterns'>{doc['notes']}</div>" if doc.get("notes") else ""
            st.markdown(f"""
            <div class="history-card">
              <div>
                <div class="history-date">{doc["doc_type"]} · {pretty_doc_date}</div>
                <div class="history-patterns">{doc['filename']} ({doc['size_bytes'] // 1024} KB)</div>
                {notes_html}
              </div>
              <span class="badge" style="background:var(--blue-bg);color:var(--blue-text);flex-shrink:0;">
                Uploaded
              </span>
            </div>
            """, unsafe_allow_html=True)

            c1, c2 = st.columns([3, 1], gap="small")
            with c1:
                file_bytes = base64.b64decode(doc["data_b64"])
                st.download_button(
                    "Download",
                    data=file_bytes,
                    file_name=doc["filename"],
                    mime=doc["mime"],
                    key=f"vault_dl_{doc['id']}",
                    use_container_width=True,
                )
            with c2:
                if st.button("Delete", key=f"vault_del_{doc['id']}", use_container_width=True):
                    delete_vault_document(profile_id, doc["id"])
                    st.toast("Document deleted.")
                    st.rerun()
        else:
            report = entry["data"]
            report_type = report.get("report_type", DEFAULT_REPORT_TYPE)
            type_info = REPORT_TYPES.get(report_type, REPORT_TYPES[DEFAULT_REPORT_TYPE])
            sty = status_chip_style(report["severity"])
            try:
                pretty_date = datetime.strptime(report["timestamp"], "%Y-%m-%d %H:%M").strftime("%d %b %Y, %I:%M %p")
            except Exception:
                pretty_date = report["timestamp"]
            patterns_text = ", ".join(report["patterns"]) if report["patterns"] else "No pattern detected"
            st.markdown(f"""
            <div class="history-card">
              <div>
                <div class="history-date">{type_info['short_label']} Report · {pretty_date}</div>
                <div class="history-patterns">Patterns: {patterns_text}</div>
              </div>
              <span class="badge" style="background:{sty['bg']};color:{sty['text']};flex-shrink:0;">
                {report['severity']}
              </span>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Open Report", key=f"vault_open_{report['timestamp']}_{report_type}", use_container_width=True):
                st.session_state.last_result = report["results"]
                st.session_state.last_report_date = report["timestamp"]
                st.session_state.report_type = report_type
                st.session_state.dashboard_tab = "Results"
                st.session_state.show_success_actions = False
                st.rerun()

        st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)


def maybe_scroll_to_top(marker: str) -> None:
    """Scrolls the page to the top whenever `marker` (e.g. the active tab)
    changes since the last render — fixes landing at the bottom of a tab
    after navigating there (e.g. via 'View Results')."""
    if st.session_state.get("_last_scroll_marker") != marker:
        st.session_state["_last_scroll_marker"] = marker
        components.html(
            """<script>
            try {
              window.parent.document.querySelector('section.main').scrollTo({top: 0, behavior: 'instant'});
              window.parent.scrollTo({top: 0, behavior: 'instant'});
            } catch (e) {}
            </script>""",
            height=0,
        )


def render_dashboard() -> None:
    render_sidebar()

    # Page heading
    tab = LEGACY_NAV_MAP.get(st.session_state.dashboard_tab, st.session_state.dashboard_tab)
    if tab not in NAV_ITEMS:
        tab = NAV_ITEMS[0]
    st.session_state.dashboard_tab = tab
    maybe_scroll_to_top(f"dashboard:{tab}")

    render_profile_strip()

    if tab == "Add Report":
        render_add_report()
    elif tab == "Results":
        render_results()
    elif tab == "History":
        render_history()
    elif tab == "Trends":
        render_trends()
    elif tab == "Insights":
        render_insights()
    elif tab == "Vault":
        render_vault()


def main() -> None:
    initialize_state()
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    if st.session_state.current_page == "identity":
        render_identity_screen()
    else:
        render_dashboard()


if __name__ == "__main__":
    main()
