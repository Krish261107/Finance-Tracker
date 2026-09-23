"""Generates realistic synthetic transaction history for demos/testing."""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

EXPENSE_TEMPLATES = [
    ("Food & Dining", ["Zomato order", "Swiggy dinner", "Cafe coffee", "Restaurant bill"], (150, 1200)),
    ("Groceries", ["BigBasket order", "Local supermarket", "Kirana store"], (300, 3000)),
    ("Transport", ["Uber ride", "Ola cab", "Fuel - petrol pump", "Metro card recharge"], (50, 1500)),
    ("Shopping", ["Amazon purchase", "Myntra order", "Flipkart electronics"], (500, 6000)),
    ("Bills & Utilities", ["Electricity bill", "Internet bill", "Mobile recharge"], (300, 2500)),
    ("Rent", ["Monthly rent payment"], (8000, 18000)),
    ("Entertainment", ["Netflix subscription", "Movie tickets", "Spotify premium"], (150, 1000)),
    ("Health", ["Pharmacy purchase", "Doctor consultation", "Gym membership"], (200, 3000)),
    ("Education", ["Udemy course", "Book purchase"], (300, 2000)),
]

INCOME_TEMPLATES = [
    ("Salary", ["Monthly salary credit"], (35000, 65000)),
    ("Freelance", ["Freelance project payment"], (3000, 15000)),
    ("Investment", ["Mutual fund dividend", "Stock dividend"], (500, 5000)),
]


def generate_sample_transactions(months: int = 8, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    today = datetime.now()
    start = today - timedelta(days=30 * months)

    for m in range(months):
        month_start = start + timedelta(days=30 * m)
        # Salary always lands early in the month
        cat, descs, (lo, hi) = INCOME_TEMPLATES[0]
        rows.append({
            "date": (month_start + timedelta(days=2)).strftime("%Y-%m-%d"),
            "amount": round(rng.uniform(lo, hi), 2), "type": "income", "category": cat,
            "description": descs[0],
        })
        for cat, descs, (lo, hi) in INCOME_TEMPLATES[1:]:
            if rng.random() < 0.5:
                rows.append({
                    "date": (month_start + timedelta(days=int(rng.integers(0, 28)))).strftime("%Y-%m-%d"),
                    "amount": round(rng.uniform(lo, hi), 2), "type": "income", "category": cat,
                    "description": rng.choice(descs),
                })
        for cat, descs, (lo, hi) in EXPENSE_TEMPLATES:
            n_tx = int(rng.integers(1, 6)) if cat not in ("Rent",) else 1
            for _ in range(n_tx):
                rows.append({
                    "date": (month_start + timedelta(days=int(rng.integers(0, 28)))).strftime("%Y-%m-%d"),
                    "amount": round(rng.uniform(lo, hi), 2), "type": "expense", "category": cat,
                    "description": rng.choice(descs),
                })
        # sprinkle a rare anomalous large expense for the anomaly detector to catch
        if rng.random() < 0.3:
            rows.append({
                "date": (month_start + timedelta(days=int(rng.integers(0, 28)))).strftime("%Y-%m-%d"),
                "amount": round(rng.uniform(9000, 20000), 2), "type": "expense",
                "category": "Shopping", "description": "Laptop purchase",
            })

    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    return df
