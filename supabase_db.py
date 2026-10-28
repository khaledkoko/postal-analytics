import psycopg2
import math
import pandas as pd

DB_HOST = "aws-0-eu-west-1.pooler.supabase.com"
DB_PORT = 5432
DB_USER = "postgres.bobgrwefgrfpkbnfahye"
DB_PASS = "Inter@mn2026"
DB_NAME = "postgres"

def get_db_connection():
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "postgres" in st.secrets:
            sec = st.secrets["postgres"]
            return psycopg2.connect(
                host=sec.get("host", DB_HOST),
                port=int(sec.get("port", DB_PORT)),
                user=sec.get("user", DB_USER),
                password=sec.get("password", DB_PASS),
                dbname=sec.get("dbname", DB_NAME),
                connect_timeout=10
            )
    except Exception:
        pass

    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        dbname=DB_NAME,
        connect_timeout=10
    )

def round_money(val, digits=2):
    try:
        return round(float(val or 0.0), digits)
    except Exception:
        return 0.0

def normalize_category(value):
    value = str(value or "").strip()
    if not value or value.lower() == "nan":
        return ""
    value = value.replace("داخلى", "داخلي")
    value = value.replace("داخلي+مجمع", "داخلي + مجمع")
    value = value.replace("داخلي +مجمع", "داخلي + مجمع")
    value = value.replace("داخلي+ مجمع", "داخلي + مجمع")
    value = value.replace("داخلى+مجمع", "داخلي + مجمع")
    value = value.replace("داخلى + مجمع", "داخلي + مجمع")
    value = " ".join(value.split())
    norm_val = value.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
    if "شامل" in norm_val or "اولي" in norm_val:
        return "البريد الشامل"
    allowed = ["داخلي", "مجمع", "داخلي + مجمع", "البريد الشامل"]
    return value if value in allowed else value

def safe_div(a, b):
    try:
        b_flt = float(b or 0.0)
        return (float(a or 0.0) / b_flt) if b_flt != 0 else 0.0
    except Exception:
        return 0.0

def calculate_financials(local_outbound_revenue=0.0, collected_mail_revenue=0.0,
                         international_outbound_revenue=0.0, intermediary_transactions_discount=0.0,
                         review_differences=0.0, inbound_commission=0.0):
    total_eligible = (
        float(local_outbound_revenue or 0.0)
        + float(collected_mail_revenue or 0.0)
        + float(international_outbound_revenue or 0.0)
    )
    comm_10 = total_eligible * 0.10
    commission_before_round = (
        comm_10
        + float(inbound_commission or 0.0)
        - float(intermediary_transactions_discount or 0.0)
        + float(review_differences or 0.0)
    )
    total_comm = math.ceil(commission_before_round - 1e-9)
    vat = round_money(total_comm * 0.14, 2)
    debt = math.ceil(total_comm + vat)

    return {
        "إجمالي الإيرادات الخاضعة": round_money(total_eligible, 2),
        "العمولة المستحقة 10%": round_money(comm_10, 2),
        "العمولة قبل التقريب": round_money(commission_before_round, 2),
        "إجمالي العمولة المستحقة": float(total_comm),
        "ضريبة القيمة المضافة": vat,
        "إجمالي المديونية": float(debt),
    }

def calculate_indicators(local_count, local_weight, local_rev,
                         bulk_count, bulk_weight, bulk_rev,
                         intl_count, intl_weight, intl_rev,
                         in_count, in_weight, in_comm):
    total_shipments = int(local_count or 0) + int(bulk_count or 0) + int(intl_count or 0) + int(in_count or 0)
    total_weights = float(local_weight or 0) + float(bulk_weight or 0) + float(intl_weight or 0) + float(in_weight or 0)
    work_volume = float(local_rev or 0) + float(bulk_rev or 0) + float(intl_rev or 0) + float(in_comm or 0)

    return {
        "متوسط السعر الداخلي": round(safe_div(local_rev, local_count), 4),
        "متوسط الوزن الداخلي": round(safe_div(local_weight, local_count), 4),
        "متوسط سعر المجمع": round(safe_div(bulk_rev, bulk_count), 4),
        "متوسط وزن المجمع": round(safe_div(bulk_weight, bulk_count), 4),
        "متوسط سعر الخارجي": round(safe_div(intl_rev, intl_count), 4),
        "متوسط وزن الخارجي": round(safe_div(intl_weight, intl_count), 4),
        "متوسط عمولة الوارد": round(safe_div(in_comm, in_count), 4),
        "متوسط وزن الوارد": round(safe_div(in_weight, in_count), 4),
        "إجمالي عدد الشحنات": total_shipments,
        "إجمالي الأوزان": round(total_weights, 2),
        "حجم العمل": round(work_volume, 2),
    }

