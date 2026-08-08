# cd git-crypto/crypto-project/alt_approach
# python new_strat_analyze.py


import numpy as np
# import pandas as pd
from pathlib import Path


# ============================================================
# START FUNCTION
# ============================================================

def stat_arb_analysis(df=None,
                      etf_group=None, 
                      suffix=None,
                      sorted_etf_list=None,
                      anchor_etf=None,
                      moving_avg_window=20,
                      comm_per_share=0.005,
                      dollar_constant=100_000,
                      limit_list=None):

    
# ============================================================
# CALC SHS PER UNIT
# ============================================================

    shs_per_unit_cols_list = [f"{etf}_shs_per_unit" for etf in sorted_etf_list]
    df[shs_per_unit_cols_list] = 0

    anchor_shs_col = f"{anchor_etf}_shs_per_unit"
    moving_avg_col = f"{anchor_etf}/{anchor_etf}_prev_moving_avg"
    df[anchor_shs_col] = (df[moving_avg_col] * dollar_constant / df[f"{anchor_etf}_price"]).round()

    for etf in sorted_etf_list:
        if etf == anchor_etf:
            continue

        moving_avg_col = f"{anchor_etf}/{etf}_prev_moving_avg"
        df[f"{etf}_shs_per_unit"] = (df[anchor_shs_col] * df[moving_avg_col]).round()


# ============================================================
# ADD COLUMNS FOR USE IN LOOP
# ============================================================

    current_shs_cols_list = [f"{etf}_current_shs" for etf in sorted_etf_list]
    tgt_shs_cols_list = [f"{etf}_tgt_shs" for etf in sorted_etf_list]

    df[current_shs_cols_list] = 0

    df["current_long_etf"] = None
    df["current_short_etf"] = None

    df["current_max-min"] = 0.0  
    df["current_pct_diff"] = 0.0

    df["current_position"] = 0
    df["open_trade"] = False
    df["exit_trade"] = False
    df["flatten_for_div"] = df["ex_div_date"].shift(1).eq(True)
    df["tgt_position"] = 0

    df["tgt_long_etf"] = None
    df["tgt_short_etf"] = None

    df[tgt_shs_cols_list] = 0

    df.loc[0:moving_avg_window - 1, current_shs_cols_list] = np.nan
    df.loc[0:moving_avg_window - 2, tgt_shs_cols_list] = np.nan

    df.loc[0:moving_avg_window - 1, "current_position"] = np.nan
    df.loc[0:moving_avg_window - 2, "tgt_position"] = np.nan

    df.loc[0:moving_avg_window - 1, "current_max-min"] = np.nan
    df.loc[0:moving_avg_window - 1, "current_pct_diff"] = np.nan


# ============================================================
# LOOP STARTS HERE
# ============================================================

    start_with_this_df = df.copy()

    results = {}
    grid_results = []

    min_limit = limit_list[0]
    max_limit = limit_list[1]
    limit_step_size = limit_list[2]
    epsilon = 1E-16

    for enter_limit in np.arange(min_limit, max_limit + epsilon, limit_step_size):
        enter_limit = round(enter_limit, 4)

        for exit_limit in np.arange(min_limit, enter_limit + epsilon, limit_step_size):
            exit_limit = round(exit_limit, 4)

            df = start_with_this_df.copy()

# ============================================================
# DETERMINE TARGET INDICATORS
# ============================================================

            signal = df["tgt_pct_diff"]
            df["open_trade"] = (signal > enter_limit)
            df["exit_trade"] = (signal < exit_limit)


# ============================================================
# START LOOP FOR CURRENT AND TARGET SHARE DETERMINATIONS
# ============================================================

            for row_num in range(moving_avg_window, len(df)):

                row = df.index[row_num]
                prior_row = df.index[row_num - 1]


