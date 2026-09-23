"""ML features: auto-categorization, spend forecasting, anomaly detection."""
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor, IsolationForest

# Generic keyword -> category fallback, used to bootstrap the classifier
# when a brand-new user has too little labeled history of their own.
SEED_TRAINING = [
    ("uber ride cab taxi ola fuel petrol diesel bus metro parking toll", "Transport"),
    ("swiggy zomato restaurant cafe coffee starbucks dinner lunch pizza food", "Food & Dining"),
    ("supermarket grocery bigbasket walmart vegetables milk kirana mart", "Groceries"),
    ("amazon flipkart myntra shopping mall clothes shoes electronics", "Shopping"),
    ("electricity water bill internet wifi recharge broadband gas utility", "Bills & Utilities"),
    ("rent landlord lease apartment housing", "Rent"),
    ("netflix spotify movie cinema concert game entertainment subscription", "Entertainment"),
    ("hospital doctor pharmacy medicine clinic health insurance gym", "Health"),
    ("course tuition udemy book school college university education", "Education"),
    ("salary payroll paycheck wages", "Salary"),
    ("freelance client invoice project payment", "Freelance"),
    ("dividend stock mutual fund interest investment returns", "Investment"),
]


def _seed_df():
    return pd.DataFrame(SEED_TRAINING, columns=["description", "category"])


def train_category_classifier(df: pd.DataFrame):
    """Trains a TF-IDF + Naive Bayes text classifier on description->category.
    Blends the user's own history with a generic seed set so it works
    even for a brand-new account, and improves as the user adds data."""
    seed = _seed_df()
    if df is not None and not df.empty:
        user_data = df[["description", "category"]].dropna()
        user_data = user_data[user_data["description"].str.strip() != ""]
        train_df = pd.concat([seed, user_data], ignore_index=True)
    else:
        train_df = seed

    model = Pipeline([
        ("tfidf", TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=1)),
        ("clf", MultinomialNB()),
    ])
    model.fit(train_df["description"], train_df["category"])
    return model


def predict_category(model, description: str) -> str:
    if not description or not description.strip():
        return "Other"
    return model.predict([description])[0]


def predict_category_confidence(model, description: str):
    proba = model.predict_proba([description])[0]
    classes = model.classes_
    idx = np.argmax(proba)
    return classes[idx], float(proba[idx])


def forecast_expenses(df: pd.DataFrame, months_ahead: int = 3):
    """Aggregates monthly expenses and forecasts the next N months using
    a RandomForestRegressor over time + seasonality features."""
    exp = df[df["type"] == "expense"].copy()
    if exp.empty or exp["date"].dt.to_period("M").nunique() < 3:
        return None, "Need at least 3 months of expense history to forecast."

    exp["month"] = exp["date"].dt.to_period("M")
    monthly = exp.groupby("month")["amount"].sum().reset_index()
    monthly["month_idx"] = range(len(monthly))
    monthly["month_num"] = monthly["month"].apply(lambda p: p.month)
    monthly["sin_m"] = np.sin(2 * np.pi * monthly["month_num"] / 12)
    monthly["cos_m"] = np.cos(2 * np.pi * monthly["month_num"] / 12)

    X = monthly[["month_idx", "sin_m", "cos_m"]].values
    y = monthly["amount"].values

    n_estimators = 200 if len(monthly) >= 6 else 50
    model = RandomForestRegressor(n_estimators=n_estimators, random_state=42, max_depth=4)
    model.fit(X, y)

    last_idx = monthly["month_idx"].max()
    last_period = monthly["month"].max()
    future_rows, future_periods = [], []
    for i in range(1, months_ahead + 1):
        period = last_period + i
        future_periods.append(str(period))
        m = period.month
        future_rows.append([last_idx + i, np.sin(2 * np.pi * m / 12), np.cos(2 * np.pi * m / 12)])

    preds = model.predict(np.array(future_rows))
    result = pd.DataFrame({"month": future_periods, "predicted_expense": np.round(preds, 2)})
    history = monthly[["month", "amount"]].rename(columns={"amount": "actual_expense"})
    history["month"] = history["month"].astype(str)
    return {"history": history, "forecast": result}, None


def detect_anomalies(df: pd.DataFrame):
    """Flags unusual transactions using IsolationForest over amount + day-of-month
    + category-relative z-score, so it catches both outlier amounts and
    spending on categories that spike unexpectedly."""
    work = df.copy()
    if len(work) < 8:
        return df.assign(is_anomaly=False)

    work["day"] = work["date"].dt.day
    work["cat_mean"] = work.groupby("category")["amount"].transform("mean")
    work["cat_std"] = work.groupby("category")["amount"].transform("std").fillna(1.0).replace(0, 1.0)
    work["z"] = (work["amount"] - work["cat_mean"]) / work["cat_std"]

    features = work[["amount", "day", "z"]].fillna(0)
    contamination = min(0.15, max(0.03, 5 / len(work)))
    iso = IsolationForest(contamination=contamination, random_state=42)
    work["is_anomaly"] = iso.fit_predict(features) == -1
    return work.drop(columns=["day", "cat_mean", "cat_std", "z"])
