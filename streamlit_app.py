import streamlit as st
import requests
import pandas as pd
from io import BytesIO
import matplotlib.pyplot as plt
import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
import plotly.express as px
import plotly.graph_objects as go
import os
import math
import time
import uuid
import re
from pathlib import Path
import json

API_BASE_URL = "http://127.0.0.1:8000"

# v15: فلتر الشركة الواحدة - تم إلغاؤه لعرض كافة الشركات
SINGLE_COMPANY_MODE = False
ALLOWED_COMPANY_NAME = "جواكسبريس للشحن"

def apply_company_filter(data_list, name_keys=("اسم الشركة", "company_name", "الشركة")):
    """يصفّي قائمة بيانات بحيث تظهر فقط الشركة المسموح بها."""
    if not SINGLE_COMPANY_MODE or not data_list:
        return data_list
    filtered = []
    for item in data_list:
        if not isinstance(item, dict):
            continue
        for key in name_keys:
            val = str(item.get(key, "")).strip()
            if ALLOWED_COMPANY_NAME in val or val in ALLOWED_COMPANY_NAME:
                filtered.append(item)
                break
    return filtered  # لا يعرض حاجة لو مفيش شركات مطابقة
# -------------------------------------------------------
EXCLUDED_COMPANIES_FILE = "excluded_companies.json"

def load_excluded_companies():
    if os.path.exists(EXCLUDED_COMPANIES_FILE):
        try:
            with open(EXCLUDED_COMPANIES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return {"1": data, "2": data, "3": data, "4": data}
                return data
        except:
            return {}
    return {}

def save_excluded_companies(companies_dict):
    with open(EXCLUDED_COMPANIES_FILE, "w", encoding="utf-8") as f:
        json.dump(companies_dict, f, ensure_ascii=False)

st.set_page_config(page_title="نظام الشركات البريدية", layout="wide")

if "pending_dashboard_year" in st.session_state:
    st.session_state.dashboard_year = st.session_state.pending_dashboard_year
    del st.session_state.pending_dashboard_year
if "pending_dashboard_quarter" in st.session_state:
    st.session_state.dashboard_quarter = st.session_state.pending_dashboard_quarter
    del st.session_state.pending_dashboard_quarter
if "pending_dashboard_mode" in st.session_state:
    st.session_state.dashboard_mode = st.session_state.pending_dashboard_mode
    del st.session_state.pending_dashboard_mode

st.markdown("""
<style>
    .main {
        background: #f6f8fc;
    }

    .block-container {
        padding-top: 3.2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }

    .dashboard-title {
        font-size: 54px;
        font-weight: 900;
        text-align: center;
        line-height: 1.5;
        margin-top: 34px;
        margin-bottom: 14px;
        color: #15803d;
        text-shadow:
            0 0 8px rgba(34, 197, 94, 0.20),
            0 0 18px rgba(34, 197, 94, 0.14),
            0 2px 0 rgba(255, 255, 255, 0.65);
        letter-spacing: 0.6px;
    }

    .dashboard-subtitle {
        font-size: 26px;
        font-weight: 700;
        color: #166534;
        text-align: center;
        line-height: 1.7;
        margin-bottom: 16px;
        text-shadow: 0 0 8px rgba(34, 197, 94, 0.10);
    }

    .title-divider {
        width: 220px;
        height: 6px;
        margin: 0 auto 34px auto;
        border-radius: 999px;
        background: linear-gradient(90deg, #166534, #22c55e, #86efac);
        box-shadow: 0 0 14px rgba(34, 197, 94, 0.35);
    }

    .section-title {
        font-size: 26px;
        font-weight: 800;
        color: #0f172a;
        margin-top: 18px;
        margin-bottom: 14px;
    }

    .subsection-title {
        font-size: 20px;
        font-weight: 700;
        color: #1e293b;
        margin-top: 16px;
        margin-bottom: 10px;
    }

    .kpi-card {
        border-radius: 18px;
        padding: 18px 20px;
        color: white;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.10);
        margin-bottom: 12px;
        min-height: 110px;
    }

    .kpi-card .label {
        font-size: 15px;
        font-weight: 600;
        opacity: 0.95;
        margin-bottom: 12px;
    }

    .kpi-card .value {
        font-size: 24px;
        font-weight: 800;
        line-height: 1.2;
    }

    .blue { background: linear-gradient(135deg, #2563eb, #1d4ed8); }
    .purple { background: linear-gradient(135deg, #7c3aed, #6d28d9); }
    .green { background: linear-gradient(135deg, #059669, #047857); }
    .orange { background: linear-gradient(135deg, #ea580c, #c2410c); }
    .red { background: linear-gradient(135deg, #dc2626, #b91c1c); }

    /* بطاقة نابضة - للعمولة المستحقة */
    @keyframes pulseGlow {
        0%   { box-shadow: 0 0 12px 2px rgba(220, 38, 38, 0.5),  0 8px 20px rgba(15,23,42,0.10); transform: scale(1); }
        50%  { box-shadow: 0 0 32px 10px rgba(255, 80, 80, 0.85), 0 8px 28px rgba(15,23,42,0.18); transform: scale(1.028); }
        100% { box-shadow: 0 0 12px 2px rgba(220, 38, 38, 0.5),  0 8px 20px rgba(15,23,42,0.10); transform: scale(1); }
    }

    .red-pulse {
        background: linear-gradient(135deg, #dc2626, #b91c1c);
        animation: pulseGlow 1.8s ease-in-out infinite;
    }
    .gold { background: linear-gradient(135deg, #d97706, #b45309); }
    .cyan { background: linear-gradient(135deg, #0891b2, #0e7490); }
    .slate { background: linear-gradient(135deg, #475569, #334155); }

    /* تحسين شكل multiselect في الداشبورد */
    [data-baseweb="tag"] {
        background-color: #2563eb !important;
        color: white !important;
        border-radius: 20px !important;
        font-size: 12px !important;
        font-weight: 600 !important;
    }
    [data-baseweb="tag"] span[role="button"] {
        color: white !important;
    }
    .stMultiSelect [data-baseweb="select"] {
        border-radius: 10px !important;
    }

    .table-box {
        background: white;
        border-radius: 18px;
        padding: 14px;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
        margin-top: 10px;
        margin-bottom: 16px;
    }

    .scan-box {
        background: white;
        border-radius: 18px;
        padding: 16px;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
        margin-bottom: 16px;
        border: 1px solid #dbeafe;
    }

    .scan-ready {
        background: #ecfdf5;
        border: 1px solid #86efac;
        border-radius: 14px;
        padding: 12px;
        color: #166534;
        font-weight: 700;
        margin-top: 8px;
        margin-bottom: 12px;
    }

    div[data-testid="stDataFrame"] {
        border-radius: 14px;
        overflow: hidden;
    }

    div[data-testid="stTabs"] {
        direction: rtl;
    }

    div[data-testid="stTabs"] div[role="tablist"] {
        gap: 8px;
        flex-wrap: wrap;
        justify-content: center;
        border-bottom: 1px solid #e5e7eb;
    }

    div[data-testid="stTabs"] button[role="tab"] {
        padding: 8px 12px;
        font-size: 14px;
        white-space: nowrap;
    }

    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: #dc2626;
        border-bottom: 3px solid #ef4444;
    }


    /* تكبير ثقل الخط في واجهة النظام بالكامل */
    html, body, .main, .block-container, p, span, label, div, button,
    input, textarea, select, option {
        font-weight: 700 !important;
    }

    h1, h2, h3, h4, h5, h6,
    .dashboard-title,
    .dashboard-subtitle,
    .section-title,
    .subsection-title {
        font-weight: 900 !important;
    }

    div[data-testid="stTabs"] button[role="tab"],
    div[data-testid="stTabs"] button[role="tab"] p {
        font-weight: 800 !important;
    }

    div[data-testid="stWidgetLabel"],
    div[data-testid="stWidgetLabel"] p,
    .stSelectbox label,
    .stTextInput label,
    .stNumberInput label,
    .stTextArea label,
    .stFileUploader label {
        font-weight: 800 !important;
    }

    .stButton button,
    .stDownloadButton button {
        font-weight: 800 !important;
    }

    /* ===== منع الزووم العرضي على الرسوم البيانية في الموبايل نهائياً مع السماح بسكرول الصفحة بسلاسة ===== */
    div[data-testid="stPlotlyChart"] {
        touch-action: pan-y !important;
        -ms-touch-action: pan-y !important;
    }

    /* إخفاء شريط أدوات الرسم دائماً لمنع التكبير العرضي */
    .modebar-container, .modebar {
        display: none !important;
    }

    /* على شاشات اللمس والموبايل والتابلت: إيقاف تفاعل اللمس مع الرسوم تماماً لمنع الزووم وتسهيل سكرول الصفحة */
    @media (max-width: 1024px), (pointer: coarse) {
        div[data-testid="stPlotlyChart"],
        div[data-testid="stPlotlyChart"] *,
        div[data-testid="stPlotlyChart"] .js-plotly-plot,
        div[data-testid="stPlotlyChart"] .plot-container,
        div[data-testid="stPlotlyChart"] .svg-container,
        div[data-testid="stPlotlyChart"] svg,
        div[data-testid="stPlotlyChart"] .draglayer,
        div[data-testid="stPlotlyChart"] .nsewdrag,
        div[data-testid="stPlotlyChart"] .drag,
        div[data-testid="stPlotlyChart"] .pie,
        div[data-testid="stPlotlyChart"] .bar {
            pointer-events: none !important;
            touch-action: pan-y !important;
            -webkit-touch-callout: none !important;
            user-select: none !important;
            -webkit-user-select: none !important;
        }

        /* Matplotlib / st.pyplot charts */
        div[data-testid="stImage"] img,
        div[data-testid="stPyplot"] img {
            touch-action: pan-y !important;
            -ms-touch-action: pan-y !important;
            pointer-events: none !important;
        }
    }

</style>
""", unsafe_allow_html=True)

st.markdown('<div class="dashboard-title">قطاع تنظيم السوق البريدي</div>', unsafe_allow_html=True)
st.markdown('<div class="dashboard-subtitle">تحليل إيرادات الشركات البريدية</div>', unsafe_allow_html=True)
st.markdown('<div class="title-divider"></div>', unsafe_allow_html=True)


# -----------------------------
# Helpers & Database Integration
# -----------------------------
try:
    from supabase_db import (
        get_all_companies,
        get_all_quarterly_reports,
        migrate_smart_reports,
        get_deleted_reports,
        add_deleted_report,
        clear_deleted_reports
    )
except Exception:
    get_all_companies = None
    get_all_quarterly_reports = None
    migrate_smart_reports = None
    get_deleted_reports = None
    add_deleted_report = None
    clear_deleted_reports = None

def safe_get_json(url):
    # 1. Try local API if available
    try:
        response = requests.get(url, timeout=1.5)
        if response.status_code == 200:
            return response.json(), None
    except Exception:
        pass

    # 2. Fallback directly to Supabase cloud database
    try:
        if "companies" in url and get_all_companies:
            data = get_all_companies()
            return data, None
        if "quarterly-reports" in url and get_all_quarterly_reports:
            data = get_all_quarterly_reports()
            return data, None
    except Exception as e:
        return [], str(e)

    return [], "Connection to backend or database failed"


def safe_post_files(url, files):
    try:
        response = requests.post(url, files=files)
        if response.status_code == 200:
            return response.json(), None
        return None, response.text
    except Exception as e:
        return None, str(e)


def post_scan_file_to_api(uploaded_file):
    endpoint = f"{API_BASE_URL}/quarterly-reports/extract-from-scan/"
    try:
        files = {
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                uploaded_file.type or "application/octet-stream",
            )
        }
        response = requests.post(endpoint, files=files)
        if response.status_code == 200:
            return response.json(), None
        if response.status_code == 404:
            return None, (
                "مسار تحليل السكان غير موجود في FastAPI. "
                "أضف كود backend_scan_endpoint_patch.py إلى ملف الـ backend الرئيسي، "
                "ثم شغّل السيرفر من جديد. المسار المطلوب: "
                f"{endpoint}"
            )
        if response.status_code == 405:
            return None, (
                "مسار تحليل السكان موجود لكنه ليس POST. "
                "لازم يكون @router.post('/extract-from-scan/') في FastAPI."
            )
        return None, f"{response.status_code}: {response.text}"
    except Exception as e:
        return None, str(e)


def post_abbyy_excel_to_api(uploaded_file):
    endpoint = f"{API_BASE_URL}/quarterly-reports/extract-from-abbyy-excel/"
    try:
        files = {
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                uploaded_file.type or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        }

        response = requests.post(endpoint, files=files)

        if response.status_code == 200:
            return response.json(), None

        if response.status_code == 404:
            return None, (
                "مسار تحليل Excel الناتج من ABBYY غير موجود في FastAPI. "
                "تأكد أنك أضفت endpoint: /quarterly-reports/extract-from-abbyy-excel/"
            )

        return None, f"{response.status_code}: {response.text}"

    except Exception as e:
        return None, str(e)



ABBYY_HOT_INPUT_DIR = Path(r"C:\abbyy_hot\input")
ABBYY_HOT_OUTPUT_DIR = Path(r"C:\abbyy_hot\output")


class LocalBytesFile:
    def __init__(self, name, file_type, data):
        self.name = name
        self.type = file_type
        self._data = data

    def getvalue(self):
        return self._data


def wait_for_abbyy_output(expected_stem, start_time=None, timeout_seconds=300):
    """
    ينتظر ملف Excel الناتج من ABBYY HotFolder لنفس الملف المرفوع فقط.
    يبحث داخل C:\abbyy_hot\output وكل الفولدرات الفرعية.
    """
    if start_time is None:
        start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        possible_files = []
        possible_files += list(ABBYY_HOT_OUTPUT_DIR.rglob(f"{expected_stem}*.xlsx"))
        possible_files += list(ABBYY_HOT_OUTPUT_DIR.rglob(f"{expected_stem}*.xlsm"))

        fresh_files = []
        for p in possible_files:
            try:
                if p.is_file() and p.stat().st_mtime >= start_time:
                    fresh_files.append(p)
            except Exception:
                pass

        if fresh_files:
            newest_file = max(fresh_files, key=lambda p: p.stat().st_mtime)

            try:
                size1 = newest_file.stat().st_size
                time.sleep(1)
                size2 = newest_file.stat().st_size

                if size1 == size2 and size2 > 0:
                    return newest_file
            except Exception:
                pass

        time.sleep(2)

    return None


