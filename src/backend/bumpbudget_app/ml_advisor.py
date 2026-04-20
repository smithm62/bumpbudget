# ml_advisor.py
# Decile-based pregnancy cost advisor
# Data source: CSO Ireland SIA205 — Average equivalised disposable income by decile, 2024
# https://data.cso.ie/table/SIA205
#
# To update: replace data/SIA205.csv with the latest CSO export — no code changes needed.
# Place this file in your bumpbudget_app/ folder.

import os
import csv

# ── Path to CSV ──
# Looks for data/SIA205.csv relative to the Django project root (manage.py location)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE_DIR, "data", "SIA205.csv")

# ── Fallback hardcoded values (used if CSV not found) ──
# Source: SIA205_20260226T150209.csv, 2024
_FALLBACK_AVERAGES = {
    1: 14183, 2: 19070, 3: 22231, 4: 25338, 5: 28377,
    6: 31833, 7: 35464, 8: 40169, 9: 46896, 10: 78098,
}
_FALLBACK_BOUNDARIES = {
    1: 0, 2: 17436, 3: 20650, 4: 23650, 5: 27001,
    6: 29996, 7: 33885, 8: 37482, 9: 43135, 10: 52112,
}

_DECILE_MAP = {
    "1st decile": 1, "2nd decile": 2, "3rd decile": 3,
    "4th decile": 4, "5th decile": 5, "6th decile": 6,
    "7th decile": 7, "8th decile": 8, "9th decile": 9,
    "10th decile": 10,
}


def _load_from_csv():
    """
    Parse SIA205.csv and extract:
      - Average equivalised nominal disposable income (annual) per decile
      - Lower decile boundary per decile
    Returns (averages_dict, boundaries_dict) or None if file not found/invalid.
    """
    if not os.path.exists(CSV_PATH):
        return None, None

    averages   = {}
    boundaries = {1: 0}  # decile 1 has no lower boundary

    try:
        with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                label  = row.get("Statistic Label", "").strip()
                decile = _DECILE_MAP.get(row.get("Deciles", "").strip())
                value  = row.get("VALUE", "").strip()

                if not decile or not value:
                    continue

                try:
                    value = float(value)
                except ValueError:
                    continue

                if label == "Average equivalised nominal disposable income":
                    averages[decile] = value

                elif label == "Lower decile boundary - equivalised nominal disposable income":
                    if decile > 1:
                        boundaries[decile] = value

    except Exception:
        return None, None

    if len(averages) == 10:
        return averages, boundaries
    return None, None


# ── Load data ──
_csv_averages, _csv_boundaries = _load_from_csv()

DECILE_AVERAGES    = _csv_averages   or _FALLBACK_AVERAGES
DECILE_BOUNDARIES  = _csv_boundaries or _FALLBACK_BOUNDARIES
DATA_SOURCE        = "CSV" if _csv_averages else "fallback constants"

DECILE_MONTHLY_INCOME = {
    d: round(annual / 12, 2)
    for d, annual in DECILE_AVERAGES.items()
}

# ── Pregnancy cost scenarios ──
COST_SCENARIOS = {
    "Essential": {
        "total": 3000,
        "label": "Essential",
        "description": "Covers the basics - second-hand where possible, minimal spend.",
        "colour": "green",
        "items": {
            "Baby Equipment": 1200,
            "Clothing": 300,
            "Supplements": 200,
            "Classes": 100,
            "Travel & Misc": 400,
            "Medical": 800,
        },
    },
    "Standard": {
        "total": 4500,
        "label": "Standard",
        "description": "A comfortable, well-prepared approach for most families.",
        "colour": "sage",
        "items": {
            "Baby Equipment": 2000,
            "Clothing": 500,
            "Supplements": 200,
            "Classes": 200,
            "Travel & Misc": 600,
            "Medical": 1000,
        },
    },
    "Premium": {
        "total": 6500,
        "label": "Premium",
        "description": "Higher-end choices, private care, and all-new equipment.",
        "colour": "amber",
        "items": {
            "Baby Equipment": 3000,
            "Clothing": 800,
            "Supplements": 300,
            "Classes": 400,
            "Travel & Misc": 1000,
            "Medical": 1000,
        },
    },
}

SAVINGS_RATE = 0.15


def get_decile(monthly_income: float) -> int:
    """
    Assign a user to an income decile (1–10) using CSO lower boundary thresholds.
    Annual income is compared against the lower boundary of each decile.
    """
    annual = monthly_income * 12
    assigned = 1
    for decile, boundary in sorted(DECILE_BOUNDARIES.items()):
        if annual >= boundary:
            assigned = decile
    return assigned


def get_decile_label(decile: int) -> str:
    suffixes = {1: "st", 2: "nd", 3: "rd"}
    suffix = suffixes.get(decile, "th")
    return f"{decile}{suffix} decile"


def get_recommendation(monthly_income: float, months_remaining: int = 8) -> dict:
    """
    Given a user's monthly income and months until birth,
    return their decile, recommended cost scenario, and full affordability breakdown.
    """
    months_remaining = max(months_remaining, 1)
    decile = get_decile(monthly_income)
    savings_capacity = monthly_income * SAVINGS_RATE
    decile_avg_monthly = DECILE_MONTHLY_INCOME.get(decile, monthly_income)

    all_scenarios = []

    for key, scenario in COST_SCENARIOS.items():
        monthly_required = scenario["total"] / months_remaining
        feasible = savings_capacity >= monthly_required
        shortfall = max(monthly_required - savings_capacity, 0)
        pct_covered = min(round(savings_capacity / monthly_required * 100), 100)

        entry = {
            "key": key,
            "label": scenario["label"],
            "description": scenario["description"],
            "colour": scenario["colour"],
            "total": scenario["total"],
            "items": scenario["items"],
            "monthly_required": round(monthly_required, 2),
            "feasible": feasible,
            "shortfall": round(shortfall, 2),
            "pct_covered": pct_covered,
        }
        all_scenarios.append(entry)

    # Recommend the HIGHEST affordable scenario, not the lowest
    # e.g. high earner gets Premium, low earner gets Essential
    recommended = all_scenarios[0]  # default to Essential
    for entry in all_scenarios:
        if entry["feasible"]:
            recommended = entry  # keep upgrading as long as feasible

    return {
        "decile": decile,
        "decile_label": get_decile_label(decile),
        "decile_avg_monthly": decile_avg_monthly,
        "monthly_income": round(monthly_income, 2),
        "savings_capacity": round(savings_capacity, 2),
        "months_remaining": months_remaining,
        "recommended": recommended,
        "all_scenarios": all_scenarios,
        "can_afford_recommended": recommended["feasible"],
        "data_source": DATA_SOURCE,
    }