def get_all_companies():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, license_number, company_name, license_category, uses_weight, notes, is_active FROM companies ORDER BY id")
    rows = cur.fetchall()
    conn.close()

    result = []
    for r in rows:
        lic = str(r[1]).strip()
        if lic.endswith(".0"):
            lic = lic[:-2]
        result.append({
            "id": r[0],
            "رقم الرخصة": lic,
            "license_number": lic,
            "اسم الشركة": str(r[2]).strip(),
            "company_name": str(r[2]).strip(),
            "الاسم التجاري": str(r[2]).strip(),
            "الفئة": normalize_category(r[3]),
            "فئة الترخيص": normalize_category(r[3]),
            "تستخدم الأوزان": bool(r[4]),
            "ملاحظات": str(r[5] or ""),
            "نشطة": bool(r[6])
        })
    return result

def get_all_quarterly_reports():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT r.id, r.company_id, c.company_name, c.license_number, c.license_category, c.uses_weight,
               r.year, r.quarter,
               r.local_outbound_count, r.local_outbound_weight, r.local_outbound_revenue,
               r.collected_mail_count, r.collected_mail_weight, r.collected_mail_revenue,
               r.international_outbound_count, r.international_outbound_weight, r.international_outbound_revenue,
               r.inbound_count, r.inbound_weight, r.inbound_commission,
               r.intermediary_transactions_discount, r.review_differences, r.notes,
               r.total_commission, r.total_indebtedness
        FROM quarterly_reports r
        JOIN companies c ON r.company_id = c.id
        ORDER BY r.year DESC, r.quarter DESC, r.id ASC
    """)
    rows = cur.fetchall()
    conn.close()

    result = []
    for r in rows:
        local_c, local_w, local_r = r[8], r[9], r[10]
        bulk_c, bulk_w, bulk_r = r[11], r[12], r[13]
        intl_c, intl_w, intl_r = r[14], r[15], r[16]
        in_c, in_w, in_comm = r[17], r[18], r[19]
        ded_amount, review_diff = r[20], r[21]
        notes = r[22] or ""
        stored_total_comm = r[23] if len(r) > 23 and r[23] is not None else None
        stored_total_indebt = r[24] if len(r) > 24 and r[24] is not None else None

        fin = calculate_financials(local_r, bulk_r, intl_r, ded_amount, review_diff, in_comm)
        if stored_total_comm is not None:
            fin["إجمالي العمولة المستحقة"] = float(stored_total_comm)
            fin["العمولة قبل التقريب"] = float(stored_total_comm)
        if stored_total_indebt is not None:
            fin["إجمالي المديونية"] = float(stored_total_indebt)
        ind = calculate_indicators(local_c, local_w, local_r, bulk_c, bulk_w, bulk_r, intl_c, intl_w, intl_r, in_c, in_w, in_comm)

        lic = str(r[3]).strip()
        if lic.endswith(".0"):
            lic = lic[:-2]
        item = {
            "id": r[0],
            "company_id": r[1],
            "الشركة": r[2],
            "اسم الشركة": r[2],
            "company_name": r[2],
            "رقم الرخصة": lic,
            "license_number": lic,
            "الفئة": normalize_category(r[4]),
            "فئة الترخيص": normalize_category(r[4]),
            "تستخدم الأوزان": bool(r[5]),
            "السنة": r[6],
            "year": r[6],
            "الربع": r[7],
            "quarter": r[7],

            "عدد الصادر الداخلي": local_c,
            "وزن الصادر الداخلي": round_money(local_w),
            "إيراد الصادر الداخلي": round_money(local_r),

            "عدد البريد المجمع": bulk_c,
            "وزن البريد المجمع": round_money(bulk_w),
            "إيراد البريد المجمع": round_money(bulk_r),

            "عدد الصادر الخارجي": intl_c,
            "وزن الصادر الخارجي": round_money(intl_w),
            "إيراد الصادر الخارجي": round_money(intl_r),

            "عدد الوارد": in_c,
            "وزن الوارد": round_money(in_w),
            "عمولة الوارد": round_money(in_comm),

            "خصم المعاملات الوسيطة": round_money(ded_amount),
            "فروق المراجعة": round_money(review_diff),
            "ملاحظات": notes,
        }
        item.update(fin)
        item.update(ind)
        result.append(item)

    return result

import re

def strip_tashkeel(text):
    return re.sub(r'[\u064B-\u065F\u0670]', '', str(text))

def migrate_smart_reports(df, target_year, target_quarter, deleted_keys=None):
    if df is None or df.empty:
        return False, "لا توجد بيانات في ملف سمارت ريبورت للترحيل."

    deleted_keys = set(deleted_keys or [])
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        def get_series(col_names):
            norm_col_names = [strip_tashkeel(n).strip() for n in col_names]
            for c in df.columns:
                c_norm = strip_tashkeel(c).strip()
                for n in norm_col_names:
                    if n in c_norm:
                        return df[c]
            return pd.Series(0, index=df.index)

        def clean_num(series):
            return pd.to_numeric(
                series.astype(str).str.replace('٫', '.').str.replace('٬', '').str.replace(',', '').str.strip(),
                errors='coerce'
            ).fillna(0)

        # 1. Register or update companies
        lic_series = get_series(['رقم الترخيص', 'الترخيص'])
        name_series = get_series(['اسم الشركة', 'الشركة'])
        cat_series = get_series(['فئة الترخيص', 'الفئة'])

        companies_map = {}
        for idx in range(len(df)):
            lic = str(lic_series.iloc[idx]).strip()
            if lic.endswith(".0"):
                lic = lic[:-2]
            name = str(name_series.iloc[idx]).strip()
            cat = normalize_category(cat_series.iloc[idx])
            if not lic or lic == "nan" or lic == "0" or not name or name == "nan":
                continue
            if lic == "999" or "تجربة" in name or "فحص" in name:
                continue

            # Check if company exists by license
            cur.execute("SELECT id FROM companies WHERE license_number = %s", (lic,))
            row = cur.fetchone()
            if row:
                comp_id = row[0]
                cur.execute("UPDATE companies SET company_name = %s, license_category = %s WHERE id = %s", (name, cat or "عام", comp_id))
            else:
                cur.execute("INSERT INTO companies (license_number, company_name, license_category, uses_weight, is_active) VALUES (%s, %s, %s, TRUE, TRUE) RETURNING id", (lic, name, cat or "عام"))
                comp_id = cur.fetchone()[0]
            companies_map[lic] = comp_id

        # 2. Delete existing reports for that year and quarter to avoid duplicates
        cur.execute("DELETE FROM quarterly_reports WHERE year = %s AND quarter = %s", (int(target_year), int(target_quarter)))

        # 3. Insert fresh reports from df
        in_count_s = clean_num(get_series(['عدد الصادر المحلي', 'عدد الصادر الداخلي']))
        in_rev_s = clean_num(get_series(['إيراد الصادر المحلي', 'إيراد الصادر الداخلي']))
        bulk_count_s = clean_num(get_series(['عدد البريد المجمع', 'عدد المجمع']))
        bulk_rev_s = clean_num(get_series(['إيراد البريد المجمع', 'إيراد المجمع']))
        out_count_s = clean_num(get_series(['عدد الصادر الدولي', 'عدد الصادر الخارجي']))
        out_rev_s = clean_num(get_series(['إيراد الصادر الدولي', 'إيراد الصادر الخارجي']))
        inbound_comm_s = clean_num(get_series(['عمولة الوارد الخارجي', 'عمولة الوارد']))
        ded_s = clean_num(get_series(['خصم', 'الوسيطة']))
        diff_s = clean_num(get_series(['فروق المراجعة', 'فروق']))
        vat_s = clean_num(get_series(['القيمة المضافة', 'ضريبة']))
        comm_s = clean_num(get_series(['إجمالي العمولة المستحقة', 'العمولة المستحقة']))
        debt_s = clean_num(get_series(['إجمالي المديونية المستحقة', 'إجمالي المديونية']))
        notes_s = get_series(['الملاحظات', 'ملاحظات']).astype(str).replace('nan', '')
        date_s = get_series(['التاريخ', 'تاريخ']).astype(str)

        inserted_count = 0
        for idx in range(len(df)):
            lic = str(lic_series.iloc[idx]).strip()
            if lic.endswith(".0"):
                lic = lic[:-2]
            name = str(name_series.iloc[idx]).strip()
            date_val = str(date_s.iloc[idx]).strip() if not date_s.empty else ""

            # Check if deleted by supervisor (handling both lic with and without .0)
            k1 = f"{name}_{lic}_{date_val}"
            k2 = f"{name}_{lic}.0_{date_val}"
            if k1 in deleted_keys or k2 in deleted_keys:
                continue
            if lic == "999" or "تجربة" in name or "فحص" in name:
                continue

            comp_id = companies_map.get(lic)
            if not comp_id:
                continue

            local_c = int(in_count_s.iloc[idx])
            local_r = float(in_rev_s.iloc[idx])
            bulk_c = int(bulk_count_s.iloc[idx])
            bulk_r = float(bulk_rev_s.iloc[idx])
            intl_c = int(out_count_s.iloc[idx])
            intl_r = float(out_rev_s.iloc[idx])
            in_c = 0
            in_comm = float(inbound_comm_s.iloc[idx])
            ded_amt = float(ded_s.iloc[idx])
            diff_amt = float(diff_s.iloc[idx])
            vat_amt = float(vat_s.iloc[idx])
            comm_amt = float(comm_s.iloc[idx])
            debt_amt = float(debt_s.iloc[idx])
            note_val = str(notes_s.iloc[idx]).strip()

            cur.execute("""
                INSERT INTO quarterly_reports (
                    company_id, year, quarter,
                    local_outbound_count, local_outbound_weight, local_outbound_revenue,
                    collected_mail_count, collected_mail_weight, collected_mail_revenue,
                    international_outbound_count, international_outbound_weight, international_outbound_revenue,
                    inbound_count, inbound_weight, inbound_commission,
                    intermediary_transactions_discount, review_differences, vat_amount, notes,
                    total_commission, total_indebtedness
                ) VALUES (
                    %s, %s, %s,
                    %s, 0.0, %s,
                    %s, 0.0, %s,
                    %s, 0.0, %s,
                    %s, 0.0, %s,
                    %s, %s, %s, %s,
                    %s, %s
                )
            """, (
                comp_id, int(target_year), int(target_quarter),
                local_c, local_r,
                bulk_c, bulk_r,
                intl_c, intl_r,
                in_c, in_comm,
                ded_amt, diff_amt, vat_amt, note_val,
                comm_amt, debt_amt
            ))
            inserted_count += 1

        conn.commit()
        conn.close()
        return True, f"تم ترحيل وحفظ {inserted_count} تقرير بنجاح إلى قاعدة البيانات السحابية Supabase!"
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, f"حدث خطأ أثناء الترحيل إلى السيرفر السحابي: {e}"


# ─────────────────────────────────────────────────────────────
# إدارة التقارير المحذوفة في Supabase (بديل عن deleted_reports.json)
# ─────────────────────────────────────────────────────────────

def _ensure_deleted_reports_table(conn):
    """ينشئ جدول deleted_reports في Supabase لو مش موجود."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS deleted_reports (
                id SERIAL PRIMARY KEY,
                report_key TEXT UNIQUE NOT NULL,
                deleted_at TIMESTAMP DEFAULT NOW()
            )
        """)
    conn.commit()


def get_deleted_reports() -> list:
    """يجيب قائمة مفاتيح التقارير المحذوفة من Supabase."""
    try:
        conn = get_db_connection()
        _ensure_deleted_reports_table(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT report_key FROM deleted_reports")
            rows = cur.fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception:
        return []


def add_deleted_report(key: str) -> bool:
    """يضيف مفتاح تقرير للقائمة المحذوفة في Supabase."""
    try:
        conn = get_db_connection()
        _ensure_deleted_reports_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO deleted_reports (report_key) VALUES (%s) ON CONFLICT (report_key) DO NOTHING",
                (key,)
            )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def clear_deleted_reports() -> bool:
    """يمسح كل التقارير المحذوفة من Supabase (استعادة الكل)."""
    try:
        conn = get_db_connection()
        _ensure_deleted_reports_table(conn)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM deleted_reports")
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False
