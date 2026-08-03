# cd git-crypto/crypto-project/alt_approach
# python new_strat_prep.py


import numpy as np
import pandas as pd
from pathlib import Path


# ============================================================
# USER INPUTS
# ============================================================

input_file = "HI YLD.csv"

moving_average_window = 20

start_date = pd.Timestamp("2025-01-02")
end_date = pd.Timestamp("2025-12-15")


# ============================================================
# READ DATA
# ============================================================

df = pd.read_csv(input_file)

date_col = "DATE"

# Convert CSV values such as "45659" into numbers
df[date_col] = pd.to_numeric(
    df[date_col],
    errors="coerce",
)

# Convert Excel serial dates into pandas dates
df[date_col] = pd.to_datetime(
    df[date_col],
    unit="D",
    origin="1899-12-30",
    errors="coerce",
)

# Keep only rows inside the requested date range
df = (
    df.loc[df[date_col].between(start_date, end_date)]
    .sort_values(date_col)
    .reset_index(drop=True)
)

etf_list = [col for col in df.columns if col != date_col]

sorted_etf_list = sorted(
    etf_list,
    key=lambda col: df[col].iloc[0],
)

df = df[[date_col] + sorted_etf_list]

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
    .sort_values("DATE")
    .reset_index(drop=True)
)

df.columns = [
    col if col == "DATE" else f"{col}_price"
    for col in df.columns
]


# ============================================================
# CALCULATIONS
# ============================================================

for etf in sorted_etf_list:
    df[f"{etf}_price_chg"] = df[f"{etf}_price"].diff()


anchor_etf = sorted_etf_list[-1]

ratio_name_list = []
for etf in sorted_etf_list:
    ratio_name = f"{anchor_etf}/{etf}"
    ratio_name_list.append(ratio_name)
    df[ratio_name] = df[f"{anchor_etf}_price"] / df[f"{etf}_price"]

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

for etf in sorted_etf_list:
    prior_price_ratio_moving_avg = (
        df[f"{anchor_etf}/{etf}_prev_moving_avg"]
    )

    df[f"{etf}_scaled_price"] = (
        df[f"{etf}_price"]
        * prior_price_ratio_moving_avg
    )

ln_name_list = []
for etf in sorted_etf_list:
    ln_name = f"ln({etf}*/{anchor_etf})"
    ln_name_list.append(ln_name)
    df[ln_name] = np.log(
        df[f"{etf}_scaled_price"]
        / df[f"{anchor_etf}_price"]
    )

'''
df['max_ln'] = df[ln_name_list].max(axis=1)
df['min_ln'] = df[ln_name_list].min(axis=1) 
df['max_ln_minus_min_ln'] = df['max_ln'] - df['min_ln']
'''


# ============================================================
# EX-DIVIDEND / MONTH-END FLAGS
# ============================================================

# These ETFs go ex-dividend on the first trading day
# of every month.
#
# ex_div_date is True on the first available trading
# day of each new month.

current_month = df["DATE"].dt.to_period("M")
previous_month = df["DATE"].shift(1).dt.to_period("M")

df['date'] = df['DATE']
df.drop(columns=['DATE'], inplace=True)

df["ex_div_date"] = (
    current_month != previous_month
)

# Do not treat the first row of the entire dataset as an
# actual identified ex-dividend date.
df.loc[df.index[0], "ex_div_date"] = False


# ============================================================
# ADD COLUMNS FOR BACKTEST
# ============================================================

for name in sorted_etf_list:
    df[f"{name}_current_shs"] = 0

for name in sorted_etf_list:
    df[f"{name}_daily_pnl"] = 0

# flatten_at_close is True on the trading day immediately
# preceding an ex-dividend date.
#
# The strategy's target position must be zero at that close.
df["flatten_at_close"] = (
    df["ex_div_date"]
    .astype("boolean")
    .shift(-1, fill_value=False)
    .astype(bool)
)
    
df["open_trade"] = False
df['exit_trade'] = False
df['target_position'] = 0

for name in sorted_etf_list:
    df[f"{name}_target_position"] = 0

for name in sorted_etf_list:
    df[f"{name}_target_shs"] = 0

for name in sorted_etf_list:
    df[f"{name}_shs_to_buy"] = 0

for name in sorted_etf_list:
    df[f"{name}_shs_to_sell"] = 0

for name in sorted_etf_list:
    df[f"{name}_daily_commission"] = 0

for name in sorted_etf_list:
    df[f"{name}_gross_pnl"] = 0

'''

# ============================================================
# SAVE PREPARED FILE
# ============================================================

output_file = input_file.replace(".csv", " prep.csv")
df.to_csv(output_file, index=False)

