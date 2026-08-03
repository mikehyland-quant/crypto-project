# cd git-crypto/crypto-project/alt_approach
# python new_strat_prep.py


import numpy as np
import pandas as pd
from pathlib import Path


# ============================================================
# USER INPUTS
# ============================================================

etf_group = "hi yld"

moving_average_window = 20

start_date = pd.Timestamp("2025-01-02")
end_date = pd.Timestamp("2025-12-15")


# ============================================================
# CHOOSE ETFs
# ============================================================

etf_group_dict = {"hi yld" : ['SPHY', 'SCYB', 'HYLB', 'USHY', 'HYG', 'JNK'],
                  "muni"   : ['TFI', 'VTEB', 'MUB']}

sorted_etf_list = etf_group_dict[etf_group]


# ============================================================
# READ DATA
# ============================================================

input_file = 'prices.csv'
file_path = Path("stat_arb_analysis") / input_file
df = pd.read_csv(file_path)

df = df.dropna(axis=1, how="all")
df = df.dropna(how="all")

date_col = "date"

df = df[[date_col] + sorted_etf_list]

# Convert into pandas dates
df[date_col] = pd.to_datetime(
    df[date_col],
    errors="coerce",
)

# Keep only rows inside the requested date range
df = (
    df.loc[df[date_col].between(start_date, end_date)]
    .sort_values(date_col)
    .reset_index(drop=True)
)

for col in sorted_etf_list:
    df[col] = pd.to_numeric(
        df[col]
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip(),
        errors="coerce",
    )

df = (
    df.dropna(subset=sorted_etf_list)
    .sort_values(date_col)
    .reset_index(drop=True)
)

df.columns = [
    col if col == date_col else f"{col}_price"
    for col in df.columns
]


# ============================================================
# CALCULATIONS
# ============================================================

# daily price changes
for etf in sorted_etf_list:
    df[f"{etf}_price_chg"] = df[f"{etf}_price"].diff()


anchor_etf = sorted_etf_list[-1]

# daily price ratios
ratio_name_list = []
for etf in sorted_etf_list:
    ratio_name = f"{anchor_etf}/{etf}"
    ratio_name_list.append(ratio_name)
    df[ratio_name] = df[f"{anchor_etf}_price"] / df[f"{etf}_price"]

# price ratio moving averages
for ratio_name in ratio_name_list:
    df[f"{ratio_name}_moving_avg"] = (
        df[f"{ratio_name}"]
        .rolling(
            window=moving_average_window,
            min_periods=moving_average_window,
        )
        .mean()
    )

# Use only information available from the preceding row.
for ratio_name in ratio_name_list:
    df[f"{ratio_name}_prev_moving_avg"] = df[f"{ratio_name}_moving_avg"].shift(1)

# scaled prices
scaled_price_columns = []
for etf in sorted_etf_list:
    prior_price_ratio_moving_avg = (
        df[f"{anchor_etf}/{etf}_prev_moving_avg"]
    )

    scaled_price_name = f"{etf}_scaled_price"
    scaled_price_columns.append(scaled_price_name)
    df[scaled_price_name] = (
        df[f"{etf}_price"]
        * prior_price_ratio_moving_avg
    )

# relative prices
ln_name_list = []
for etf in sorted_etf_list:
    ln_name = f"ln({etf}*/{anchor_etf})"
    ln_name_list.append(ln_name)
    df[ln_name] = np.log(
        df[f"{etf}_scaled_price"]
        / df[f"{anchor_etf}_price"]
    )

# max, min and diff of ln's
df['max_ln'] = df[ln_name_list].max(axis=1)
df['min_ln'] = df[ln_name_list].min(axis=1) 
df['max_ln_minus_min_ln'] = df['max_ln'] - df['min_ln']

# etf with lowest ln
valid_rows = df[scaled_price_columns].notna().any(axis=1)

df["best_long"] = pd.NA
df.loc[valid_rows, "best_long"] = (
    df.loc[valid_rows, scaled_price_columns]
    .idxmin(axis=1)
)
df["best_long"] = df["best_long"].str.replace(
    "_scaled_price",
    "",
    regex=False,
)

# etf with highest ln
df["best_short"] = pd.NA
df.loc[valid_rows, "best_short"] = (
    df.loc[valid_rows, scaled_price_columns]
    .idxmax(axis=1)
)
df["best_short"] = df["best_short"].str.replace(
    "_scaled_price",
    "",
    regex=False,
)


# ============================================================
# EX-DIVIDEND / MONTH-END FLAGS
# ============================================================

df['new_date_col'] = df[date_col]
df.drop(columns=[date_col], inplace=True)
df.rename(
    columns={'new_date_col': 'date'},
    inplace=True,
)

# These ETFs go ex-dividend on the first trading day
# of every month.
#
# ex_div_date is True on the first available trading
# day of each new month.

current_month = df["date"].dt.to_period("M")
previous_month = df["date"].shift(1).dt.to_period("M")

df["ex_div_date"] = (
    current_month != previous_month
)

# Do not treat the first row of the entire dataset as an
# actual identified ex-dividend date.
df.loc[df.index[0], "ex_div_date"] = False


# ============================================================
# SAVE PREPARED FILE
# ============================================================

file_name = etf_group + "_prep.csv"
file_path = Path("stat_arb_analysis") / file_name
df.to_csv(file_path, index=False)