def clear_abbyy_hotfolder_files():
    """
    يمسح الملفات القديمة فقط من input/output حتى لا يقرأ البرنامج تقريرًا سابقًا.
    لا يمسح الفولدرات نفسها.
    """
    for folder in [ABBYY_HOT_INPUT_DIR, ABBYY_HOT_OUTPUT_DIR]:
        folder.mkdir(parents=True, exist_ok=True)

        for p in folder.rglob("*"):
            try:
                if p.is_file():
                    p.unlink()
            except Exception:
                pass


def convert_pdf_with_abbyy_hotfolder_and_extract(uploaded_file):
    """
    يحفظ PDF في ABBYY HotFolder باسم فريد،
    ينتظر Excel الناتج بنفس الاسم،
    ثم يرسله لنفس API قراءة Excel الناتج من ABBYY.

    هذا يمنع قراءة ملف Excel قديم أو تقرير مختلف من C:\abbyy_hot\output.
    """
    ABBYY_HOT_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    ABBYY_HOT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # مهم جدًا: تنظيف الملفات القديمة قبل التحليل
    clear_abbyy_hotfolder_files()

    original_stem = Path(uploaded_file.name).stem
    safe_stem = re.sub(r"[^\w\u0600-\u06FF\-]+", "_", original_stem).strip("_")
    if not safe_stem:
        safe_stem = "postal_report"

    unique_stem = f"{safe_stem}_{uuid.uuid4().hex[:8]}"
    input_pdf_path = ABBYY_HOT_INPUT_DIR / f"{unique_stem}.pdf"

    start_time = time.time()
    input_pdf_path.write_bytes(uploaded_file.getvalue())

    output_xlsx_path = wait_for_abbyy_output(
        expected_stem=unique_stem,
        start_time=start_time,
        timeout_seconds=300,
    )

    if output_xlsx_path is None:
        return None, (
            "لم يتم العثور على ملف Excel الناتج من ABBYY لنفس التقرير المرفوع. "
            "تأكد أن ABBYY HotFolder مفتوح وحالته Watching، وأن الإعدادات هي: "
            "Input=C:\\abbyy_hot\\input و Output=C:\\abbyy_hot\\output "
            "وأن الخرج Microsoft Excel XLSX واللغة Arabic + English."
        )

    excel_bytes = output_xlsx_path.read_bytes()
    fake_file = LocalBytesFile(
        name=output_xlsx_path.name,
        file_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        data=excel_bytes,
    )

    result, error = post_abbyy_excel_to_api(fake_file)

    if isinstance(result, dict):
        result["_abbyy_output_file"] = str(output_xlsx_path)
        result["_abbyy_input_file"] = str(input_pdf_path)
        result["_abbyy_unique_stem"] = unique_stem

    return result, error


def safe_text(value, default="0"):
    if pd.isna(value):
        return default
    value = str(value).strip()
    if value.lower() == "nan" or value == "":
        return default
    return value


def safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        text = str(value).replace(",", "").strip()
        if text == "":
            return default
        return float(text)
    except Exception:
        return default


def safe_int(value, default=0):
    try:
        if value is None:
            return default
        text = str(value).replace(",", "").strip()
        if text == "":
            return default
        return int(float(text))
    except Exception:
        return default





def egp_round_up(value):
    try:
        return int(math.ceil(float(value) - 1e-9))
    except Exception:
        return 0


def calculate_official_financials(local_outbound_revenue=0.0, collected_mail_revenue=0.0, international_outbound_revenue=0.0, inbound_commission=0.0, intermediary_transactions_discount=0.0, review_differences=0.0):
    taxable_revenue = safe_float(local_outbound_revenue) + safe_float(collected_mail_revenue) + safe_float(international_outbound_revenue)
    commission_10_percent = taxable_revenue * 0.10
    commission_before_round = commission_10_percent + safe_float(inbound_commission) - safe_float(intermediary_transactions_discount) + safe_float(review_differences)
    total_commission_due = egp_round_up(commission_before_round)
    vat_amount = total_commission_due * 0.14
    total_indebtedness = total_commission_due + vat_amount
    return {
        "taxable_revenue": taxable_revenue,
        "commission_10_percent": commission_10_percent,
        "commission_before_round": commission_before_round,
        "total_commission_due": total_commission_due,
        "vat_amount": vat_amount,
        "total_indebtedness": total_indebtedness,
    }


def apply_official_financials_to_df(df):
    if df is None or df.empty:
        return df
    work = df.copy()
    for col in ["إيراد الصادر الداخلي", "إيراد البريد المجمع", "إيراد الصادر الخارجي", "عمولة الوارد", "خصم المعاملات الوسيطة", "فروق المراجعة"]:
        if col not in work.columns:
            work[col] = 0.0
        work[col] = pd.to_numeric(work[col], errors="coerce").fillna(0.0)
    work["إجمالي الإيرادات الخاضعة"] = work["إيراد الصادر الداخلي"] + work["إيراد البريد المجمع"] + work["إيراد الصادر الخارجي"]
    work["العمولة المستحقة 10%"] = work["إجمالي الإيرادات الخاضعة"] * 0.10

    has_stored_comm = "إجمالي العمولة المستحقة" in work.columns and pd.to_numeric(work["إجمالي العمولة المستحقة"], errors="coerce").fillna(0.0).sum() > 0
    if not has_stored_comm:
        work["العمولة قبل التقريب"] = work["العمولة المستحقة 10%"] + work["عمولة الوارد"] - work["خصم المعاملات الوسيطة"] + work["فروق المراجعة"]
        work["إجمالي العمولة المستحقة"] = work["العمولة قبل التقريب"].apply(egp_round_up)
    else:
        work["إجمالي العمولة المستحقة"] = pd.to_numeric(work["إجمالي العمولة المستحقة"], errors="coerce").fillna(0.0)
        work["العمولة قبل التقريب"] = work["إجمالي العمولة المستحقة"]

    work["ضريبة القيمة المضافة"] = work["إجمالي العمولة المستحقة"] * 0.14
    has_stored_debt = "إجمالي المديونية" in work.columns and pd.to_numeric(work["إجمالي المديونية"], errors="coerce").fillna(0.0).sum() > 0
    if not has_stored_debt:
        work["إجمالي المديونية"] = work["إجمالي العمولة المستحقة"] + work["ضريبة القيمة المضافة"]
    else:
        work["إجمالي المديونية"] = pd.to_numeric(work["إجمالي المديونية"], errors="coerce").fillna(0.0)
    work["إجمالي العمولة المحسوبة"] = work["إجمالي العمولة المستحقة"]
    return work


def normalize_digits(value):
    text = safe_text(value, "")
    arabic_digits = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
    return text.translate(arabic_digits)


def digits_only(value):
    return "".join(ch for ch in normalize_digits(value) if ch.isdigit())


def is_probable_tax_card_number(value):
    # رقم البطاقة الضريبية غالبًا رقم طويل مثل 479844704، لذلك لا نستخدمه للربط.
    digits = digits_only(value)
    return len(digits) >= 9


def is_valid_postal_license_number(value):
    """رقم الرخصة البريدية يبدأ من 1 وقد يكون رقمًا قصيرًا جدًا مثل 1 أو 5."""
    digits = digits_only(value)
    if not digits:
        return False
    if is_probable_tax_card_number(digits):
        return False
    return int(digits) >= 1


def clean_license_value(value):
    """تنظيف رقم الرخصة البريدية مع قبول أي رقم صحيح يبدأ من 1."""
    text = normalize_digits(value).strip()
    if not text:
        return ""
    text = text.replace(",", "").replace("-", "").replace(" ", "").strip()
    return text


