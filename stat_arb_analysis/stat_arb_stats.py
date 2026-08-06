# cd git-crypto/crypto-project/alt_approach
# python new_strat_analyze.py


import numpy as np
import pandas as pd
from pathlib import Path


# ============================================================
# USER INPUTS
# ============================================================

etf_group = 'faln_angls'

comm_per_share = 0.005


# ============================================================
# CHOOSE ETFs
# ============================================================

etf_group_dict = {"agg"         : ['SCHZ', 'SPAB', 'IUSB', 'BND', 'AGG'],
                  "ca_munis"    : ['CMF', 'VTEC'],
                  "converts"    : ['CWB', 'ICVT'],
                  "corps"       : ['SPBO', 'USIG', 'VTC', 'CORP'],
                  "em_mkts"     : ['VWOB', 'EMB'],
                  "faln_angls"  : ['FALN', 'ANGL'],
                  "hi_yld"      : ['SPHY', 'SCYB', 'HYLB', 'USHY', 'HYG', 'JNK'],
                  "intl_agg"    : ['BNDX', 'IAGG'],
                  "intl_tsy"    : ['BWX', 'IGOV'],
                  "lt_corps"    : ['SPLB', 'IGLB', 'VCLT'],
                  "lt_tsy"      : ['SPTL', 'SCHQ', 'VGLT'],
                  "lt_tsy2"     : ['SPTL', 'SCHQ', 'VGLT', 'TLT'],
                  "mortgages"   : ['SPMB', 'VMBS', 'MBB'],
                  "munis"       : ['TFI', 'VTEB', 'MUB'],
                  "prefs"       : ['PFFD', 'PFF'],
                  "real_estate" : ['SCHH', 'USRT']}

sorted_etf_list = etf_group_dict[etf_group]
anchor_etf = sorted_etf_list[-1]


# ============================================================
# GET FILENAMES
# ============================================================

directory = Path("stat_arb_analysis/analysis/" + etf_group)

filename_list = [file.name for file in directory.iterdir() if file.is_file()]


# ============================================================
# READ DATA
# ============================================================

for filename in filename_list:

    file_path = Path(directory) / filename
    df = pd.read_csv(file_path)

# ============================================================
# PREP DF AND DATE COLUMN
# ============================================================

    date_col = "date"

    # Convert Excel serial dates into pandas dates
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    df = df.sort_values(date_col).reset_index(drop=True)


# ============================================================
# CURRENT INVESTMENT
# ============================================================

    # Daily P&L is earned by the shares carried into the day.
    # Measure the gross capital deployed over that same
    # close-to-close holding period using the preceding close.
    #
    # Flat days are zero and are intentionally included when
    # calculating average daily investment.

    inv_amt_col_list = []
    for etf in sorted_etf_list:
        col_name = f"{etf}_tgt_inv_amt"
        inv_amt_col_list.append(col_name)

        df[col_name] = df[f"{etf}_tgt_shs"].shift(1) * df[f"{etf}_price"].shift(1)

    df["gross_inv_amt"] = df[inv_amt_col_list].abs().sum(axis=1)
    df["net_inv_amt"] = df[inv_amt_col_list].sum(axis=1)


# ============================================================
# SHARES TO TRADE AT TODAY'S CLOSE
# ============================================================

    for etf in sorted_etf_list:
        df[f"{etf}_shs_to_trade"] = df[f"{etf}_tgt_shs"] - df[f"{etf}_current_shs"]

    for etf in sorted_etf_list:
        df[f"{etf}_shs_to_buy"] = df[f"{etf}_shs_to_trade"].clip(lower=0)

    for etf in sorted_etf_list:
        df[f"{etf}_shs_to_sell"] = -df[f"{etf}_shs_to_trade"].clip(upper=0)

    
# ============================================================
# COMMISSIONS
# ============================================================

    daily_comm_col_list = []
    for etf in sorted_etf_list:
        col_name = f"{etf}_daily_comm"
        daily_comm_col_list.append(col_name)
        df[col_name] = -abs(df[f"{etf}_shs_to_trade"] * comm_per_share)

    df["daily_comm"] = df[daily_comm_col_list].sum(axis=1)


# ============================================================
# DAILY P&L
# ============================================================

    daily_pnl_col_list = []
    for etf in sorted_etf_list:
        col_name = f"{etf}_daily_profit"
        daily_pnl_col_list.append(col_name)
        df[col_name] = df[f"{etf}_current_shs"] * df[etf + "_price_chg"]
            
    df["daily_gross_profit"] = df[daily_pnl_col_list].sum(axis=1)


# ============================================================
# P&L TOTALS
# ============================================================

    df["daily_net_profit"] = df["daily_gross_profit"] +  df["daily_comm"]  
    df["cumulative_net_profit"] = df["daily_net_profit"].fillna(0).cumsum()


# ============================================================
# SAVE FILE
# ============================================================

    df.to_csv(file_path, index=False)

print()
print("finished")
print()


