# cd git-crypto/crypto-project/alt_approach
# python new_strat_analyze.py


import numpy as np
import pandas as pd
from pathlib import Path
import xlwings as xw

'''
# ============================================================
# USER INPUTS
# ============================================================

etf_group ='ca_munis'
suffix = "2026"

moving_avg_window = 20


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
'''

# ============================================================
# START FUNCTION
# ============================================================

def stat_arb_comp_stats(etf_group=None, 
                        suffix=None,
                        moving_avg_window=20):


# ============================================================
# GET FILENAMES
# ============================================================

    directory = Path("stat_arb/analysis_" + suffix + "/" + etf_group)

    filename_list = [file.name for file in directory.iterdir() if file.is_file()]


# ============================================================
# READ EACH FILE
# ============================================================

    results = {}
    grid_results = []

    for filename in filename_list:

        file_path = Path(directory) / filename
        df = pd.read_csv(file_path)


# ============================================================
# DETERMINE ENTER AND EXIT LIMITS
# ============================================================

        filename_strings = filename.split("_")
        enter_limit = filename_strings[-3]
        exit_limit = filename_strings[-2]


# ============================================================
# PREP DF AND DATE COLUMN
# ============================================================

        date_col = "date"

        # Convert Excel serial dates into pandas dates
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

        df = df.sort_values(date_col).reset_index(drop=True)


# ============================================================
# CALC SUMMARY STATISTICS
# ============================================================

        daily_net_profit = df["daily_net_profit"]

        total_net_profit = daily_net_profit.sum()

        # Include every backtest day, including flat days with
        # zero investment, so strategies that are rarely invested
        # receive a lower average-capital denominator.
        average_daily_investment = df["gross_inv_amt"].mean()
        

        number_of_days = len(daily_net_profit) - moving_avg_window

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

        running_max_profit = df["cumulative_net_profit"].cummax()

        df["drawdown"] = df["cumulative_net_profit"] - running_max_profit

        max_drawdown = df["drawdown"].min()

        position_changes = (df["tgt_position"] != df["current_position"]).sum()

        '''
        total_shares_traded = (
            df["SPBO_shs_to_trade"].abs().sum()
            + df["USIG_shs_to_trade"].abs().sum()
        )
        '''

        month_end_flattens = (df["flatten_for_div"] & df["current_position"].ne(0)).sum()


# ============================================================
# STORE RESULTS
# ============================================================ 

        column_name = (
            f"Enter {float(enter_limit):.3%} | "
            f"Exit {float(exit_limit):.3%}"
        )

        
        results[column_name] = {
            "Enter limit": enter_limit,
            "Exit limit": exit_limit,
            "Total net profit": total_net_profit,
            "Average daily investment": average_daily_investment,
            "Annualized return on avg investment": annualized_return_on_avg_investment,
            "Annualized Sharpe": annualized_sharpe,
            "Maximum drawdown": max_drawdown,
            "Position changes": position_changes,
            "Month-end flattens": month_end_flattens,
    #        "Total shares traded": total_shares_traded,
        }
        
        
        grid_results.append(
            {
                "enter_limit": round(float(enter_limit), 6),
                "exit_limit": round(float(exit_limit), 6),
                "total_net_profit": total_net_profit,
                "average_daily_investment": average_daily_investment,
                "annualized_return_on_avg_investment": annualized_return_on_avg_investment,
                "annualized_sharpe": annualized_sharpe,
                "max_drawdown": max_drawdown,
            }
        )


# ============================================================
# GATHER RESULTS AND MAKE PIVOTS
# ============================================================ 

    results_table_df = pd.DataFrame(results)
    comp_results_df = pd.DataFrame(grid_results)

    total_net_profit_df = comp_results_df.pivot(
        index="enter_limit",
        columns="exit_limit",
        values="total_net_profit",
    )

    average_daily_investment_df = comp_results_df.pivot(
        index="enter_limit",
        columns="exit_limit",
        values="average_daily_investment",
    )

    annualized_return_on_avg_investment_df = comp_results_df.pivot(
        index="enter_limit",
        columns="exit_limit",
        values="annualized_return_on_avg_investment",
    )

    annualized_sharpe_df = comp_results_df.pivot(
        index="enter_limit",
        columns="exit_limit",
        values="annualized_sharpe",
    )

    max_drawdown_df = comp_results_df.pivot(
        index="enter_limit",
        columns="exit_limit",
        values="max_drawdown",
    )


# ============================================================
# CLEAN PIVOTS
# ============================================================ 

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

        output_df.index.name = "Enter Long"
        output_df.columns.name = "Exit Long"


# ============================================================
# TRANSFER OUTPUT TO WORKBOOK VIA XLWINGS
# ============================================================ 

    wb = xw.Book()

    output_sheets = {
        "Results Table" : results_table_df,
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


# ============================================================
# SAVE WORKBOOK
# ============================================================ 

    directory = Path("stat_arb/comp_stats_" + suffix)
    filename = f"{etf_group}_comp_stats_{suffix}.xlsx"

    # Create the directory if it does not already exist
    directory.mkdir(parents=True, exist_ok=True)

    output_path = directory / filename

    wb.save(output_path)
    wb.close()

    '''
    print()
    print("finished")
    print()




# ============================================================
# SAVE AND PRINT RESULTS - ALTERNATIVE
# ============================================================
        
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

    print(f"Enter trade:             {enter_limit:.4%}")
    print(f"Exit trade:              {exit_limit:.4%}")

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


print()
print("finished")
print()

'''