def normalize_arabic_for_match(value):
    text = normalize_digits(value).strip().lower()
    replacements = {
        "أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ئ": "ي", "ؤ": "و", "ة": "ه",
        "ـ": "", "-": " ", "_": " ", ".": " ", "،": " ", ",": " ", "/": " ", "\\": " ", "(": " ", ")": " "
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    stop_words = [
        "شركه", "للبريد", "البريد", "السريع", "ربع", "اول", "الثاني", "الثالث", "الرابع",
        "تقرير", "عام", "سنه", "pdf", "scan", "final", "copy"
    ]
    for word in stop_words:
        text = text.replace(word, " ")
    return " ".join(text.split())


def fuzzy_company_match_score(search_text, company_name):
    from difflib import SequenceMatcher
    a = normalize_arabic_for_match(search_text)
    b = normalize_arabic_for_match(company_name)
    if not a or not b:
        return 0.0
    a_tokens = set(a.split())
    b_tokens = set(b.split())
    token_score = len(a_tokens & b_tokens) / max(1, len(b_tokens))
    seq_score = SequenceMatcher(None, a, b).ratio()
    # نعطي وزنًا أكبر للتوكنات المشتركة لأن أسماء الشركات غالبًا تظهر جزئيًا في اسم الملف أو OCR.
    return max(token_score, seq_score)


def extract_text_values_from_payload(payload):
    if not isinstance(payload, dict):
        return []
    possible_keys = [
        "raw_text", "ocr_text", "full_text", "text", "extracted_text",
        "page_text", "pages_text", "scan_text", "all_text"
    ]
    texts = []
    for key in possible_keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            texts.append(value)
        elif isinstance(value, list):
            texts.extend(str(x) for x in value if str(x).strip())
    return texts


def find_best_company_from_scan_context(payload, companies_data):
    """مطابقة الشركة من اسم الشركة المستخرج أو اسم الملف أو نص OCR.
    هذا مهم لأن OCR أحيانًا يقرأ رقم البطاقة الضريبية بدل الرخصة، بينما اسم الشركة أو اسم الملف يكون أوضح.
    """
    if not companies_data:
        return None
    context_parts = []
    if isinstance(payload, dict):
        context_parts.extend([
            safe_text(payload.get("company_name"), ""),
            safe_text(payload.get("اسم الشركة"), ""),
            safe_text(payload.get("_source_file_name"), ""),
        ])
        context_parts.extend(extract_text_values_from_payload(payload)[:2])
    context = " ".join(x for x in context_parts if x)
    if not context.strip():
        return None
    best_company = None
    best_score = 0.0
    for c in companies_data:
        score = fuzzy_company_match_score(context, safe_text(c.get("اسم الشركة"), ""))
        if score > best_score:
            best_score = score
            best_company = c
    # 0.35 مقصودة لأنها تمسك حالة: اسم الملف "يونيون كوريير" واسم الشركة "يونيون كورير للبريد السريع".
    return best_company if best_score >= 0.35 else None


def quarter_from_month(month):
    """تحديد الربع من الشهر حسب تقسيم السنة الرسمي:
    الربع الأول: 1/1 إلى 31/3، الربع الثاني: 1/4 إلى 30/6،
    الربع الثالث: 1/7 إلى 30/9، الربع الرابع: 1/10 إلى 31/12.
    """
    try:
        month = int(month)
    except Exception:
        return None
    if 1 <= month <= 3:
        return 1
    if 4 <= month <= 6:
        return 2
    if 7 <= month <= 9:
        return 3
    if 10 <= month <= 12:
        return 4
    return None


def extract_dates_from_text(text):
    """استخراج التواريخ المكتوبة بصيغ مثل 2026/1/1 أو 31-3-2026 أو 2026-03-31."""
    import re
    text = normalize_digits(safe_text(text, ""))
    dates = []

    # صيغة: yyyy/mm/dd أو yyyy-mm-dd
    for y, m, d in re.findall(r"(20\d{2})\s*[/-]\s*(\d{1,2})\s*[/-]\s*(\d{1,2})", text):
        dates.append((int(y), int(m), int(d)))

    # صيغة: dd/mm/yyyy أو dd-mm-yyyy
    for d, m, y in re.findall(r"(\d{1,2})\s*[/-]\s*(\d{1,2})\s*[/-]\s*(20\d{2})", text):
        dates.append((int(y), int(m), int(d)))

    return dates


def infer_quarter_from_date_range(text):
    """نستخدم فترة التقرير إن وجدت لأنها أدق من أي رقم عشوائي في OCR.
    مثال: من 2026/1/1 إلى 2026/3/31 => الربع الأول.
    """
    dates = extract_dates_from_text(text)
    if not dates:
        return None, None

    # اختر سنة التقرير من أول/أكثر سنة ظاهرة في التواريخ.
    years = [d[0] for d in dates if 2020 <= d[0] <= 2100]
    year = years[0] if years else None

    months = [d[1] for d in dates if 1 <= d[1] <= 12]
    if not months:
        return year, None

    # لو الفترة كلها داخل ربع واحد، نأخذ هذا الربع.
    quarters = [quarter_from_month(m) for m in months if quarter_from_month(m)]
    unique_quarters = sorted(set(quarters))
    if len(unique_quarters) == 1:
        return year, unique_quarters[0]

    # لو ظهر تاريخ بداية ونهاية لنفس الربع، مثل 1/1 و31/3، سنصل هنا أحيانًا بسبب تواريخ أخرى.
    # نعطي أولوية للأنماط الرسمية الشائعة لكل ربع داخل النص.
    normalized_text = normalize_digits(text)
    patterns = [
        (1, [r"1\s*[/-]\s*1\s*[/-]\s*20\d{2}", r"20\d{2}\s*[/-]\s*1\s*[/-]\s*1", r"31\s*[/-]\s*3\s*[/-]\s*20\d{2}", r"20\d{2}\s*[/-]\s*3\s*[/-]\s*31"]),
        (2, [r"1\s*[/-]\s*4\s*[/-]\s*20\d{2}", r"20\d{2}\s*[/-]\s*4\s*[/-]\s*1", r"30\s*[/-]\s*6\s*[/-]\s*20\d{2}", r"20\d{2}\s*[/-]\s*6\s*[/-]\s*30"]),
        (3, [r"1\s*[/-]\s*7\s*[/-]\s*20\d{2}", r"20\d{2}\s*[/-]\s*7\s*[/-]\s*1", r"30\s*[/-]\s*9\s*[/-]\s*20\d{2}", r"20\d{2}\s*[/-]\s*9\s*[/-]\s*30"]),
        (4, [r"1\s*[/-]\s*10\s*[/-]\s*20\d{2}", r"20\d{2}\s*[/-]\s*10\s*[/-]\s*1", r"31\s*[/-]\s*12\s*[/-]\s*20\d{2}", r"20\d{2}\s*[/-]\s*12\s*[/-]\s*31"]),
    ]
    import re
    best_q = None
    best_hits = 0
    for q, q_patterns in patterns:
        hits = sum(1 for pat in q_patterns if re.search(pat, normalized_text))
        if hits > best_hits:
            best_hits = hits
            best_q = q
    if best_q:
        return year, best_q

    # آخر حل: نأخذ ربع شهر البداية إن كان واضحًا.
    return year, quarters[0] if quarters else None


def extract_report_year_quarter_from_context(payload):
    """استخراج السنة والربع من عنوان التقرير أو فترة التقرير.
    الأولوية لفترة التقرير: 1/1-31/3 = الربع الأول، 1/4-30/6 = الثاني،
    1/7-30/9 = الثالث، 1/10-31/12 = الرابع.
    """
    import re
    texts = []
    if isinstance(payload, dict):
        texts.extend(extract_text_values_from_payload(payload))
        texts.append(safe_text(payload.get("_source_file_name"), ""))
    text = normalize_digits(" ".join(texts))

    # فترة التقرير أدق مصدر للسنة والربع.
    range_year, range_quarter = infer_quarter_from_date_range(text)
    if range_year or range_quarter:
        return range_year, range_quarter

    year = None
    quarter = None
    m = re.search(r"20\d{2}", text)
    if m:
        year = int(m.group(0))

    q_words = {
        "الاول": 1, "الأول": 1, "اول": 1, "1": 1,
        "الثاني": 2, "ثاني": 2, "2": 2,
        "الثالث": 3, "ثالث": 3, "3": 3,
        "الرابع": 4, "رابع": 4, "4": 4,
    }
    normalized = normalize_arabic_for_match(text)
    for word, q in q_words.items():
        w = normalize_arabic_for_match(word)
        if f"ربع {w}" in normalized or f"الربع {w}" in normalized:
            quarter = q
            break
    return year, quarter


def extract_postal_license_from_text_payload(payload):
    """يحاول التقاط رقم الرخصة من نص OCR الخام إن كان الـ API يرجعه.
    نبحث حول عبارة رقم الرخصة البريدية ونستبعد رقم البطاقة الضريبية الطويل.
    """
    if not isinstance(payload, dict):
        return ""

    texts = extract_text_values_from_payload(payload)
    if not texts:
        return ""

    import re
    text = normalize_digits("\n".join(texts))
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for i, line in enumerate(lines):
        if "الرخص" in line and "البريدي" in line:
            window = " ".join(lines[max(0, i - 1): min(len(lines), i + 3)])
            # رقم الرخصة البريدية يبدأ من 1، وقد يكون رقمًا واحدًا مثل 5.
            # نستبعد فقط الأرقام الطويلة التي تشبه البطاقة الضريبية.
            nums = re.findall(r"\b\d{1,8}\b", window)
            valid_nums = [num for num in nums if is_valid_postal_license_number(num)]
            if valid_nums:
                # رقم الرخصة في تقارير الهيئة غالبًا هو الرقم القصير بجوار عبارة رقم الرخصة البريدية،
                # وليس الأرقام الطويلة مثل السجل/الموبايل/التقرير.
                return sorted(valid_nums, key=lambda x: (len(x), int(x)))[0]
    return ""


def normalize_extracted_report_data(extracted, companies_data=None):
    if not extracted:
        return {}
    cleaned = dict(extracted)
    companies_data = companies_data or []

    explicit_postal_license = clean_license_value(
        cleaned.get("postal_license_number")
        or cleaned.get("mail_license_number")
        or cleaned.get("رقم الرخصة البريدية")
    )
    license_from_raw_text = clean_license_value(extract_postal_license_from_text_payload(cleaned))
    extracted_license = clean_license_value(cleaned.get("license_number"))
    extracted_name = safe_text(cleaned.get("company_name"), "")

    registered_licenses = {
        clean_license_value(c.get("رقم الرخصة")): c
        for c in companies_data
        if clean_license_value(c.get("رقم الرخصة"))
    }

    matched_company = None
    if extracted_name:
        normalized_extracted_name = extracted_name.replace(" ", "")
        for c in companies_data:
            company_name = safe_text(c.get("اسم الشركة"), "")
            normalized_company_name = company_name.replace(" ", "")
            if normalized_company_name and (
                normalized_extracted_name in normalized_company_name
                or normalized_company_name in normalized_extracted_name
                or fuzzy_company_match_score(extracted_name, company_name) >= 0.55
            ):
                matched_company = c
                break

    if matched_company is None:
        matched_company = find_best_company_from_scan_context(cleaned, companies_data)

    inferred_year, inferred_quarter = extract_report_year_quarter_from_context(cleaned)
    if inferred_year and not cleaned.get("year"):
        cleaned["year"] = inferred_year
    if inferred_quarter and not cleaned.get("quarter"):
        cleaned["quarter"] = inferred_quarter

    # الأولوية: رقم رخصة صريح، ثم رقم مستخرج من النص بجوار عبارة رقم الرخصة البريدية، ثم رقم موجود بالفعل في الشركات، ثم مطابقة اسم الشركة/اسم الملف/OCR.
    if explicit_postal_license:
        cleaned["license_number"] = explicit_postal_license
    elif license_from_raw_text:
        cleaned["license_number"] = license_from_raw_text
    elif extracted_license in registered_licenses:
        cleaned["license_number"] = extracted_license
    elif matched_company:
        cleaned["license_number"] = clean_license_value(matched_company.get("رقم الرخصة"))
        if not cleaned.get("company_name"):
            cleaned["company_name"] = safe_text(matched_company.get("اسم الشركة"), "")
        if not cleaned.get("category"):
            cleaned["category"] = safe_text(matched_company.get("الفئة"), "")
    elif is_probable_tax_card_number(extracted_license):
        cleaned["tax_card_number"] = extracted_license
        cleaned["license_number"] = ""
        cleaned["license_warning"] = (
            "تم تجاهل الرقم المستخرج لأنه رقم بطاقة ضريبية. سيتم الربط تلقائيًا من اسم الشركة أو بيانات الشركة المسجلة."
        )
    else:
        cleaned["license_number"] = extracted_license

    calc = calculate_official_financials(
        cleaned.get("local_outbound_revenue", 0.0),
        cleaned.get("collected_mail_revenue", 0.0),
        cleaned.get("international_outbound_revenue", 0.0),
        cleaned.get("inbound_commission", 0.0),
        cleaned.get("intermediary_transactions_discount", 0.0),
        cleaned.get("review_differences", 0.0),
    )
    cleaned["total_commission_due"] = calc["total_commission_due"]
    cleaned["vat_amount"] = calc["vat_amount"]
    cleaned["total_indebtedness"] = calc["total_indebtedness"]
    return cleaned

def find_matching_company(extracted, companies_data):
    extracted_license = safe_text(extracted.get("license_number"), "")
    extracted_name = safe_text(extracted.get("company_name"), "")

    for company in companies_data:
        company_license = safe_text(company.get("رقم الرخصة"), "")
        company_name = safe_text(company.get("اسم الشركة"), "")

        if extracted_license and company_license == extracted_license:
            return company

        if extracted_name and company_name:
            if extracted_name in company_name or company_name in extracted_name:
                return company

    return None


def clean_report_note_text(value, source_file_name=""):
    """ملاحظات قصيرة ونظيفة حتى لا نرسل نص OCR طويل أو أرقام بطاقة ضريبية للـ API."""
    base = "تم الربط تلقائيًا من تقرير سكان"
    source_file_name = safe_text(source_file_name, "").strip()
    if source_file_name:
        base += f": {source_file_name}"
    return base[:250]


def build_quarterly_report_params(extracted, company_id, year, quarter, source_file_name=""):
    calc = calculate_official_financials(
        extracted.get("local_outbound_revenue", 0.0),
        extracted.get("collected_mail_revenue", 0.0),
        extracted.get("international_outbound_revenue", 0.0),
        extracted.get("inbound_commission", 0.0),
        extracted.get("intermediary_transactions_discount", 0.0),
        extracted.get("review_differences", 0.0),
    )
    return {
        "company_id": int(company_id),
        "year": int(year),
        "quarter": int(quarter),
        "local_outbound_count": safe_int(extracted.get("local_outbound_count"), 0),
        "local_outbound_weight": safe_float(extracted.get("local_outbound_weight"), 0.0),
        "local_outbound_revenue": safe_float(extracted.get("local_outbound_revenue"), 0.0),
        "collected_mail_count": safe_int(extracted.get("collected_mail_count"), 0),
        "collected_mail_weight": safe_float(extracted.get("collected_mail_weight"), 0.0),
        "collected_mail_revenue": safe_float(extracted.get("collected_mail_revenue"), 0.0),
        "international_outbound_count": safe_int(extracted.get("international_outbound_count"), 0),
        "international_outbound_weight": safe_float(extracted.get("international_outbound_weight"), 0.0),
        "international_outbound_revenue": safe_float(extracted.get("international_outbound_revenue"), 0.0),
        "inbound_count": safe_int(extracted.get("inbound_count"), 0),
        "inbound_weight": safe_float(extracted.get("inbound_weight"), 0.0),
        "inbound_commission": safe_float(extracted.get("inbound_commission"), 0.0),
        "intermediary_transactions_discount": safe_float(extracted.get("intermediary_transactions_discount"), 0.0),
        "review_differences": safe_float(extracted.get("review_differences"), 0.0),
        "total_commission_due": safe_float(calc["total_commission_due"], 0.0),
        "vat_amount": safe_float(calc["vat_amount"], 0.0),
        "notes": clean_report_note_text(extracted.get("notes"), source_file_name),
    }



def find_existing_report(company_id, year, quarter):
    """يعثر على التقرير الموجود لنفس الشركة/السنة/الربع، ويرجع كائن التقرير كاملًا إن وجد."""
    reports_data, reports_error = safe_get_json(f"{API_BASE_URL}/quarterly-reports/")
    if reports_error or not reports_data:
        return None

    def _get_int(report, *keys):
        for key in keys:
            if key in report and report.get(key) not in (None, ""):
                try:
                    return int(float(str(report.get(key)).replace(',', '').strip()))
                except Exception:
                    pass
        return None

    for report in reports_data:
        try:
            r_company_id = _get_int(report, "company_id", "شركة_id", "معرف الشركة")
            r_year = _get_int(report, "السنة", "year")
            r_quarter = _get_int(report, "الربع", "quarter")
            if r_company_id == int(company_id) and r_year == int(year) and r_quarter == int(quarter):
                return report
        except Exception:
            continue
    return None


def report_already_exists(company_id, year, quarter):
    return find_existing_report(company_id, year, quarter) is not None


def delete_existing_report_if_any(company_id, year, quarter):
    """يحذف أي تقرير بنفس الشركة/السنة/الربع قبل الحفظ.

    مهم: لا نعتمد على find_existing_report فقط، لأن بعض نسخ API لا ترجع company_id
    في قائمة التقارير، فكان التقرير القديم يفضل موجودًا ثم يفشل الحفظ بـ 500.
    """
    key_params = {
        "company_id": int(company_id),
        "year": int(year),
        "quarter": int(quarter),
    }

    # المحاولة الأساسية: حذف مباشر بالمفاتيح حتى لو لم يظهر التقرير في قائمة العرض.
    try:
        response = requests.delete(
            f"{API_BASE_URL}/quarterly-reports/delete-by-keys/",
            params=key_params,
            timeout=30,
        )
        # 200 = اتحذف، 404 = غير موجود أصلاً، وده مقبول قبل الحفظ.
        if response.status_code in (200, 404):
            return True, ""
        # بعض النسخ ترجع 400 عند عدم وجود التقرير، وده برضه لا يمنع الحفظ الجديد.
        if response.status_code == 400 and ("غير موجود" in response.text or "not found" in response.text.lower()):
            return True, ""
        direct_delete_error = f"delete-by-keys: {response.status_code} - {response.text[:300]}"
    except Exception as e:
        direct_delete_error = f"delete-by-keys exception: {e}"

    # المحاولة الاحتياطية: لو قدرنا نلاقي التقرير في القائمة نحذفه بالـ id.
    existing_report = find_existing_report(company_id, year, quarter)
    if existing_report:
        report_id = existing_report.get("id") or existing_report.get("report_id") or existing_report.get("معرف التقرير")
        if report_id not in (None, ""):
            try:
                response = requests.delete(
                    f"{API_BASE_URL}/quarterly-reports/{report_id}",
                    timeout=30,
                )
                if response.status_code in (200, 404):
                    return True, ""
                return False, f"{direct_delete_error} | delete-by-id: {response.status_code} - {response.text[:300]}"
            except Exception as e:
                return False, f"{direct_delete_error} | delete-by-id exception: {e}"

    # لو الحذف المباشر فشل، نرجع تفاصيل واضحة بدل ما نخفي السبب.
    return False, direct_delete_error


def post_quarterly_report_with_fallbacks(params):
    """يحفظ التقرير بالطريقة التي يتوقعها FastAPI: Query Params فقط.

    رسالة 422 التي ظهرت عند form/json كانت طبيعية لأن الـ backend يعرف الحقول كـ Query
    وليس JSON body. لذلك ألغينا form/json حتى لا تظهر أخطاء مضللة.
    """
    clean_params = {}
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, bool):
            clean_params[key] = int(value)
        elif isinstance(value, int):
            clean_params[key] = int(value)
        elif isinstance(value, float):
            # تقليل مشاكل 773120.3200000001 عند الإرسال.
            clean_params[key] = round(float(value), 2)
        else:
            clean_params[key] = str(value)[:250] if key == "notes" else str(value)

    required_keys = ["company_id", "year", "quarter"]
    missing = [k for k in required_keys if k not in clean_params or clean_params[k] in ("", None)]
    if missing:
        return None, "حقول الربط ناقصة قبل الإرسال: " + ", ".join(missing)

    try:
        response = requests.post(
            f"{API_BASE_URL}/quarterly-reports/",
            params=clean_params,
            timeout=30,
        )
        if response.status_code == 200:
            return response, ""
        return None, f"POST query params: {response.status_code} - {response.text[:800]}"
    except Exception as e:
        return None, f"POST query params exception: {e}"

