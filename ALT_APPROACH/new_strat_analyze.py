# cd git-crypto/crypto-project/alt_approach
# python new_strat_analyze.py


import numpy as np
import pandas as pd


# ============================================================
# USER INPUTS
# ============================================================

input_file = "HI YLD prep.csv"

dollar_constant = 100_000
commission_per_share = 0.005


# ============================================================
# READ DATA
# ============================================================

df = pd.read_csv(input_file)

date_col = "date"

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

df = (
    df.dropna()
    .sort_values(date_col)
    .reset_index(drop=True)
)

sorted_etf_list =[
    col.removesuffix("_scaled_price")
    for col in df.columns
    if col.endswith("_scaled_price")
]


# ============================================================
# LOOP STARTS HERE
# ============================================================

results = {}
grid_results = []

for enter_limit in np.arange(0.001, 0.0071, 0.001):
    for exit_limit in np.arange(0.000, enter_limit + 0.0001, 0.001):

        determine_target_position(enter_limit, exit_limit)



# ============================================================
# ENTRY AND EXIT CONDITIONS
# ============================================================
def determine_target_position(enter_limit, exit_limit):
    signal = df["max_ln_minus_min_ln"]

    df["open_trade"] = (
        signal > enter_limit
    )

    df["exit_trade"] = (
        signal < exit_limit
    )

    df["target_position"] = (
        1 if df["open_trade"].iat[i] else
        0 if df["exit_trade"].iat[i] else
        df["target_position"].iat[i - 1] if i > 0 else 0
    )

def deterine_target_long():
    for i in range(len(df)):
        if df["target_position"].iat[i] == 0:
            df["target_long"].iat[i] = None
        else:
            current_long is
            target_long is
            switch if target_long - switch_cost_long > current_long



def determine_target_short():
    for i in range(len(df)):


def determine_target_shs():


def determine_change_in_shs():



def determine_daily_pnl():
    determine_daily_gross_pnl
    determine_daily_commissions
    determine_daily_net_pnl
    cumsum






# ============================================================
# POSITION MARKET VALUES
# ============================================================

        df["CWB_target_inv"] = (
            df["CWB_target_shs"]
            * df["CWB_price"].shift(1)
        )

        df["ICVT_target_inv"] = (
            df["ICVT_target_shs"]
            * df["ICVT_price"].shift(1)
        )

        df["gross_target_inv"] = (
            df["CWB_target_inv"].abs()
            + df["ICVT_target_inv"].abs()
        )

        df["net_target_inv"] = (
            df["CWB_target_inv"]
            + df["ICVT_target_inv"]
        )


# ============================================================
# DAILY P&L
# ============================================================

        # The position carried into today earns today's close-to-close
        # price change.
        #
        # A position entered at today's close does not earn today's
        # price movement.

        df["CWB_daily_profit"] = (
            df["CWB_current_shs"]
            * df["CWB_price_chg"]
        )

        df["ICVT_daily_profit"] = (
            df["ICVT_current_shs"]
            * df["ICVT_price_chg"]
        )

        df["daily_gross_profit"] = (
            df["CWB_daily_profit"]
            + df["ICVT_daily_profit"]
        )


# ============================================================
# COMMISSIONS
# ============================================================

        df["CWB_commission"] = (
            df["CWB_shs_to_trade"].abs()
            * commission_per_share
        )

        df["ICVT_commission"] = (
            df["ICVT_shs_to_trade"].abs()
            * commission_per_share
        )

        df["daily_commission"] = (
            df["CWB_commission"]
            + df["ICVT_commission"]
        )

        df["daily_net_profit"] = (
            df["daily_gross_profit"]
            - df["daily_commission"]
        )

        df["cumulative_net_profit"] = (
            df["daily_net_profit"]
            .fillna(0)
            .cumsum()
        )


# ============================================================
# SUMMARY STATISTICS
# ============================================================

        daily_net_profit = (
            df["daily_net_profit"]
            .fillna(0)
        )

        total_net_profit = daily_net_profit.sum()

        daily_mean = daily_net_profit.mean()
        daily_std = daily_net_profit.std()

        if daily_std != 0 and not pd.isna(daily_std):
            annualized_sharpe = (
                daily_mean
                / daily_std
                * np.sqrt(252)
            )
        else:
            annualized_sharpe = np.nan

        running_max_profit = (
            df["cumulative_net_profit"]
            .cummax()
        )

        df["drawdown"] = (
            df["cumulative_net_profit"]
            - running_max_profit
        )

        max_drawdown = df["drawdown"].min()

        position_changes = (
            df["target_position"]
            != df["current_position"]
        ).sum()

        total_shares_traded = (
            df["CWB_shs_to_trade"].abs().sum()
            + df["ICVT_shs_to_trade"].abs().sum()
        )

        month_end_flattens = (
            df["flatten_at_close"]
            & df["current_position"].ne(0)
        ).sum()


























