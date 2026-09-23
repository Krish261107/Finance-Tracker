"""Flexible import of arbitrary CSV/Excel bank-export formats, and export/report generation."""
import io
import pandas as pd
import numpy as np
from datetime import datetime

# Synonym maps used to auto-detect columns regardless of the source format.
COLUMN_SYNONYMS = {
    "date": ["date", "transaction date", "txn date", "posting date", "value date", "trans date"],
    "amount": ["amount", "value", "amt", "transaction amount", "total"],
    "debit": ["debit", "withdrawal", "debit amount", "money out", "dr"],
    "credit": ["credit", "deposit", "credit amount", "money in", "cr"],
    "description": ["description", "narration", "details", "particulars", "remarks", "memo", "note", "notes"],
    "category": ["category", "type", "tag", "label"],
}


def _find_col(columns, keys):
    lower = {c.lower().strip(): c for c in columns}
    for key in keys:
        if key in lower:
            return lower[key]
    # fuzzy contains-match fallback
    for c in columns:
        cl = c.lower().strip()
        if any(k in cl for k in keys):
            return c
    return None


def smart_import(uploaded_file) -> tuple[pd.DataFrame, str]:
    """Reads a CSV or Excel file with an unknown/arbitrary column layout and
    normalizes it to columns: date, amount, type, category, description.
    Handles both a single signed 'amount' column and separate debit/credit columns."""
    name = uploaded_file.name.lower()
    try:
        if name.endswith(".csv"):
            raw = pd.read_csv(uploaded_file)
        else:
            raw = pd.read_excel(uploaded_file)
    except Exception as e:
        return None, f"Could not read file: {e}"

    if raw.empty:
        return None, "File is empty."

    cols = list(raw.columns)
    date_col = _find_col(cols, COLUMN_SYNONYMS["date"])
    amount_col = _find_col(cols, COLUMN_SYNONYMS["amount"])
    debit_col = _find_col(cols, COLUMN_SYNONYMS["debit"])
    credit_col = _find_col(cols, COLUMN_SYNONYMS["credit"])
    desc_col = _find_col(cols, COLUMN_SYNONYMS["description"])
    cat_col = _find_col(cols, COLUMN_SYNONYMS["category"])

    if not date_col:
        return None, "Couldn't detect a date column. Rename it to 'Date' and retry."
    if not amount_col and not (debit_col or credit_col):
        return None, "Couldn't detect an amount/debit/credit column."

    out = pd.DataFrame()
    # DD/MM/YYYY is the more common bank-export convention outside the US; try it first.
    out["date"] = pd.to_datetime(raw[date_col], errors="coerce", dayfirst=True)
    if out["date"].isna().mean() > 0.5:
        out["date"] = pd.to_datetime(raw[date_col], errors="coerce", dayfirst=False)

    if amount_col:
        amt = pd.to_numeric(raw[amount_col].astype(str).str.replace(r"[^\d\.\-]", "", regex=True), errors="coerce")
        out["amount"] = amt.abs()
        out["type"] = np.where(amt >= 0, "income", "expense")
    else:
        debit = pd.to_numeric(raw[debit_col], errors="coerce").fillna(0) if debit_col else 0
        credit = pd.to_numeric(raw[credit_col], errors="coerce").fillna(0) if credit_col else 0
        out["amount"] = np.where(credit > 0, credit, debit)
        out["type"] = np.where(credit > 0, "income", "expense")

    out["description"] = raw[desc_col].astype(str) if desc_col else ""
    out["category"] = raw[cat_col].astype(str) if cat_col else "Other"
    out["category"] = out["category"].replace(["nan", "None", ""], "Other")

    out = out.dropna(subset=["date", "amount"])
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")

    if out.empty:
        return None, "No valid rows found after parsing."
    return out, f"Imported {len(out)} rows ({(out['type']=='expense').sum()} expense / {(out['type']=='income').sum()} income)."


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def generate_pdf_report(df: pd.DataFrame, username: str) -> bytes:
    """Builds a downloadable PDF summary report using fpdf2."""
    from fpdf import FPDF

    total_income = df.loc[df["type"] == "income", "amount"].sum()
    total_expense = df.loc[df["type"] == "expense", "amount"].sum()
    net = total_income - total_expense
    by_cat = (
        df[df["type"] == "expense"].groupby("category")["amount"].sum().sort_values(ascending=False)
    )

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "Personal Finance Report", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"User: {username}", ln=True)
    pdf.cell(0, 8, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "Summary", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Total Income:   {total_income:,.2f}", ln=True)
    pdf.cell(0, 8, f"Total Expense:  {total_expense:,.2f}", ln=True)
    pdf.cell(0, 8, f"Net Savings:    {net:,.2f}", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "Expense by Category", ln=True)
    pdf.set_font("Helvetica", "", 11)
    for cat, amt in by_cat.items():
        pdf.cell(0, 7, f"{cat}: {amt:,.2f}", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "Recent Transactions", ln=True)
    pdf.set_font("Helvetica", "", 9)
    recent = df.sort_values("date", ascending=False).head(25)
    for _, r in recent.iterrows():
        d = r["date"].strftime("%Y-%m-%d") if hasattr(r["date"], "strftime") else str(r["date"])
        line = f"{d}  {r['type']:<8}  {r['category']:<18}  {r['amount']:>10,.2f}  {str(r['description'])[:30]}"
        pdf.cell(0, 6, line, ln=True)

    return bytes(pdf.output())