def auto_save_extracted_report(extracted):
    companies_data, companies_error = safe_get_json(f"{API_BASE_URL}/companies/")
    if companies_error:
        return False, "تعذر جلب الشركات المسجلة. تأكد أن الـ API يعمل ثم أعد المحاولة."

    source_file_name = safe_text(extracted.get("_source_file_name"), "") if isinstance(extracted, dict) else ""
    extracted = normalize_extracted_report_data(extracted, companies_data)
    matched_company = find_matching_company(extracted, companies_data)
    if matched_company is None:
        matched_company = find_best_company_from_scan_context(extracted, companies_data)

    if matched_company is None:
        return False, "لم يتم العثور على الشركة تلقائيًا من اسم التقرير أو اسم الشركة المسجلة. راجع أن الشركة موجودة في تبويب الشركات بنفس الاسم."

    company_id = matched_company.get("id")
    if company_id is None:
        return False, "تم العثور على الشركة لكن رقمها الداخلي غير موجود. راجع بيانات الشركات في قاعدة البيانات."

    year = safe_int(extracted.get("year"), 2026)
    quarter = safe_int(extracted.get("quarter"), 1)

    # تثبيت بيانات الربط من الشركة المسجلة وليس من أرقام OCR العشوائية.
    extracted["license_number"] = clean_license_value(matched_company.get("رقم الرخصة"))
    extracted["company_name"] = safe_text(matched_company.get("اسم الشركة"), "")
    extracted["category"] = safe_text(matched_company.get("الفئة"), "")

    ok_delete, delete_error = delete_existing_report_if_any(company_id, year, quarter)
    if not ok_delete:
        return False, f"تعذر استبدال التقرير القديم لنفس الشركة والسنة والربع: {delete_error}"

    params = build_quarterly_report_params(extracted, company_id, year, quarter, source_file_name)

    company_name = safe_text(matched_company.get("اسم الشركة"), "")

    save_response, save_error = post_quarterly_report_with_fallbacks(params)
    if save_response is not None and save_response.status_code == 200:
        return True, f"تم ربط البيانات وحفظ التقرير للشركة: {company_name} - سنة {year} / ربع {quarter}"

    # لو ظهر خطأ بسبب تقرير موجود أو خطأ داخلي، نحاول حذف أي تقرير بنفس المفاتيح ثم نعيد الحفظ بملاحظات قصيرة جدًا.
    ok_delete_again, delete_error_again = delete_existing_report_if_any(company_id, year, quarter)
    retry_params = dict(params)
    retry_params["notes"] = "تم الربط تلقائيًا من تقرير سكان"
    retry_response, retry_error = post_quarterly_report_with_fallbacks(retry_params)
    if retry_response is not None and retry_response.status_code == 200:
        return True, f"تم ربط البيانات وحفظ التقرير للشركة: {company_name} - سنة {year} / ربع {quarter}"

    details = retry_error or save_error
    if delete_error_again:
        details = f"مشكلة أثناء استبدال تقرير قديم: {delete_error_again} | {details}"
    return False, (
        f"فشل ربط/حفظ التقرير للشركة: {company_name} - السنة {year} / الربع {quarter}. "
        f"تفاصيل الخطأ: {details}. "
        "لو استمر الخطأ فالمشكلة من API/قاعدة البيانات، وليس من شاشة الربط، لأن الحقول المطلوبة أُرسلت كـ query params."
    )

def ar_text(text):
    text = safe_text(text, "")
    if not text:
        return ""
    try:
        return get_display(arabic_reshaper.reshape(str(text)))
    except Exception:
        return str(text)


def shape_labels(labels):
    return [ar_text(label) for label in labels]


def normalize_category(value):
    value = safe_text(value, "").strip()
    value = value.replace("داخلى", "داخلي")
    value = value.replace("داخلي+مجمع", "داخلي + مجمع")
    value = value.replace("داخلي +مجمع", "داخلي + مجمع")
    value = value.replace("داخلي+ مجمع", "داخلي + مجمع")
    value = value.replace("داخلى+مجمع", "داخلي + مجمع")
    value = value.replace("داخلى + مجمع", "داخلي + مجمع")
    value = " ".join(value.split())
    allowed = ["داخلي", "مجمع", "داخلي + مجمع", "شامل"]
    return value if value in allowed else value


