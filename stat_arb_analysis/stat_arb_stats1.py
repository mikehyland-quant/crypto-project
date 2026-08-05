# cd git-crypto/crypto-project/alt_approach
# python new_strat_analyze.py


import numpy as np
import pandas as pd
from pathlib import Path


# ============================================================
# USER INPUTS
# ============================================================

etf_group = 'hi_yld'


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

input_file = etf_group + '_analysis.csv'
file_path = Path("stat_arb_analysis") / input_file
df = pd.read_csv(file_path)


# ============================================================
# PREP DF AND DATE COLUMN
# ============================================================

date_col = "date"

# Convert Excel serial dates into pandas dates
df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

df = df.sort_values(date_col).reset_index(drop=True)


# ============================================================
# SUMMARY STATISTICS
# ============================================================

daily_net_profit = (
    df["daily_net_profit"]
    .fillna(0)
)

total_net_profit = daily_net_profit.sum()

# Include every backtest day, including flat days with
# zero investment, so strategies that are rarely invested
# receive a lower average-capital denominator.
average_daily_investment = (
    df["gross_tgt_inv"]
    .fillna(0)
    .mean()
)

number_of_days = len(daily_net_profit)

# Annualize total net profit relative to average gross
# capital deployed:
#
# total profit / average investment / years in backtest
if (average_daily_investment > 0 and number_of_days > 0):
    annualized_return_on_avg_investment = (
        total_net_profit
        / average_daily_investment
        * 252
        / number_of_days
    )
else:
    annualized_return_on_avg_investment = np.nan

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
    df["tgt_position"]
    != df["current_position"]
).sum()

total_shares_traded = (
    df["SPBO_shs_to_trade"].abs().sum()
    + df["USIG_shs_to_trade"].abs().sum()
)

month_end_flattens = (
    df["flatten_at_close"]
    & df["current_position"].ne(0)
).sum()


# ============================================================
# SAVE AND PRINT RESULTS - PART 1 OF 2
# ============================================================


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
        print(f"Commission per share:   ${comm_per_share:.4f}")

        print(f"Enter long:             {enter_long_limit:.4%}")
        print(f"Exit long:              {exit_long_limit:.4%}")
        print(f"Enter short:            {enter_short_limit:.4%}")
        print(f"Exit short:             {exit_short_limit:.4%}")

        print()
        print("RESULTS")
        print("-" * 50)

        print(f"Total net profit:       ${total_net_profit:,.2f}")
        print(f"Avg daily investment:   ${average_daily_investment:,.2f}")
        print(
            f"Annualized return:      "
            f"{annualized_return_on_avg_investment:.2%}"
        )
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
                    "SPBO_price",
                    "USIG_price",
                    "ln(SPBO*/USIG)",
                    "ex_div_date",
                    "flatten_at_close",
                    "current_position",
                    "tgt_position",
                    "SPBO_current_shs",
                    "SPBO_tgt_shs",
                    "USIG_current_shs",
                    "USIG_tgt_shs",
                    "daily_net_profit",
                    "cumulative_net_profit",
                ]
            ].tail(40)
        )


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
            "Average daily investment": average_daily_investment,
            "Annualized return on avg investment": annualized_return_on_avg_investment,
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
                "average_daily_investment": average_daily_investment,
                "annualized_return_on_avg_investment": annualized_return_on_avg_investment,
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

average_daily_investment_df = results_long_df.pivot(
    index="enter_short_limit",
    columns="exit_short_limit",
    values="average_daily_investment",
)

annualized_return_on_avg_investment_df = results_long_df.pivot(
    index="enter_short_limit",
    columns="exit_short_limit",
    values="annualized_return_on_avg_investment",
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
    average_daily_investment_df,
    annualized_return_on_avg_investment_df,
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



wb = xw.Book()

output_sheets = {
    "Total Net Profit": total_net_profit_df,
    "Average Investment": average_daily_investment_df,
    "Annualized Return": annualized_return_on_avg_investment_df,
    "Annualized Sharpe": annualized_sharpe_df,
    "Max Drawdown": max_drawdown_df,
}

# Use the workbook's initial worksheet for the first output.
first_sheet = wb.sheets[0]

for i, (sheet_name, output_df) in enumerate(output_sheets.items()):

    if i == 0:
        ws = first_sheet
        ws.name = sheet_name
    else:
        ws = wb.sheets.add(
            sheet_name,
            after=wb.sheets[-1],
        )

    # Write the DataFrame, including row and column labels.
    ws.range("A1").options(
        pd.DataFrame,
        index=True,
        header=True,
    ).value = output_df

    # Basic formatting.
    ws.range("A1").expand().columns.autofit()
    ws.range("A1").expand().rows.autofit()

    # Freeze the row and column labels.
    ws.activate()
    ws.api.Application.ActiveWindow.SplitRow = 1
    ws.api.Application.ActiveWindow.SplitColumn = 1
    ws.api.Application.ActiveWindow.FreezePanes = True


# Apply suitable number formats.
wb.sheets["Total Net Profit"].range("B2").expand().number_format = "$#,##0.00"
wb.sheets["Average Investment"].range("B2").expand().number_format = "$#,##0.00"
wb.sheets["Annualized Return"].range("B2").expand().number_format = "0.00%"
wb.sheets["Annualized Sharpe"].range("B2").expand().number_format = "0.000"
wb.sheets["Max Drawdown"].range("B2").expand().number_format = "$#,##0.00"

wb.save(output_file)
wb.close()

print(f"Excel results saved to: {output_file}")


# ============================================================
# SAVE AND PRINT RESULTS - PART 2 OF 2
# ============================================================


results_df = pd.DataFrame(results)

results_df.to_csv(
    output_file,
    index=True,
)

print(results_df)
'''
