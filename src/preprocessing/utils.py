"""
utils.py
--------
General-purpose helper functions for data cleaning and transformation.
"""

import pandas as pd
import re


# ============================================================
# 🧩 Convert Nepali digits to English
# ============================================================
def nepali_to_english(num_str):
    """Convert Nepali digits (०१२३४५६७८९) to English (0123456789)."""
    if pd.isna(num_str):
        return num_str
    mapping = str.maketrans("०१२३४५६७८९", "0123456789")
    return str(num_str).translate(mapping)


# ============================================================
# 🧩 Clean numeric and currency strings
# ============================================================
def clean_number(value):
    """Clean numeric or currency-like strings and convert to float."""
    if pd.isna(value):
        return None
    value = str(value).replace("रू", "").replace(",", "").strip()
    value = nepali_to_english(value)
    try:
        return float(value)
    except:
        return None


# ============================================================
# 🧩 Clean commodity names
# ============================================================
def clean_commodity(name):
    """Normalize Nepali commodity names into standard English categories."""
    name = re.sub(r"\(.*?\)", "", str(name)).strip()
    mapping = {
        "गोलभेडा ठूलो": "Tomato_Big",
        "गोलभेडा सानो": "Tomato_Small",
        "गोलभेडा": "Tomato"
    }
    for np_name, en_name in mapping.items():
        if np_name in name:
            return en_name
    return name