# ============================================================
# DETERMINE CURRENT POSITION AND SPREAD
# ============================================================

                df.loc[row, current_shs_cols_list] = (df.loc[prior_row, tgt_shs_cols_list].to_numpy())

                df.loc[row, 'current_long_etf'] = df.loc[prior_row, 'tgt_long_etf']
                df.loc[row, 'current_short_etf'] = df.loc[prior_row, 'tgt_short_etf']
                df.loc[row, 'current_position'] = df.loc[prior_row, 'tgt_position']

                if df.loc[row, 'current_position'] == 1:
                    current_short_etf = df.loc[row, "current_short_etf"]
                    current_long_etf = df.loc[row, "current_long_etf"]
                
                    df.loc[row, 'current_max-min'] = (df.loc[row, f"{current_short_etf}_scaled_price_minus_comm"] - 
                                                    df.loc[row, f"{current_long_etf}_scaled_price_plus_comm"])
                else: 
                    df.loc[row, 'current_max-min'] = 0

                df.loc[row, 'current_pct_diff'] = df.loc[row, 'current_max-min'] / df.loc[row, f'{anchor_etf}_price']


# ============================================================
# DETERMINE TARGET POSITION 
# ============================================================

                if df.loc[row, "flatten_for_div"]:
                    df.loc[row, "tgt_position"] = 0

                elif df.loc[row, "open_trade"]:
                    df.loc[row, "tgt_position"] = 1

                elif df.loc[row, "exit_trade"]:
                    df.loc[row, "tgt_position"] = 0

                else:
                    df.loc[row, "tgt_position"] = -df.loc[row, "current_position"]


# ============================================================
# DETERMINE TARGET ETFs
# ============================================================

                if df.loc[row, 'tgt_position'] == 1:
                    df.loc[row, 'tgt_long_etf'] = df.loc[row, 'tgt_min_price_etf']
                    df.loc[row, 'tgt_short_etf'] = df.loc[row, 'tgt_max_price_etf']
                        
                elif df.loc[row, 'tgt_position'] == -1:
                    if df.loc[row, "current_max-min"] > exit_limit:
                        df.loc[row, 'tgt_long_etf'] = df.loc[row, 'current_long_etf']
                        df.loc[row, 'tgt_short_etf'] = df.loc[row, 'current_short_etf']

    
# ============================================================
# DETERMINE TARGET SHARES
# ============================================================

                for etf in sorted_etf_list:
                    col = f"{etf}_tgt_shs"
                            
                    if df.loc[row, "tgt_long_etf"] == etf:
                        df.loc[row, col] = df.loc[row, f"{etf}_shs_per_unit"]
                        
                    elif df.loc[row, "tgt_short_etf"] == etf:
                        df.loc[row, col] = -df.loc[row, f"{etf}_shs_per_unit"]


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

            df.loc[0:moving_avg_window, "gross_inv_amt"] = np.nan
            df.loc[0:moving_avg_window, "net_inv_amt"] = np.nan


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

            df.loc[0:moving_avg_window - 1, "daily_comm"] = np.nan


# ============================================================
# DAILY P&L
# ============================================================

            daily_pnl_col_list = []
            for etf in sorted_etf_list:
                col_name = f"{etf}_daily_profit"
                daily_pnl_col_list.append(col_name)
                df[col_name] = df[f"{etf}_current_shs"] * df[etf + "_price_chg"]
                    
            df["daily_gross_profit"] = df[daily_pnl_col_list].sum(axis=1)

            df.loc[0:moving_avg_window - 1, "daily_gross_profit"] = np.nan

# ============================================================
# P&L TOTALS
# ============================================================

            df["daily_net_profit"] = df["daily_gross_profit"] +  df["daily_comm"]  
            df["cumulative_net_profit"] = df["daily_net_profit"].cumsum()
                    

# ============================================================
# SAVE AND PRINT DF
# ============================================================

            replace_string = f"_analysis_{enter_limit}_{exit_limit}_{limit_step_size}"
            output_file = etf_group + replace_string + '.csv'

            file_path = Path("stat_arb/analysis_" + suffix + "/" + etf_group) / output_file
            df.to_csv(file_path, index=False)


'''
        print(df)
        print()

print()
print("finished")
print()

'''