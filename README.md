# FinSight — AI Personal Finance Dashboard

Stack: Python · SQLite · scikit-learn · Streamlit (Plotly, custom dark CSS)

## Run
```
pip install -r requirements.txt
streamlit run app.py
```

## Features
- **Auth**: signup/login (PBKDF2-SHA256 salted hashes), full account deletion (cascades to all transactions/categories).
- **CRUD**: add/edit/delete transactions and categories; filter/search.
- **Flexible import**: CSV/Excel with auto-detected columns (date, amount, or separate debit/credit, description, category) — works with arbitrary bank-export layouts.
- **ML**:
  - Category auto-classifier (TF-IDF + Naive Bayes, seeded + learns from your history).
  - Expense forecasting next 3 months (RandomForestRegressor with seasonal features).
  - Anomaly detection on transactions (IsolationForest).
- **Reports**: CSV export + generated PDF summary report.
- **Sample data**: one-click realistic synthetic transaction history.
- **UI**: dark, animated, gradient-accented, fully interactive Plotly charts.

## Files
- `app.py` — Streamlit UI & routing
- `db.py` — SQLite schema + all data access
- `ml_models.py` — the three ML features
- `data_io.py` — smart import + CSV/PDF export
- `sample_data.py` — synthetic demo data generator
- `style.py` — dark theme CSS + Plotly template