def metric_card(label, value, color_class="blue"):
    st.markdown(
        f"""
        <div class="kpi-card {color_class}">
            <div class="label">{label}</div>
            <div class="value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def boxed_dataframe(df):
    st.markdown('<div class="table-box">', unsafe_allow_html=True)
    row_count = len(df) if df is not None else 0
    calc_height = min(520, max(180, (row_count + 1) * 38)) if row_count > 0 else 200
    st.dataframe(df, use_container_width=True, height=calc_height)
    st.markdown('</div>', unsafe_allow_html=True)


def make_bar_chart(labels, values, title, ylabel="القيمة", rotate=20, figsize=(10, 5), annotate=True):
    fig, ax = plt.subplots(figsize=figsize)
    bars = ax.bar(shape_labels(labels), values)
    ax.set_title(ar_text(title), fontsize=18)
    ax.set_ylabel(ar_text(ylabel), fontsize=13)
    plt.xticks(rotation=rotate, ha="right")
    if annotate:
        max_val = max(values) if len(values) else 0
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + (max_val * 0.01 if max_val else 0.1),
                f"{int(value) if float(value).is_integer() else round(value, 2)}",
                ha="center",
                va="bottom",
                fontsize=10
            )
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def make_line_chart(x_values, series, title, ylabel="القيمة", figsize=(10, 5)):
    fig, ax = plt.subplots(figsize=figsize)
    for y_values, label in series:
        ax.plot(x_values, y_values, marker="o", label=ar_text(label))
    ax.legend()
    ax.set_title(ar_text(title), fontsize=18)
    ax.set_ylabel(ar_text(ylabel), fontsize=13)
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def register_arabic_font():
    possible_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "DejaVuSans.ttf",
        "arial.ttf",
    ]

    for font_path in possible_fonts:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont("ArabicFont", font_path))
                return "ArabicFont"
            except Exception:
                continue
    return "Helvetica"


def draw_rtl_line(pdf, text, x, y, font_name="Helvetica", font_size=11):
    text = safe_text(text, "")
    pdf.setFont(font_name, font_size)
    pdf.drawRightString(x, y, text)


def generate_companies_template():
    df = pd.DataFrame([
        {
            "رقم الرخصة": "",
            "اسم الشركة": "",
            "الفئة": "داخلي",
            "تستخدم الأوزان": "نعم",
            "ملاحظات": ""
        }
    ])
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="CompaniesTemplate")
    output.seek(0)
    return output


def generate_quarterly_template():
    df = pd.DataFrame([
        {
            "رقم الرخصة": "",
            "السنة": 2026,
            "الربع": 1,
            "عدد الصادر الداخلي": 0,
            "وزن الصادر الداخلي": 0.0,
            "إيراد الصادر الداخلي": 0.0,
            "عدد البريد المجمع": 0,
            "وزن البريد المجمع": 0.0,
            "إيراد البريد المجمع": 0.0,
            "عدد الصادر الخارجي": 0,
            "وزن الصادر الخارجي": 0.0,
            "إيراد الصادر الخارجي": 0.0,
            "عدد الوارد": 0,
            "وزن الوارد": 0.0,
            "عمولة الوارد": 0.0,
            "خصم المعاملات الوسيطة": 0.0,
            "فروق المراجعة": 0.0,
            "ضريبة القيمة المضافة": 0.0,
            "ملاحظات": ""
        }
    ])
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="QuarterlyReportsTemplate")
    output.seek(0)
    return output


def build_official_pdf(report):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    font_name = register_arabic_font()

    y = height - 50

    def new_page():
        pdf.showPage()
        if font_name != "Helvetica":
            pdf.setFont(font_name, 11)
        return height - 50

    pdf.setTitle("Official Quarterly Report")

    pdf.setFont(font_name, 16)
    pdf.drawRightString(width - 40, y, "تقرير ربع سنوي رسمي")
    y -= 30

    pdf.setFont(font_name, 12)
    draw_rtl_line(pdf, f"الشركة: {safe_text(report.get('الشركة', ''))}", width - 40, y, font_name, 12)
    y -= 22
    draw_rtl_line(
        pdf,
        f"الفئة: {safe_text(report.get('الفئة', ''))} | السنة: {safe_text(report.get('السنة', ''))} | الربع: {safe_text(report.get('الربع', ''))}",
        width - 40,
        y,
        font_name,
        12,
    )
    y -= 30

    pdf.setFont(font_name, 13)
    draw_rtl_line(pdf, "أولًا: بيانات النشاط", width - 40, y, font_name, 13)
    y -= 24

    activity_rows = []
    category = safe_text(report.get("الفئة", ""), "")

    if category in ["داخلي", "داخلي + مجمع", "شامل"]:
        activity_rows.append(
            f"الصادر الداخلي | العدد: {safe_text(report.get('عدد الصادر الداخلي'))} | الوزن: {safe_text(report.get('وزن الصادر الداخلي'))} | الإيراد/العمولة: {safe_text(report.get('إيراد الصادر الداخلي'))}"
        )

    if category in ["مجمع", "داخلي + مجمع", "شامل"]:
        activity_rows.append(
            f"البريد المجمع | العدد: {safe_text(report.get('عدد البريد المجمع'))} | الوزن: {safe_text(report.get('وزن البريد المجمع'))} | الإيراد/العمولة: {safe_text(report.get('إيراد البريد المجمع'))}"
        )

    if category == "شامل":
        activity_rows.append(
            f"الصادر الخارجي | العدد: {safe_text(report.get('عدد الصادر الخارجي'))} | الوزن: {safe_text(report.get('وزن الصادر الخارجي'))} | الإيراد/العمولة: {safe_text(report.get('إيراد الصادر الخارجي'))}"
        )
        activity_rows.append(
            f"الوارد الخارجي | العدد: {safe_text(report.get('عدد الوارد'))} | الوزن: {safe_text(report.get('وزن الوارد'))} | الإيراد/العمولة: {safe_text(report.get('عمولة الوارد'))}"
        )

    pdf.setFont(font_name, 11)
    for row in activity_rows:
        wrapped_lines = simpleSplit(row, font_name, 11, width - 80)
        for line in wrapped_lines:
            if y < 60:
                y = new_page()
            draw_rtl_line(pdf, line, width - 40, y, font_name, 11)
            y -= 18

    y -= 10
    if y < 60:
        y = new_page()

    pdf.setFont(font_name, 13)
    draw_rtl_line(pdf, "ثانيًا: التسويات والنتائج المالية", width - 40, y, font_name, 13)
    y -= 24

    financial_rows = [
        f"إجمالي الإيرادات الخاضعة: {safe_text(report.get('إجمالي الإيرادات الخاضعة'))}",
        f"العمولة المستحقة 10%: {safe_text(report.get('العمولة المستحقة 10%'))}",
        f"خصم المعاملات الوسيطة: {safe_text(report.get('خصم المعاملات الوسيطة'))}",
        f"فروق المراجعة: {safe_text(report.get('فروق المراجعة'))}",
        f"ضريبة القيمة المضافة: {safe_text(report.get('ضريبة القيمة المضافة'))}",
        f"إجمالي العمولة المستحقة: {safe_text(report.get('إجمالي العمولة المستحقة'))}",
        f"إجمالي المديونية: {safe_text(report.get('إجمالي المديونية'))}",
    ]

    pdf.setFont(font_name, 11)
    for row in financial_rows:
        if y < 60:
            y = new_page()
        draw_rtl_line(pdf, row, width - 40, y, font_name, 11)
        y -= 18

    y -= 10
    if y < 60:
        y = new_page()

    pdf.setFont(font_name, 13)
    draw_rtl_line(pdf, "ثالثًا: الملاحظات", width - 40, y, font_name, 13)
    y -= 24

    notes = safe_text(report.get("ملاحظات"), "لا توجد ملاحظات")
    wrapped_notes = simpleSplit(notes, font_name, 11, width - 80)

    pdf.setFont(font_name, 11)
    for line in wrapped_notes:
        if y < 60:
            y = new_page()
        draw_rtl_line(pdf, line, width - 40, y, font_name, 11)
        y -= 18

    pdf.save()
    buffer.seek(0)
    return buffer


PLOTLY_CONFIG = {
    "displayModeBar": False,
    "displaylogo": False,
    "scrollZoom": False,
    "responsive": True,
    "doubleClick": False,
    "showTips": False,
    "showAxisDragHandles": False,
    "showAxisRangeEntryBoxes": False,
    "modeBarButtonsToRemove": [
        "pan2d",
        "lasso2d",
        "select2d",
        "zoomIn2d",
        "zoomOut2d",
        "autoScale2d",
        "zoom2d",
        "resetScale2d"
    ]
}


def plotly_donut(labels, values, title, colors=None):
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.55,
                textinfo="label+percent",
                textposition="inside",
                pull=[0.02] * len(labels),
                marker=dict(colors=colors) if colors else None,
                hovertemplate="<b>%{label}</b><br>القيمة: %{value:,.2f}<br>النسبة: %{percent}<extra></extra>"
            )
        ]
    )

    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center"},
        height=540,
        margin=dict(t=70, b=20, l=20, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        dragmode=False
    )

    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)


def plotly_horizontal_bar(labels, values, title, x_title="القيمة", color="#7c3aed"):
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=color,
            text=[f"{v:,.2f}" for v in values],
            textposition="outside",
            hovertemplate=f"<b>%{{y}}</b><br>{x_title}: %{{x:,.2f}}<extra></extra>"
        )
    )

    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center"},
        height=560,
        margin=dict(t=70, b=20, l=20, r=20),
        xaxis_title=x_title,
        yaxis=dict(autorange="reversed"),
        dragmode=False
    )
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)

    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)


def plotly_vertical_bar(labels, values, title, y_title="القيمة", color="#10b981"):
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=labels,
            y=values,
            marker_color=color,
            text=[f"{v:,.2f}" if isinstance(v, float) else f"{v:,}" for v in values],
            textposition="outside",
            hovertemplate=f"<b>%{{x}}</b><br>{y_title}: %{{y:,.2f}}<extra></extra>"
        )
    )

    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center"},
        height=560,
        margin=dict(t=70, b=40, l=20, r=20),
        yaxis_title=y_title,
        dragmode=False
    )
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)

    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)


def plotly_stacked_bar(x_labels, series_data, title, y_title="القيمة"):
    colors = ["#dc2626", "#d97706", "#7c3aed", "#0891b2"]
    fig = go.Figure()

    for i, (label, values) in enumerate(series_data):
        fig.add_trace(
            go.Bar(
                x=x_labels,
                y=values,
                name=label,
                marker_color=colors[i % len(colors)],
                text=[f"{v:,.2f}" for v in values],
                hovertemplate=f"<b>{label}</b><br>السنة: %{{x}}<br>{y_title}: %{{y:,.2f}}<extra></extra>"
            )
        )

    fig.update_layout(
        barmode="stack",
        title={"text": title, "x": 0.5, "xanchor": "center"},
        height=560,
        margin=dict(t=70, b=40, l=20, r=20),
        yaxis_title=y_title,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        dragmode=False
    )
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)

    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)


def generate_executive_summary_excel(market_df, year_label, quarter_label, kpi_dict):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()

    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )
    navy_fill = PatternFill(start_color='1E3A8A', end_color='1E3A8A', fill_type='solid')
    header_font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
    title_font = Font(name='Calibri', size=16, bold=True, color='1E3A8A')
    subtitle_font = Font(name='Calibri', size=11, italic=True, color='64748B')
    bold_font = Font(name='Calibri', size=11, bold=True)
    regular_font = Font(name='Calibri', size=11)
    highlight_fill = PatternFill(start_color='FEF3C7', end_color='FEF3C7', fill_type='solid')

    # Sheet 1: الملخص التنفيذي
    ws1 = wb.active
    ws1.title = "الملخص التنفيذي"
    ws1.views.sheetView[0].rightToLeft = True

    ws1.merge_cells("A1:D1")
    ws1["A1"] = "قطاع تنظيم السوق البريدي - التقرير التنفيذي المالي والتشغيلي"
    ws1["A1"].font = title_font
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[1].height = 32

    ws1.merge_cells("A2:D2")
    ws1["A2"] = f"الفترة المستهدفة: السنة {year_label} - الربع {quarter_label}"
    ws1["A2"].font = subtitle_font
    ws1["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[2].height = 20

    ws1.append([])
    ws1.append(["المؤشر المالي / التشغيلي", "القيمة", "الوحدة", "ملاحظات وتفاصيل"])
    ws1.row_dimensions[4].height = 25
    for col in range(1, 5):
        cell = ws1.cell(row=4, column=col)
        cell.fill = navy_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    kpis = [
        ("إجمالي إيرادات السوق البريدي", kpi_dict.get("total_market_rev", 0.0), "جنيه مصري", "إجمالي إيرادات الصادر والمجمع"),
        ("إجمالي الصادر الداخلي", kpi_dict.get("total_local_rev", 0.0), "جنيه مصري", "حركة النقل والبريد داخل الجمهورية"),
        ("إجمالي البريد المجمع", kpi_dict.get("total_bulk_rev", 0.0), "جنيه مصري", "البريد السريع والمجمع"),
        ("إجمالي الصادر الخارجي (الدولي)", kpi_dict.get("total_intl_rev", 0.0), "جنيه مصري", "الشحنات والطرود الصادرة دولياً"),
        ("إجمالي عمولة الوارد الخارجي", kpi_dict.get("total_inbound_comm", 0.0), "جنيه مصري", "عمولات الشحنات الواردة من الخارج"),
        ("العمولة الأساسية 10%", kpi_dict.get("base_comm", 0.0), "جنيه مصري", "10% من الإيرادات الخاضعة"),
        ("(-) خصم المعاملات الوسيطة", kpi_dict.get("total_discount", 0.0), "جنيه مصري", "عمولات المعاملات الوسيطة المستبعدة"),
        ("(+) فروق المراجعة", kpi_dict.get("total_diff", 0.0), "جنيه مصري", "فروق الفحص والتدقيق"),
        ("إجمالي العمولة المستحقة للهيئة", kpi_dict.get("total_comm", 0.0), "جنيه مصري", "صافي العمولة واجبة السداد"),
        ("ضريبة القيمة المضافة 14%", kpi_dict.get("total_vat", 0.0), "جنيه مصري", "الضريبة المقررة قانوناً"),
        ("إجمالي المديونية المستحقة", kpi_dict.get("total_debt", 0.0), "جنيه مصري", "شامل العمولة وضريبة القيمة المضافة"),
        ("إجمالي عدد الشحنات المنفذة", kpi_dict.get("total_shipments", 0), "شحنة", "إجمالي حجم العمل بالعدد"),
        ("متوسط إيراد الشحنة بالسوق", kpi_dict.get("avg_shipment_price", 0.0), "جنيه / شحنة", "متوسط سعر الشحنة العام"),
        ("عدد الشركات المرخصة بالتقرير", kpi_dict.get("companies_count", 0), "شركة", "إجمالي الشركات المسجلة"),
        ("عدد الشركات ذات النشاط الفعلي", kpi_dict.get("active_companies_count", 0), "شركة", "الشركات التي حققت إيرادات > 0"),
    ]

    for r_idx, (name, val, unit, notes) in enumerate(kpis, start=5):
        ws1.row_dimensions[r_idx].height = 22
        c1 = ws1.cell(row=r_idx, column=1, value=name)
        c2 = ws1.cell(row=r_idx, column=2, value=val)
        c3 = ws1.cell(row=r_idx, column=3, value=unit)
        c4 = ws1.cell(row=r_idx, column=4, value=notes)

        is_highlight = "إجمالي العمولة" in name or "إجمالي المديونية" in name or "إجمالي إيرادات" in name
        c1.font = bold_font if is_highlight else regular_font
        c2.font = bold_font
        c3.font = regular_font
        c4.font = regular_font

        c1.alignment = Alignment(horizontal="right", vertical="center")
        c2.alignment = Alignment(horizontal="center", vertical="center")
        c3.alignment = Alignment(horizontal="center", vertical="center")
        c4.alignment = Alignment(horizontal="right", vertical="center")

        if isinstance(val, float):
            c2.number_format = '#,##0.00'
        elif isinstance(val, int):
            c2.number_format = '#,##0'

        for cell in [c1, c2, c3, c4]:
            cell.border = thin_border
            if is_highlight:
                cell.fill = highlight_fill

    # Sheet 2: الحصص السوقية وترتيب الشركات
    ws2 = wb.create_sheet(title="الحصص السوقية والترتيب")
    ws2.views.sheetView[0].rightToLeft = True

    ws2.merge_cells("A1:K1")
    ws2["A1"] = f"ترتيب الشركات والحصص السوقية - السنة {year_label} الربع {quarter_label}"
    ws2["A1"].font = title_font
    ws2["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws2.row_dimensions[1].height = 30

    ws2.append([])
    headers2 = [
        "الترتيب", "اسم الشركة", "فئة الترخيص",
        "إيراد الصادر الداخلي", "إيراد البريد المجمع", "إيراد الصادر الدولي",
        "إجمالي الإيرادات", "الحصة السوقية (%)", "عدد الشحنات",
        "متوسط عائد الشحنة", "صافي العمولة المستحقة"
    ]
    ws2.append(headers2)
    ws2.row_dimensions[3].height = 25
    for col in range(1, len(headers2) + 1):
        cell = ws2.cell(row=3, column=col)
        cell.fill = navy_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    total_market_rev = kpi_dict.get("total_market_rev", 0.0)

    for rank, (_, row) in enumerate(market_df.iterrows(), start=1):
        r_idx = rank + 3
        ws2.row_dimensions[r_idx].height = 20
        c_name = row.get("الشركة", "")
        c_cat = row.get("الفئة", "")
        loc_rev = float(row.get("إيراد الصادر الداخلي", 0.0) or 0.0)
        blk_rev = float(row.get("إيراد البريد المجمع", 0.0) or 0.0)
        intl_rev = float(row.get("إيراد الصادر الخارجي", 0.0) or 0.0)
        tot_rev = loc_rev + blk_rev + intl_rev
        share = (tot_rev / total_market_rev * 100) if total_market_rev > 0 else 0.0
        shipments = int(row.get("إجمالي عدد الشحنات", 0) or 0)
        avg_s = (tot_rev / shipments) if shipments > 0 else 0.0
        comm = float(row.get("إجمالي العمولة المحسوبة", row.get("إجمالي العمولة المستحقة", 0.0)) or 0.0)

        vals = [rank, c_name, c_cat, loc_rev, blk_rev, intl_rev, tot_rev, share, shipments, avg_s, comm]
        for c_idx, val in enumerate(vals, start=1):
            cell = ws2.cell(row=r_idx, column=c_idx, value=val)
            cell.font = regular_font
            cell.border = thin_border
            if c_idx in [1, 3]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif c_idx == 2:
                cell.alignment = Alignment(horizontal="right", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="center", vertical="center")

            if c_idx in [4, 5, 6, 7, 10, 11]:
                cell.number_format = '#,##0.00'
            elif c_idx == 8:
                cell.number_format = '0.00"%"'
            elif c_idx == 9:
                cell.number_format = '#,##0'

    # Auto-adjust column widths
    for ws in [ws1, ws2]:
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


# -----------------------------
# Session state defaults
# -----------------------------
if "extracted_report_data" not in st.session_state:
    st.session_state["extracted_report_data"] = {}

if "scan_analysis_done" not in st.session_state:
    st.session_state["scan_analysis_done"] = False


# -----------------------------
# Tabs definition
# -----------------------------
tabs = st.tabs([
    "📊 بيانات المراجعة (سمارت ريبورت)",
    "📈 لوحة المؤشرات",
    "🏢 عرض الشركات"
])

tab2, tab0, tab1 = tabs



# -----------------------------
# تبويب 0: Dashboard
# -----------------------------
with tab0:
    st.markdown('<div class="section-title">لوحة المؤشرات</div>', unsafe_allow_html=True)

    companies_data, companies_error = safe_get_json(f"{API_BASE_URL}/companies/")
    reports_data, reports_error = safe_get_json(f"{API_BASE_URL}/quarterly-reports/")

    if companies_error or reports_error:
        st.info("💡 هذه اللوحة مخصصة للتقارير الربع سنوية. لعرض مراجعات سمارت ريبورت يرجى التبديل لتبويب '📊 بيانات المراجعة (سمارت ريبورت)'.")

    # v15: فلتر الشركة الواحدة
    companies_data = apply_company_filter(companies_data)
    reports_data = apply_company_filter(reports_data, name_keys=("اسم الشركة", "company_name", "الشركة", "company"))

    companies_df = pd.DataFrame(companies_data) if companies_data else pd.DataFrame()
    reports_df = apply_official_financials_to_df(pd.DataFrame(reports_data)) if reports_data else pd.DataFrame()

    def shorten_label(text, max_len=28):
        text = safe_text(text, "")
        return text if len(text) <= max_len else text[:max_len] + "..."

    filter_col1, filter_col2, filter_col3, filter_col4, filter_col5 = st.columns(5)

    with filter_col1:
        years = ["الكل"]
        if not reports_df.empty and "السنة" in reports_df.columns:
            years += sorted(reports_df["السنة"].dropna().astype(int).unique().tolist())
        selected_year = st.selectbox("تصفية السنة", years, key="dashboard_year")

    with filter_col2:
        quarters = ["الكل"]
        if not reports_df.empty and "الربع" in reports_df.columns:
            quarters += sorted(reports_df["الربع"].dropna().astype(int).unique().tolist())
        selected_quarter = st.selectbox("تصفية الربع", quarters, key="dashboard_quarter")

    with filter_col3:
        categories = ["الكل"]
        if not reports_df.empty and "الفئة" in reports_df.columns:
            normalized_categories = (
                reports_df["الفئة"]
                .dropna()
                .astype(str)
                .apply(normalize_category)
                .unique()
                .tolist()
            )
            categories += sorted(normalized_categories)
        selected_category = st.selectbox("تصفية الفئة", categories, key="dashboard_category")

    with filter_col4:
        dashboard_mode = st.selectbox(
            "وضع العرض",
            ["لوحة كاملة", "لوحة مختصرة"],
            key="dashboard_mode"
        )

    with filter_col5:
        comps_list = []
        if not reports_df.empty and "الشركة" in reports_df.columns:
            comps_list = sorted(reports_df["الشركة"].dropna().unique().tolist())
        selected_companies = st.multiselect(
            "تصفية الشركة (متعدد)",
            options=comps_list,
            default=[],
            placeholder="الكل (اختر شركة أو أكثر...)",
            key="dashboard_company_filter"
        )
        # للتوافق مع الكود القديم
        dashboard_company = "الكل" if not selected_companies else selected_companies

    filtered_reports_df = reports_df.copy()
    excluded_comps_dict = load_excluded_companies()

    if not filtered_reports_df.empty:
        if excluded_comps_dict:
            def is_excluded(row):
                q = str(row["الربع"]) if "الربع" in row else ""
                return row["الشركة"] in excluded_comps_dict.get(q, [])
            filtered_reports_df = filtered_reports_df[~filtered_reports_df.apply(is_excluded, axis=1)]

        if selected_year != "الكل":
            filtered_reports_df = filtered_reports_df[filtered_reports_df["السنة"].astype(str) == str(selected_year)]

        if selected_quarter != "الكل":
            filtered_reports_df = filtered_reports_df[filtered_reports_df["الربع"].astype(str) == str(selected_quarter)]

        if selected_category != "الكل":
            filtered_reports_df = filtered_reports_df[
                filtered_reports_df["الفئة"].astype(str).apply(normalize_category) == selected_category
            ]

        if selected_companies:  # لو اختار شركة أو أكثر
            filtered_reports_df = filtered_reports_df[
                filtered_reports_df["الشركة"].isin(selected_companies)
            ]


    total_local_revenue = (
        filtered_reports_df["إيراد الصادر الداخلي"].sum()
        if not filtered_reports_df.empty and "إيراد الصادر الداخلي" in filtered_reports_df.columns
        else 0
    )

    total_local_shipments_count = (
        filtered_reports_df["عدد الصادر الداخلي"].sum()
        if not filtered_reports_df.empty and "عدد الصادر الداخلي" in filtered_reports_df.columns
        else 0
    )

    avg_local_shipment_price = (total_local_revenue / total_local_shipments_count) if total_local_shipments_count > 0 else 0

    total_collected_revenue = (
        filtered_reports_df["إيراد البريد المجمع"].sum()
        if not filtered_reports_df.empty and "إيراد البريد المجمع" in filtered_reports_df.columns
        else 0
    )

    total_international_revenue = (
        filtered_reports_df["إيراد الصادر الخارجي"].sum()
        if not filtered_reports_df.empty and "إيراد الصادر الخارجي" in filtered_reports_df.columns
        else 0
    )

    total_inbound_commission = (
        filtered_reports_df["عمولة الوارد"].sum()
        if not filtered_reports_df.empty and "عمولة الوارد" in filtered_reports_df.columns
        else 0
    )

    total_review_diff = (
        filtered_reports_df["فروق المراجعة"].sum()
        if not filtered_reports_df.empty and "فروق المراجعة" in filtered_reports_df.columns
        else 0
    )

    total_vat = (
        filtered_reports_df["ضريبة القيمة المضافة"].sum()
        if not filtered_reports_df.empty and "ضريبة القيمة المضافة" in filtered_reports_df.columns
        else 0
    )

    total_intermediary_discount = (
        filtered_reports_df["خصم المعاملات الوسيطة"].sum()
        if not filtered_reports_df.empty and "خصم المعاملات الوسيطة" in filtered_reports_df.columns
        else 0
    )

    base_commission = (total_local_revenue + total_collected_revenue + total_international_revenue) * 0.10
    total_commission = (
        filtered_reports_df["إجمالي العمولة المستحقة"].sum()
        if not filtered_reports_df.empty and "إجمالي العمولة المستحقة" in filtered_reports_df.columns
        else (
            filtered_reports_df["العمولة قبل التقريب"].sum()
            if not filtered_reports_df.empty and "العمولة قبل التقريب" in filtered_reports_df.columns
            else 0
        )
    )
    total_indebtedness_sum = (
        filtered_reports_df["إجمالي المديونية"].sum()
        if not filtered_reports_df.empty and "إجمالي المديونية" in filtered_reports_df.columns
        else 0
    )

    review_diff_percentage = (total_review_diff / total_commission * 100) if total_commission > 0 else 0

    total_shipments = (
        filtered_reports_df["إجمالي عدد الشحنات"].sum()
        if not filtered_reports_df.empty and "إجمالي عدد الشحنات" in filtered_reports_df.columns
        else 0
    )

    total_weights = (
        filtered_reports_df["إجمالي الأوزان"].sum()
        if not filtered_reports_df.empty and "إجمالي الأوزان" in filtered_reports_df.columns
        else 0
    )

    companies_count = len(companies_df) if not companies_df.empty else 0
    reports_count = len(filtered_reports_df) if not filtered_reports_df.empty else 0

    total_market_revenue = float(total_local_revenue) + float(total_collected_revenue) + float(total_international_revenue)
    avg_market_shipment_price = (total_market_revenue / total_shipments) if total_shipments > 0 else 0.0

    col_hdr, col_dl = st.columns([3, 1.2])
    with col_hdr:
        st.markdown('<div class="subsection-title" style="margin-top:0;">مؤشرات النشاط المالي والتشغيلي</div>', unsafe_allow_html=True)
    with col_dl:
        if not filtered_reports_df.empty:
            active_count = 0
            if "إيراد الصادر الداخلي" in filtered_reports_df.columns:
                rev_sum_s = (
                    filtered_reports_df["إيراد الصادر الداخلي"].fillna(0)
                    + (filtered_reports_df["إيراد البريد المجمع"].fillna(0) if "إيراد البريد المجمع" in filtered_reports_df.columns else 0)
                    + (filtered_reports_df["إيراد الصادر الخارجي"].fillna(0) if "إيراد الصادر الخارجي" in filtered_reports_df.columns else 0)
                )
                active_count = int((rev_sum_s > 0).sum())

            kpi_dict = {
                "total_market_rev": total_market_revenue,
                "total_local_rev": total_local_revenue,
                "total_bulk_rev": total_collected_revenue,
                "total_intl_rev": total_international_revenue,
                "total_inbound_comm": total_inbound_commission,
                "base_comm": base_commission,
                "total_discount": total_intermediary_discount,
                "total_diff": total_review_diff,
                "total_comm": total_commission,
                "total_vat": total_vat,
                "total_debt": total_indebtedness_sum,
                "total_shipments": int(total_shipments),
                "avg_shipment_price": avg_market_shipment_price,
                "companies_count": companies_count,
                "active_companies_count": active_count,
            }

            # Generate and allow direct download
            try:
                exec_excel = generate_executive_summary_excel(filtered_reports_df, str(selected_year), str(selected_quarter), kpi_dict)
                st.download_button(
                    label="📥 تحميل التقرير التنفيذي (Excel)",
                    data=exec_excel,
                    file_name=f"تقرير_تنفيذي_{selected_year}_Q{selected_quarter}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except Exception as e:
                st.caption(f"خطأ في التقرير التنفيذي: {e}")

    n1, n2, n3, n4 = st.columns(4)

    with n1:
        metric_card("الصادر الداخلي", f"{total_local_revenue:,.2f}", "blue")
    with n2:
        metric_card("البريد المجمع", f"{total_collected_revenue:,.2f}", "purple")
    with n3:
        metric_card("الصادر الخارجي", f"{total_international_revenue:,.2f}", "green")
    with n4:
        metric_card("الوارد", f"{total_inbound_commission:,.2f}", "orange")

    st.markdown('<div class="subsection-title">المؤشرات الأساسية</div>', unsafe_allow_html=True)
    m1, m2, m3, m4, m5 = st.columns(5)

    with m1:
        metric_card("عدد التقارير", f"{reports_count}", "cyan")
    with m2:
        metric_card("إجمالي العمولة المستحقة", f"{total_commission:,.2f}", "red red-pulse")
    with m3:
        metric_card("خصم المعاملات الوسيطة", f"{total_intermediary_discount:,.2f}", "orange")
    with m4:
        metric_card("ضريبة القيمة المضافة", f"{total_vat:,.2f}", "purple")
    with m5:
        metric_card("إجمالي المديونية", f"{total_indebtedness_sum:,.2f}", "green")

    st.markdown('<div class="subsection-title">مؤشرات إضافية</div>', unsafe_allow_html=True)
               
    extra1, extra2, extra3, extra4 = st.columns(4)

    with extra1:
        metric_card("إجمالي عدد الشحنات", f"{int(total_shipments):,}", "blue")
    with extra2:
        metric_card("متوسط سعر شحنة الصادر الداخلي", f"{avg_local_shipment_price:,.2f}", "cyan")
    with extra3:
        metric_card("فروق المراجعة", f"{total_review_diff:,.2f}", "gold")
    with extra4:
        metric_card("نسبة فروق المراجعة", f"{review_diff_percentage:,.2f}%", "orange")

    if not filtered_reports_df.empty:
        work_df = filtered_reports_df.copy()

        work_df = apply_official_financials_to_df(work_df)
        for c in ["إجمالي عدد الشحنات", "إجمالي الأوزان", "عمولة الوارد", "إجمالي العمولة المحسوبة", "خصم المعاملات الوسيطة", "فروق المراجعة", "ضريبة القيمة المضافة"]:
            if c not in work_df.columns:
                work_df[c] = 0.0
            work_df[c] = pd.to_numeric(work_df[c], errors="coerce").fillna(0.0)

        summary_df = (
            work_df.groupby(["الشركة", "الفئة"], as_index=False).agg({
                "إيراد الصادر الداخلي": "sum",
                "إيراد البريد المجمع": "sum",
                "إيراد الصادر الخارجي": "sum",
                "عمولة الوارد": "sum",
                "إجمالي العمولة المستحقة": "sum",
                "إجمالي العمولة المحسوبة": "sum",
                "خصم المعاملات الوسيطة": "sum",
                "فروق المراجعة": "sum",
                "ضريبة القيمة المضافة": "sum",
                "إجمالي عدد الشحنات": "sum",
                "إجمالي الأوزان": "sum"
            }).sort_values("إجمالي العمولة المستحقة", ascending=False)
        )

        # حساب إجمالي الإيرادات والحصة من العمولة ومتوسط الشحنة
        summary_df["إجمالي الإيرادات"] = (
            summary_df["إيراد الصادر الداخلي"].fillna(0)
            + summary_df["إيراد البريد المجمع"].fillna(0)
            + summary_df["إيراد الصادر الخارجي"].fillna(0)
        )
        total_market_calc = summary_df["إجمالي الإيرادات"].sum()
        summary_df["الحصة السوقية %"] = (
            (summary_df["إجمالي الإيرادات"] / total_market_calc * 100).round(2)
            if total_market_calc > 0 else 0.0
        )
        total_comm_calc = summary_df["إجمالي العمولة المستحقة"].sum()
        summary_df["نسبة العمولة %"] = (
            (summary_df["إجمالي العمولة المستحقة"] / total_comm_calc * 100).round(2)
            if total_comm_calc > 0 else 0.0
        )
        summary_df["متوسط عائد الشحنة"] = summary_df.apply(
            lambda r: round(r["إجمالي الإيرادات"] / r["إجمالي عدد الشحنات"], 2)
            if r["إجمالي عدد الشحنات"] > 0 else 0.0,
            axis=1
        )

        # ---------------------------------------------
        # 1. قسم الحصة السوقية ونسبة الاستحواذ على العمولة المستحقة
        # ---------------------------------------------
        st.markdown('<div class="subsection-title">📊 الحصة ونسبة الاستحواذ على إجمالي العمولة المستحقة</div>', unsafe_allow_html=True)
        ms_col1, ms_col2 = st.columns([1.1, 1.3])

        with ms_col1:
            active_comm_df = summary_df[summary_df["إجمالي العمولة المستحقة"] > 0].sort_values("إجمالي العمولة المستحقة", ascending=False)
            if not active_comm_df.empty:
                # إذا زاد عدد الشركات عن 6 شركات، نعرض أعلى 5 شركات ونجمع باقي الشركات في شريحة "أخرى" للحفاظ على وضوح وجمال الرسم
                if len(active_comm_df) > 6:
                    top_n = active_comm_df.iloc[:5]
                    other_sum = active_comm_df.iloc[5:]["إجمالي العمولة المستحقة"].sum()
                    other_count = len(active_comm_df) - 5
                    donut_labels = [shorten_label(x, 24) for x in top_n["الشركة"].tolist()] + [f"باقي الشركات ({other_count})"]
                    donut_values = top_n["إجمالي العمولة المستحقة"].tolist() + [other_sum]
                    donut_colors = ["#2563eb", "#059669", "#7c3aed", "#f97316", "#0891b2", "#94a3b8"]
                    donut_title = "نسبة العمولة (أعلى 5 شركات + أخرى)"
                else:
                    donut_labels = [shorten_label(x, 26) for x in active_comm_df["الشركة"].tolist()]
                    donut_values = active_comm_df["إجمالي العمولة المستحقة"].tolist()
                    donut_colors = ["#2563eb", "#059669", "#7c3aed", "#f97316", "#dc2626"]
                    donut_title = "الحصة من إجمالي العمولة المستحقة"

                plotly_donut(
                    donut_labels,
                    donut_values,
                    donut_title,
                    colors=donut_colors
                )
                st.caption("💡 **ماذا يعني هذا الشكل؟** يوضح النسبة المئوية لمساهمة كل شركة من إجمالي العمولة المستحقة للهيئة ككل. (إذا زاد عدد الشركات النشطة، يتم عرض كبار المتصدرين وتجميع الباقي تلقائياً في شريحة موحدة لضمان وضوح الرسم).")
            else:
                st.info("لا توجد عمولة مسجلة للشركات في الفترة المحددة")

        with ms_col2:
            st.markdown('<div class="section-title" style="font-size: 16px; margin-bottom: 12px;">🏆 جدول ترتيب الشركات حسب العمولة المستحقة</div>', unsafe_allow_html=True)
            table_ms_df = summary_df.copy().sort_values("إجمالي العمولة المستحقة", ascending=False).reset_index(drop=True)
            table_ms_df["الترتيب"] = range(1, len(table_ms_df) + 1)
            table_ms_df["حالة النشاط"] = table_ms_df["إجمالي العمولة المستحقة"].apply(lambda v: "🟢 نشطة" if v > 0 else "⚪ إقرار صفري")

            display_ms_df = pd.DataFrame({
                "الترتيب": table_ms_df["الترتيب"],
                "الشركة": table_ms_df["الشركة"],
                "الفئة": table_ms_df["الفئة"],
                "العمولة المستحقة (ج.م)": table_ms_df["إجمالي العمولة المستحقة"].apply(lambda x: f"{x:,.2f}"),
                "نسبة المساهمة": table_ms_df["نسبة العمولة %"].apply(lambda x: f"{x:.2f}%"),
                "النشاط": table_ms_df["حالة النشاط"]
            })
            boxed_dataframe(display_ms_df)
            st.caption("💡 **شرح الجدول:** يرتب كافة الشركات تنازلياً من الأعلى عمولة مستحقة للهيئة إلى الأقل، ويتيح التمرير والبحث مهما بلغ عدد الشركات (🟢 نشطة / ⚪ إقرار صفري).")


        row1_col1, row1_col2 = st.columns(2)


        with row1_col1:
            if not companies_df.empty and "الفئة" in companies_df.columns:
                st.markdown('<div class="subsection-title">توزيع عدد الشركات المسجلة حسب الفئة</div>', unsafe_allow_html=True)

                normalized_company_categories = (
                    companies_df["الفئة"]
                    .dropna()
                    .astype(str)
                    .apply(normalize_category)
                )

                category_order = ["داخلي", "مجمع", "داخلي + مجمع", "شامل"]
                category_counts = (
                    normalized_company_categories
                    .value_counts()
                    .reindex(category_order, fill_value=0)
                )

                plotly_donut(
                    category_counts.index.tolist(),
                    category_counts.values.tolist(),
                    "توزيع عدد الشركات المسجلة حسب الفئة (بالعدد)",
                    colors=["#2563eb", "#f97316", "#16a34a", "#dc2626"]
                )
                st.caption("💡 **ماذا يعني هذا الشكل؟** يوضح تراخيص الشركات الخمس المسجلة: 2 شركات ترخيص شامل (40%)، 2 داخلي (40%)، وشركة واحدة داخلي + مجمع (20%)، بغض النظر عن كونها حققت مبيعات أم لا.")

        with row1_col2:
            st.markdown('<div class="subsection-title">توزيع العمولة على الفئات</div>', unsafe_allow_html=True)

            commission_by_category_df = (
                summary_df.groupby("الفئة", as_index=False)["إجمالي العمولة المحسوبة"]
                .sum()
                .sort_values("إجمالي العمولة المحسوبة", ascending=False)
            )

            plotly_horizontal_bar(
                commission_by_category_df["الفئة"].tolist(),
                commission_by_category_df["إجمالي العمولة المحسوبة"].tolist(),
                "توزيع العمولة على الفئات",
                "إجمالي العمولة",
                color="#7c3aed"
            )
            st.caption("💡 **ماذا يعني هذا الرسم؟** يوضح أي فئة ترخيص تورّد أكبر مبالغ عمولة لهيئة البريد (10% رسم ترخيص).")

        st.markdown('<div class="subsection-title">أفضل 10 شركات حسب العمولة</div>', unsafe_allow_html=True)
        top_commission_df = (
            summary_df.groupby("الشركة", as_index=False)["إجمالي العمولة المحسوبة"]
            .sum()
            .sort_values("إجمالي العمولة المحسوبة", ascending=False)
            .head(10)
        )

        plotly_horizontal_bar(
            [shorten_label(x, 35) for x in top_commission_df["الشركة"].tolist()],
            top_commission_df["إجمالي العمولة المحسوبة"].tolist(),
            "أفضل 10 شركات حسب العمولة",
            "العمولة",
            color="#059669"
        )
        st.caption("💡 **الشرح:** يرتب الشركات بحسب أعلى مبالغ عمولة مستحقة الدفع للهيئة.")

        st.markdown('<div class="subsection-title">أعلى 10 شركات حسب عدد الشحنات</div>', unsafe_allow_html=True)
        top_shipments_df = (
            summary_df.groupby("الشركة", as_index=False)["إجمالي عدد الشحنات"]
            .sum()
            .sort_values("إجمالي عدد الشحنات", ascending=False)
            .head(10)
        )

        plotly_horizontal_bar(
            [shorten_label(x, 35) for x in top_shipments_df["الشركة"].tolist()],
            top_shipments_df["إجمالي عدد الشحنات"].tolist(),
            "أعلى 10 شركات حسب عدد الشحنات",
            "عدد الشحنات",
            color="#ea580c"
        )
        st.caption("💡 **الشرح:** يرتب الشركات حسب حجم العمل الفعلي الميداني وعدد الطرود المنقولة.")

        if dashboard_mode == "لوحة كاملة":
            st.markdown('<div class="subsection-title">الإيرادات حسب الفئة</div>', unsafe_allow_html=True)

            revenue_by_category_df = (
                work_df.groupby("الفئة", as_index=False).agg({
                    "إيراد الصادر الداخلي": "sum",
                    "إيراد البريد المجمع": "sum",
                    "إيراد الصادر الخارجي": "sum"
                })
            )
            revenue_by_category_df["إجمالي الإيرادات"] = (
                revenue_by_category_df["إيراد الصادر الداخلي"].fillna(0) +
                revenue_by_category_df["إيراد البريد المجمع"].fillna(0) +
                revenue_by_category_df["إيراد الصادر الخارجي"].fillna(0)
            )
            revenue_by_category_df["الفئة"] = revenue_by_category_df["الفئة"].astype(str).apply(normalize_category)

            plotly_horizontal_bar(
                revenue_by_category_df["الفئة"].tolist(),
                revenue_by_category_df["إجمالي الإيرادات"].tolist(),
                "الإيرادات حسب الفئة",
                "الإيرادات",
                color="#2563eb"
            )



            st.markdown('<div class="subsection-title">متوسط العمولة لكل شركة</div>', unsafe_allow_html=True)

            avg_commission_df = (
                summary_df.groupby("الشركة", as_index=False)["إجمالي العمولة المحسوبة"]
                .mean()
                .sort_values("إجمالي العمولة المحسوبة", ascending=False)
                .head(10)
            )

            plotly_horizontal_bar(
                [shorten_label(x, 35) for x in avg_commission_df["الشركة"].tolist()],
                avg_commission_df["إجمالي العمولة المحسوبة"].tolist(),
                "متوسط العمولة لكل شركة",
                "متوسط العمولة",
                color="#8b5cf6"
            )

            st.markdown('<div class="subsection-title">أعلى 10 شركات حسب الوارد</div>', unsafe_allow_html=True)

            inbound_df = (
                summary_df.groupby("الشركة", as_index=False)["عمولة الوارد"]
                .sum()
                .sort_values("عمولة الوارد", ascending=False)
                .head(10)
            )

            plotly_horizontal_bar(
                [shorten_label(x, 35) for x in inbound_df["الشركة"].tolist()],
                inbound_df["عمولة الوارد"].tolist(),
                "أعلى 10 شركات حسب الوارد",
                "الوارد",
                color="#f97316"
            )

            st.markdown('<div class="subsection-title">مقارنة الداخلي / المجمع / الخارجي</div>', unsafe_allow_html=True)

            activity_compare_df = pd.DataFrame({
                "النشاط": ["الصادر الداخلي", "البريد المجمع", "الصادر الخارجي"],
                "القيمة": [total_local_revenue, total_collected_revenue, total_international_revenue]
            })

            plotly_vertical_bar(
                activity_compare_df["النشاط"].tolist(),
                activity_compare_df["القيمة"].tolist(),
                "مقارنة الداخلي / المجمع / الخارجي",
                "القيمة",
                color="#10b981"
            )

        if "السنة" in work_df.columns and work_df["السنة"].nunique() > 1:
            st.markdown('<div class="subsection-title">مقارنة السنوات</div>', unsafe_allow_html=True)

            by_year_df = (
                work_df.groupby("السنة", as_index=False).agg({
                    "إجمالي العمولة المحسوبة": "sum",
                    "فروق المراجعة": "sum",
                    "ضريبة القيمة المضافة": "sum"
                }).sort_values("السنة")
            )

            plotly_stacked_bar(
                by_year_df["السنة"].tolist(),
                [
                    ("العمولة", by_year_df["إجمالي العمولة المحسوبة"].tolist()),
                    ("فروق المراجعة", by_year_df["فروق المراجعة"].tolist()),
                    ("ضريبة القيمة المضافة", by_year_df["ضريبة القيمة المضافة"].tolist()),
                ],
                "مقارنة السنوات",
                "القيمة"
            )

        st.markdown('<div class="subsection-title">جدول ملخص حسب الشركة</div>', unsafe_allow_html=True)
        boxed_dataframe(summary_df)
    else:
        st.info("لا توجد تقارير كافية لعرض مؤشرات الداشبورد")


# -----------------------------
# تبويب 1: عرض الشركات
# -----------------------------
with tab1:
    st.subheader("عرض الشركات المسجلة")

    companies_data, companies_error = safe_get_json(f"{API_BASE_URL}/companies/")
    reports_data, _ = safe_get_json(f"{API_BASE_URL}/quarterly-reports/")

    # v15: فلتر الشركة الواحدة
    companies_data = apply_company_filter(companies_data)
    reports_data = apply_company_filter(reports_data, name_keys=("اسم الشركة", "company_name", "الشركة", "company"))

    if companies_error:
        st.error(f"تعذر الاتصال بالخادم: {companies_error}")
    elif companies_data:
        df = pd.DataFrame(companies_data)
        if "رقم الرخصة" in df.columns:
            df["رقم الرخصة"] = df["رقم الرخصة"].astype(str).str.replace(r'\.0$', '', regex=True)
        if "اسم الشركة" in df.columns:
            df = df.drop_duplicates(subset=["اسم الشركة"])

        reports_df = apply_official_financials_to_df(pd.DataFrame(reports_data)) if reports_data else pd.DataFrame()
        if not reports_df.empty and "رقم الرخصة" in reports_df.columns:
            reports_df["رقم الرخصة"] = reports_df["رقم الرخصة"].astype(str).str.replace(r'\.0$', '', regex=True)

        # --- فلتر تلقائي: عرض فقط الشركات التي لها تقارير فعلية ---
        companies_with_reports = set()
        if not reports_df.empty and "الشركة" in reports_df.columns:
            companies_with_reports = set(reports_df["الشركة"].dropna().unique().tolist())

        st.markdown("### إدارة استبعاد الشركات من المؤشرات")
        current_excluded = load_excluded_companies()

        # قائمة الأرباع المتاحة فعلياً من التقارير الموجودة
        available_quarters = ["الكل"]
        if not reports_df.empty and "الربع" in reports_df.columns:
            qs = sorted(reports_df["الربع"].dropna().astype(str).unique().tolist())
            available_quarters += qs

        excl_q = st.selectbox("اختر الربع (سيتم عرض الشركات التي لها تقارير فقط لهذا الربع):", available_quarters, key="excl_q_sel")

        if excl_q != "الكل" and not reports_df.empty and "الربع" in reports_df.columns:
            comps_in_q = reports_df[reports_df["الربع"].astype(str) == str(excl_q)]["الشركة"].unique().tolist()
            df = df[df["اسم الشركة"].isin(comps_in_q)]
        elif companies_with_reports:
            # بدون تحديد ربع: عرض الشركات التي لها أي تقرير فعلي فقط
            df = df[df["اسم الشركة"].isin(companies_with_reports)]

        if "اسم الشركة" in df.columns:
            df = df.drop_duplicates(subset=["اسم الشركة"])

        all_comps = sorted(df["اسم الشركة"].dropna().unique().tolist()) if "اسم الشركة" in df.columns else []

        if excl_q != "الكل":
            q_excluded = current_excluded.get(excl_q, [])
            
            new_excluded = st.multiselect(
                f"حدد الشركات التي ترغب في استبعادها من الربع {excl_q} (لن تظهر بياناتها في ذلك الربع):",
                options=all_comps,
                default=[c for c in q_excluded if c in all_comps],
                key="dashboard_exclude_multiselect"
            )
            
            if new_excluded != q_excluded:
                current_excluded[excl_q] = new_excluded
                save_excluded_companies(current_excluded)
                st.rerun()
                
            df["مستبعدة من المؤشرات"] = df["اسم الشركة"].apply(lambda x: "نعم" if x in new_excluded else "لا")
        else:
            df["مستبعدة من المؤشرات"] = "لا ينطبق"

        st.markdown("---")
        st.markdown("### البحث والتصفية")

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            search_name = st.text_input("بحث باسم الشركة", key="search_company_name")

        with col2:
            search_license = st.text_input("بحث برقم الرخصة", key="search_company_license")

        with col3:
            categories = ["الكل"] + sorted(df["الفئة"].dropna().astype(str).unique().tolist())
            selected_category = st.selectbox("تصفية بالفئة", categories, key="filter_company_category")

        with col4:
            weight_options = ["الكل", "نعم", "لا"]
            selected_weight = st.selectbox("تصفية باستخدام الأوزان", weight_options, key="filter_company_weight")

        with col5:
            exclude_options = ["الكل", "مستبعدة", "غير مستبعدة"]
            selected_exclude = st.selectbox("حالة الاستبعاد", exclude_options, key="filter_company_excluded")

        filtered_df = df.copy()

        if search_name.strip():
            filtered_df = filtered_df[
                filtered_df["اسم الشركة"].astype(str).str.contains(search_name.strip(), case=False, na=False)
            ]

        if search_license.strip():
            filtered_df = filtered_df[
                filtered_df["رقم الرخصة"].astype(str).str.contains(search_license.strip(), case=False, na=False)
            ]

        if selected_category != "الكل":
            filtered_df = filtered_df[filtered_df["الفئة"] == selected_category]

        if selected_weight != "الكل":
            weight_bool = True if selected_weight == "نعم" else False
            filtered_df = filtered_df[filtered_df["تستخدم الأوزان"] == weight_bool]

        if selected_exclude != "الكل":
            is_ex = "نعم" if selected_exclude == "مستبعدة" else "لا"
            filtered_df = filtered_df[filtered_df["مستبعدة من المؤشرات"] == is_ex]

        st.markdown("### ملخص سريع")
        c1, c2, c3 = st.columns(3)
        c1.metric("عدد الشركات المعروضة", len(filtered_df))
        c2.metric("عدد الشركات التي تستخدم الأوزان", int(filtered_df["تستخدم الأوزان"].sum()) if not filtered_df.empty else 0)
        c3.metric("عدد الشركات التي لا تستخدم الأوزان", int((~filtered_df["تستخدم الأوزان"]).sum()) if not filtered_df.empty else 0)

        st.markdown("### النتائج")
        boxed_dataframe(filtered_df)

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            filtered_df.to_excel(writer, index=False, sheet_name="Companies")
        output.seek(0)

        st.download_button(
            label="تنزيل الشركات المعروضة Excel",
            data=output,
            file_name="filtered_companies.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("لا توجد شركات مسجلة بعد")


# -----------------------------
# تبويب 2: بيانات المراجعة من سمارت ريبورت
# -----------------------------
with tab2:
    st.subheader("📊 بيانات المراجعة (سمارت ريبورت)")
    st.info("هذه البيانات تأتي مباشرة من الموظفين عبر الإنترنت.")
    csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQMArVLudMJy8j440FcHbxKDaRowoGc1HHwuvyUbDrQjJct04V0XvDHRp-_KaNdOsj4CwK_ArPcZ3aK/pub?gid=1721910400&single=true&output=csv"
    
    try:
        # Read as string to prevent crash, clean empty rows, then safely convert numbers
        df = pd.read_csv(csv_url, dtype=str)
        import numpy as np
        df.replace(r'^\s*$', np.nan, regex=True, inplace=True)
        df.dropna(how='all', inplace=True)
        
        # Safely convert columns to numeric without destroying string columns like names/notes
        for col in df.columns:
            try:
                # Attempt to convert to numeric. If it fails (e.g. string col), keep original
                numeric_col = pd.to_numeric(df[col])
                df[col] = numeric_col
            except:
                pass

        # Load deleted reports from Supabase (persistent across restarts)
        import json
        deleted_file = 'deleted_reports.json'  # kept for fallback only
        deleted_list = []
        if get_deleted_reports is not None:
            try:
                deleted_list = get_deleted_reports()
            except Exception:
                pass
        if not deleted_list and os.path.exists(deleted_file):
            try:
                with open(deleted_file, 'r', encoding='utf-8') as f:
                    deleted_list = json.load(f)
            except:
                pass
        
        # استبعاد حسابات الاختبار تلقائياً
        emp_col_test = [c for c in df.columns if "اسم الموظف" in c or "الموظف" in c]
        if emp_col_test:
            df = df[~df[emp_col_test[0]].astype(str).str.strip().str.lower().isin(['test_agent', 'test', 'ggggg'])]

        # تطبيق حذف التقارير المحددة بواسطة المشرف
        if not df.empty and len(deleted_list) > 0:
            comp_col = [c for c in df.columns if "اسم الشركة" in c]
            lic_col = [c for c in df.columns if "رقم الترخيص" in c or ("الترخيص" in c and "فئة" not in c)]
            date_col = [c for c in df.columns if "التاريخ" in c]
            
            if comp_col and lic_col and date_col:
                c_c = comp_col[0]
                l_c = lic_col[0]
                d_c = date_col[0]
                
                def is_deleted(row):
                    # مفتاح فريد بالشركة والرخصة والتاريخ عشان ما يحظرش الشركة كلها
                    key_full = f"{str(row.get(c_c, '')).strip()}_{str(row.get(l_c, '')).strip()}_{str(row.get(d_c, '')).strip()}"
                    return key_full in deleted_list
                
                df = df[~df.apply(is_deleted, axis=1)]
        
        # Dashboard metrics
        if not df.empty:
            st.markdown("""
            <style>
            .chic-table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                font-size: 16px;
                text-align: center;
                direction: rtl;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                border-radius: 8px;
                overflow: hidden;
            }
            .chic-table thead tr {
                background-color: #2e7d32;
                color: white;
                font-weight: bold;
            }
            .chic-table th, .chic-table td {
                padding: 12px 15px;
                border: 1px solid #ddd;
            }
            .chic-table tbody tr {
                background-color: #f9f9f9;
            }
            .chic-table tbody tr:nth-of-type(even) {
                background-color: #f1f1f1;
            }
            .chic-table tbody tr:hover {
                background-color: #e8f5e9;
            }
            .chic-summary {
                background-color: #fff9c4;
                font-weight: bold;
                font-size: 18px;
            }
            .chic-final {
                background-color: #c8e6c9;
                font-weight: bold;
                font-size: 18px;
                color: #1b5e20;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Helper to get sum safely
            def clean_numeric(val):
                if pd.isna(val): return 0.0
                s = str(val).replace('\u066b', '.').replace('\u066c', '').replace(',', '')
                try:
                    return float(s)
                except:
                    return 0.0

            def get_sum(col_name):
                matched = [c for c in df.columns if col_name in c]
                if matched:
                    return df[matched[0]].apply(clean_numeric).sum()
                return 0
            
            # Calculate metrics
            count_local = get_sum("عدد الصادر المحلي")
            val_local = get_sum("إيراد الصادر المحلي")
            
            count_intl = get_sum("عدد الصادر الدولي")
            val_intl = get_sum("إيراد الصادر الدولي")
            
            count_bulk = get_sum("عدد البريد المجمّع")
            val_bulk = get_sum("إيراد البريد المجمّع")
            
            val_ext = get_sum("عمولة الوارد الخارجي")
            
            val_diff = get_sum("فروق المراجعة")
            val_ded = get_sum("خصم عمولة المعاملات الوسيطة")
            val_vat = get_sum("القيمة المضافة")
            
            total_comm = get_sum("إجمالي العمولة المستحقة")
            total_debt = get_sum("إجمالي المديونية المستحقة")
            
            table_html = f"""
            <table class="chic-table">
                <thead>
                    <tr>
                        <th rowspan="2">البيان</th>
                        <th colspan="2">الصادر الداخلي</th>
                        <th colspan="2">الصادر الخارجي (الدولي)</th>
                        <th colspan="2">البريد المجمّع</th>
                        <th>الوارد الخارجي</th>
                    </tr>
                    <tr>
                        <th>العدد</th>
                        <th>الإيراد</th>
                        <th>العدد</th>
                        <th>الإيراد</th>
                        <th>العدد</th>
                        <th>الإيراد</th>
                        <th>العمولة</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>الإجماليات</strong></td>
                        <td>{count_local:.0f}</td>
                        <td>{val_local:,.2f}</td>
                        <td>{count_intl:.0f}</td>
                        <td>{val_intl:,.2f}</td>
                        <td>{count_bulk:.0f}</td>
                        <td>{val_bulk:,.2f}</td>
                        <td>{val_ext:,.2f}</td>
                    </tr>
                    <tr>
                        <td colspan="7" style="text-align: left; padding-left: 20px;"><strong>(-) خصم عمولة المعاملات الوسيطة</strong></td>
                        <td style="color: red;">{val_ded:,.2f}</td>
                    </tr>
                    <tr>
                        <td colspan="7" style="text-align: left; padding-left: 20px;"><strong>(+) فروق المراجعة</strong></td>
                        <td style="color: green;">{val_diff:,.2f}</td>
                    </tr>
                    <tr class="chic-summary">
                        <td colspan="7" style="text-align: left; padding-left: 20px;">إجمالي العمولة المستحقة</td>
                        <td>{total_comm:,.2f}</td>
                    </tr>
                    <tr class="chic-summary" style="background-color: #fff59d;">
                        <td colspan="7" style="text-align: left; padding-left: 20px;">ضريبة القيمة المضافة</td>
                        <td>{val_vat:,.2f}</td>
                    </tr>
                    <tr class="chic-final">
                        <td colspan="7" style="text-align: left; padding-left: 20px;">إجمالي المديونية المستحقة</td>
                        <td>{total_debt:,.2f}</td>
                    </tr>
                </tbody>
            </table>
            """
            
            col1, col2 = st.columns([4, 1.5])
            with col1:
                st.markdown(table_html, unsafe_allow_html=True)
            with col2:
                st.markdown('<div class="section-title" style="font-size: 18px; text-align: center; margin-bottom: 15px;">📊 إحصائيات المراجعين</div>', unsafe_allow_html=True)
                
                emp_col = [c for c in df.columns if "اسم الموظف" in c or "الموظف" in c]
                if emp_col:
                    emp_col = emp_col[0]
                    import re
                    def clean_reviewer_name(name):
                        if pd.isna(name): return "غير محدد"
                        s = str(name).strip()
                        s = re.sub(r'\s+', ' ', s)
                        s_lower = s.lower()
                        if 'khaled' in s_lower and 'ahmed' in s_lower:
                            return 'احمد خالد'
                        s = s.replace('أحمد', 'احمد').replace('إبراهيم', 'ابراهيم')
                        return s

                    cleaned_series = df[emp_col].apply(clean_reviewer_name)
                    reviewer_counts = cleaned_series.value_counts().reset_index()
                    reviewer_counts.columns = ['اسم المراجع', 'التقارير']
                    
                    total_reports = len(df)
                    
                    st.dataframe(
                        reviewer_counts,
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    st.markdown(f'''
                    <div style="background-color: #e8f5e9; padding: 12px; border-radius: 8px; border-right: 4px solid #2e7d32; margin-top: 10px; text-align: center;">
                        <span style="font-size: 14px; color: #1b5e20; font-weight: bold;">إجمالي التقارير</span>
                        <br>
                        <span style="font-size: 24px; color: #1b5e20; font-weight: bold;">{total_reports}</span>
                    </div>
                    ''', unsafe_allow_html=True)
                else:
                    st.warning("لم يتم العثور على عمود اسم الموظف")
            
            st.divider()

            st.divider()
            st.markdown("### 🔄 ترحيل البيانات للبرنامج الأساسي")
            st.markdown("ترحيل وتخزين كافة تقارير الموظفين مباشرة إلى قاعدة البيانات السحابية (Supabase) لتنعكس فوراً في لوحة المؤشرات.")
            
            mig_col1, mig_col2, mig_col3 = st.columns([1, 1, 2])
            with mig_col1:
                migration_year = st.selectbox("السنة المستهدفة للترحيل:", [2024, 2025, 2026, 2027], index=2, key="mig_year")
            with mig_col2:
                migration_quarter = st.selectbox("الربع المستهدف للترحيل:", [1, 2, 3, 4], index=2, key="mig_quarter")
                
            with mig_col3:
                st.write("")
                st.write("")
                if st.button("🚀 بدء ترحيل البيانات وحفظها", type="primary", use_container_width=True):
                    with st.spinner("جاري تسجيل الشركات وترحيل بيانات التقارير إلى السيرفر السحابي Supabase..."):
                        try:
                            if migrate_smart_reports:
                                ok, msg = migrate_smart_reports(df, migration_year, migration_quarter, deleted_list)
                                if ok:
                                    st.session_state.pending_dashboard_year = int(migration_year)
                                    st.session_state.pending_dashboard_quarter = str(migration_quarter)
                                    st.session_state.pending_dashboard_mode = "لوحة كاملة"
                                    st.success(f"🎉 {msg} تم ضبط الإعدادات تلقائياً. اذهب الآن إلى تبويب 'لوحة المؤشرات' للاطلاع عليها.")
                                    time.sleep(1.5)
                                    st.rerun()
                                else:
                                    st.error(msg)
                            else:
                                st.error("وحدة الاتصال بقاعدة البيانات غير متوفرة.")
                        except Exception as e:
                            st.error(f"حدث خطأ أثناء الترحيل: {e}")

            st.divider()
            st.markdown("### ⚙️ إدارة التقارير")
            
            manage_col1, manage_col2 = st.columns(2)
            
            with manage_col1:
                st.markdown("#### 📥 تصدير البيانات")
                
                # Create a copy for export with Totals row
                export_df = df.copy()
                
                # Clean numeric columns (Google Sheets might send numbers as strings with commas)
                for c in export_df.columns:
                    if not pd.api.types.is_numeric_dtype(export_df[c]):
                        try:
                            # Replace arabic decimals and thousands separators
                            s = export_df[c].astype(str).str.replace('٫', '.').str.replace('٬', '').str.replace(',', '').str.strip()
                            export_df[c] = pd.to_numeric(s)
                        except:
                            pass
                
                numeric_cols = export_df.select_dtypes(include=['number']).columns
                
                # Create totals row
                totals = pd.Series(index=export_df.columns, dtype=object)
                totals = totals.fillna(None)
                totals[export_df.columns[0]] = "الإجماليات"
                
                for col in numeric_cols:
                    # Avoid summing ID-like columns
                    if "رقم" not in col and "الترخيص" not in col:
                        totals[col] = export_df[col].sum()
                
                export_df.reset_index(drop=True, inplace=True)
                export_df.loc[len(export_df)] = totals
                
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    export_df.to_excel(writer, index=False, sheet_name='التقارير')
                excel_data = output.getvalue()
                
                st.download_button(
                    label="📥 تصدير الإكسيل",
                    data=excel_data,
                    file_name="تقارير_الموظفين.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                
            with manage_col2:
                st.markdown("#### 🗑️ حذف تقرير")
                with st.expander("حذف تقرير (للمشرفين)"):
                    if not df.empty:
                        comp_col = [c for c in df.columns if "اسم الشركة" in c]
                        lic_col = [c for c in df.columns if "رقم الترخيص" in c or ("الترخيص" in c and "فئة" not in c)]
                        date_col = [c for c in df.columns if "التاريخ" in c]
                        emp_col_sel = [c for c in df.columns if "اسم الموظف" in c or "الموظف" in c]
                        
                        if comp_col and lic_col and date_col:
                            c_c = comp_col[0]
                            l_c = lic_col[0]
                            d_c = date_col[0]
                            e_c = emp_col_sel[0] if emp_col_sel else None
                            
                            options_map = {}
                            for _, row in df.iterrows():
                                c_val = str(row.get(c_c, '')).strip()
                                l_val = str(row.get(l_c, '')).strip()
                                d_val = str(row.get(d_c, '')).strip()
                                e_val = str(row.get(e_c, '')).strip() if e_c else ''
                                label = f"{c_val} (رخصة {l_val}) - مراجع: {e_val} [{d_val}]"
                                k = f"{c_val}_{l_val}_{d_val}"
                                options_map[label] = k
                                
                            report_to_delete = st.selectbox("اختر التقرير للحذف:", list(options_map.keys()))
                            delete_password = st.text_input("كلمة المرور للحذف:", type="password")
                            
                            col_del1, col_del2 = st.columns(2)
                            with col_del1:
                                if st.button("تأكيد الحذف", type="primary", use_container_width=True):
                                    if delete_password == "8585":
                                        if report_to_delete and report_to_delete in options_map:
                                            key = options_map[report_to_delete]
                                            # حفظ في Supabase (دائم) + ملف محلي (احتياطي)
                                            if add_deleted_report is not None:
                                                add_deleted_report(key)
                                            if key not in deleted_list:
                                                deleted_list.append(key)
                                                try:
                                                    with open(deleted_file, 'w', encoding='utf-8') as f:
                                                        json.dump(deleted_list, f, ensure_ascii=False)
                                                except Exception:
                                                    pass
                                            st.success("تم حذف التقرير بنجاح!")
                                            time.sleep(1)
                                            st.rerun()
                                    else:
                                        st.error("كلمة المرور خاطئة!")
                            with col_del2:
                                if st.button("🔄 استعادة الكل", use_container_width=True):
                                    # مسح من Supabase + الملف المحلي
                                    if clear_deleted_reports is not None:
                                        clear_deleted_reports()
                                    try:
                                        with open(deleted_file, 'w', encoding='utf-8') as f:
                                            json.dump([], f)
                                    except Exception:
                                        pass
                                    st.success("تم استعادة جميع التقارير بنجاح!")
                                    time.sleep(1)
                                    st.rerun()
                    else:
                        st.info("لا توجد تقارير للحذف.")

            st.markdown("### تفاصيل تقارير الموظفين")
            st.dataframe(export_df, use_container_width=True)
        else:
            st.warning("لا توجد بيانات مسجلة حتى الآن في جوجل شيت.")
    except Exception as e:
        st.error(f"حدث خطأ أثناء قراءة البيانات من جوجل شيت: {e}")
