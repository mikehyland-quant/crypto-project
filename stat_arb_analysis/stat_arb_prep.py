# cd git-crypto/crypto-project/alt_approach
# python new_strat_prep.py


import numpy as np
import pandas as pd
from pathlib import Path 


# ============================================================
# USER INPUTS
# ============================================================

etf_group = "hi_yld"

moving_average_window = 20

start_date = pd.Timestamp("2025-01-02")
end_date = pd.Timestamp("2025-12-15")

comm_per_share = 0.005


# ============================================================
# CHOOSE ETFs
# ============================================================

etf_group_dict = {"hi_yld" : ['SPHY', 'SCYB', 'HYLB', 'USHY', 'HYG', 'JNK'],
                  "muni"   : ['TFI', 'VTEB', 'MUB']}

sorted_etf_list = etf_group_dict[etf_group]
anchor_etf = sorted_etf_list[-1]


# ============================================================
# READ DATA
# ============================================================

input_file = 'prices.csv'
file_path = Path("stat_arb_analysis") / input_file
df = pd.read_csv(file_path)


# ============================================================
# PREP DF AND DATE COLUMN
# ============================================================

df = df.dropna(axis=1, how="all")
df = df.dropna(how="all")

date_col = "date"

df = df[[date_col] + sorted_etf_list]

# Convert into pandas dates
df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

# Keep only rows inside the requested date range
df = df.loc[df[date_col].between(start_date, end_date)].sort_values(date_col).reset_index(drop=True)


for etf in sorted_etf_list:
    df[etf] = pd.to_numeric(
        df[etf]
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip(),
        errors="coerce",
    )

df = df.sort_values(date_col).reset_index(drop=True)

df.columns = [col if col == date_col else f"{col}_price" for col in df.columns]


# ============================================================
# CALC DAILY PRICE CHANGES
# ============================================================

for etf in sorted_etf_list:
    df[f"{etf}_price_chg"] = df[f"{etf}_price"].diff()


# ============================================================
# CALC DAILY PRICE RATIOS TO ANCHOR ETF
# ============================================================

ratio_name_list = []
for etf in sorted_etf_list:
    new_col_name = f"{anchor_etf}/{etf}"
    ratio_name_list.append(new_col_name)
    df[new_col_name] = df[f"{anchor_etf}_price"] / df[f"{etf}_price"]


# ============================================================
# CALC PRICE RATIO MOVING AVERAGES
# ============================================================

# price ratio moving averages
for ratio_name in ratio_name_list:
    df[f"{ratio_name}_moving_avg"] = df[f"{ratio_name}"].rolling(window=moving_average_window, 
                                                                 min_periods=moving_average_window).mean()


# ============================================================
# COPY MOVING AVERAGES FOR USE ON NEXT DAY
# ============================================================
    
for ratio_name in ratio_name_list:
    df[f"{ratio_name}_prev_moving_avg"] = df[f"{ratio_name}_moving_avg"].shift(1)


# ============================================================
# CALC SCALED PRICES
# ============================================================

scaled_price_cols_list = []
for etf in sorted_etf_list:
    new_col_name = f"{etf}_scaled_price"
    scaled_price_cols_list.append(new_col_name)
    df[new_col_name] = df[f"{etf}_price"] * df[f"{anchor_etf}/{etf}_prev_moving_avg"]


# ============================================================
# CALC COMMISSIONS
# ============================================================

for etf in sorted_etf_list:
    new_col_name = f"{etf}_scaled_comm"
    df[new_col_name] = df[f"{anchor_etf}/{etf}_prev_moving_avg"] * comm_per_share


# ============================================================
# CALC SCALED CFs AFTER COMMISSIONS - SUBTRACT 
# ============================================================

minus_cols_list = []
for col in scaled_price_cols_list:
    new_col_name = col.replace("price", "price_minus_comm")
    minus_cols_list.append(new_col_name)
    df[new_col_name] = df[col] - df[col.replace("price", "comm")]


# ============================================================
# CALC SCALED CFs AFTER COMMISSIONS - ADD 
# ============================================================

plus_cols_list = []
for col in scaled_price_cols_list:
    new_col_name = col.replace("price", "price_plus_comm")
    plus_cols_list.append(new_col_name)
    df[new_col_name] = df[col] + df[col.replace("price", "comm")]


# ============================================================
# CALC DIFF IN BEST PRICES 
# ============================================================

df['min_price_plus_comm'] = df[plus_cols_list].min(axis=1) 
df['max_price_minus_comm'] = df[minus_cols_list].max(axis=1)
df['tgt_max-min'] = df['max_price_minus_comm'] - df['min_price_plus_comm']
df['tgt_pct_diff'] = df['tgt_max-min'] / df[f"{anchor_etf}_price"]


# ============================================================
# ID BEST ETFs TO BUY AND SELL
# ============================================================

# etf with lowest ln
valid_rows = df[scaled_price_cols_list].notna().any(axis=1)

# etf with lowest price including comm (to buy)
df['tgt_min_price_etf'] = pd.NA
df.loc[valid_rows, "tgt_min_price_etf"] = df.loc[valid_rows, plus_cols_list].idxmin(axis=1)
df["tgt_min_price_etf"] = df["tgt_min_price_etf"].str.replace("_scaled_price_plus_comm", "", regex=False)

# etf with highest price including comm (to sell)
df['tgt_max_price_etf'] =  pd.NA
df.loc[valid_rows, 'tgt_max_price_etf'] = df.loc[valid_rows, minus_cols_list].idxmax(axis=1)
df["tgt_max_price_etf"] = df["tgt_max_price_etf"].str.replace("_scaled_price_minus_comm", "", regex=False,)


# ============================================================
# EX-DIVIDEND / MONTH-END FLAGS
# ============================================================

df['new_date_col'] = df[date_col]
df.drop(columns=[date_col], inplace=True)
df.rename(columns={'new_date_col': 'date'}, inplace=True)

# These ETFs go ex-dividend on the first trading day
# of every month.
#
# ex_div_date is True on the first available trading
# day of each new month.

current_month = df["date"].dt.to_period("M")
previous_month = df["date"].shift(1).dt.to_period("M")

df["ex_div_date"] = (current_month != previous_month)

# Do not treat the first row of the entire dataset as an
# actual identified ex-dividend date.
df.loc[df.index[0], "ex_div_date"] = False


# ============================================================
# SAVE AND PRINT DF
# ============================================================

file_name = etf_group + "_prep2.csv"
file_path = Path("stat_arb_analysis") / file_name
df.to_csv(file_path, index=False) 

print(df)