# ============================================================
# SAVE AND PRINT RESULTS - PART 1 OF 2
# ============================================================

        '''
        df.to_csv(
            output_file,
            index=False,
        )
        
        print()
        print("BACKTEST COMPLETE")
        print("=" * 50)

        print(f"Input file:             {input_file}")
        print(f"Output file:            {output_file}")

        print()
        print("PARAMETERS")
        print("-" * 50)

        print(f"Moving-average window:  {moving_average_window}")
        print(f"Dollar constant:        ${dollar_constant:,.0f}")
        print(f"Commission per share:   ${commission_per_share:.4f}")

        print(f"Enter long:             {enter_long_limit:.4%}")
        print(f"Exit long:              {exit_long_limit:.4%}")
        print(f"Enter short:            {enter_short_limit:.4%}")
        print(f"Exit short:             {exit_short_limit:.4%}")

        print()
        print("RESULTS")
        print("-" * 50)

        print(f"Total net profit:       ${total_net_profit:,.2f}")
        print(f"Annualized Sharpe:      {annualized_sharpe:.3f}")
        print(f"Maximum drawdown:       ${max_drawdown:,.2f}")
        print(f"Position changes:       {position_changes:,}")
        print(f"Month-end flattens:     {month_end_flattens:,}")
        print(f"Total shares traded:    {total_shares_traded:,.0f}")

        print()
  
        print(
            df[
                [
                    "date",
                    "CWB_price",
                    "ICVT_price",
                    "ln(CWB*/ICVT)",
                    "ex_div_date",
                    "flatten_at_close",
                    "current_position",
                    "target_position",
                    "CWB_current_shs",
                    "CWB_target_shs",
                    "ICVT_current_shs",
                    "ICVT_target_shs",
                    "daily_net_profit",
                    "cumulative_net_profit",
                ]
            ].tail(40)
        )
        '''

# ============================================================
# ALT SAVE AND PRINT RESULTS
# ============================================================ 

        column_name = (
            f"Enter {enter_short_limit:.3%} | "
            f"Exit {exit_short_limit:.3%}"
        )

        results[column_name] = {
            "Enter long": enter_long_limit,
            "Exit long": exit_long_limit,
            "Enter short": enter_short_limit,
            "Exit short": exit_short_limit,
            "Total net profit": total_net_profit,
            "Annualized Sharpe": annualized_sharpe,
            "Maximum drawdown": max_drawdown,
            "Position changes": position_changes,
            "Month-end flattens": month_end_flattens,
            "Total shares traded": total_shares_traded,
        }

        grid_results.append(
            {
                "enter_short_limit": round(enter_short_limit, 6),
                "exit_short_limit": round(exit_short_limit, 6),
                "total_net_profit": total_net_profit,
                "annualized_sharpe": annualized_sharpe,
                "max_drawdown": max_drawdown,
            }
        )

results_long_df = pd.DataFrame(grid_results)

total_net_profit_df = results_long_df.pivot(
    index="enter_short_limit",
    columns="exit_short_limit",
    values="total_net_profit",
)

annualized_sharpe_df = results_long_df.pivot(
    index="enter_short_limit",
    columns="exit_short_limit",
    values="annualized_sharpe",
)

max_drawdown_df = results_long_df.pivot(
    index="enter_short_limit",
    columns="exit_short_limit",
    values="max_drawdown",
)

for output_df in [
    total_net_profit_df,
    annualized_sharpe_df,
    max_drawdown_df,
]:
    output_df.index = output_df.index.map(
        lambda x: f"{x:.2%}"
    )

    output_df.columns = output_df.columns.map(
        lambda x: f"{x:.2%}"
    )

    output_df.index.name = "Enter Short"
    output_df.columns.name = "Exit Short"

total_net_profit_df.to_csv("total_net_profit.csv")
annualized_sharpe_df.to_csv("annualized_sharpe.csv")
max_drawdown_df.to_csv("max_drawdown.csv")


# ============================================================
# SAVE AND PRINT RESULTS - PART 2 OF 2
# ============================================================

'''
results_df = pd.DataFrame(results)

results_df.to_csv(
    output_file,
    index=True,
)

print(results_df)
'''