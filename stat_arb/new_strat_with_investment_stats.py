import numpy as np
import pandas as pd
import xlwings as xw


# ============================================================
# USER INPUTS
# ============================================================

input_file = "corps.csv"
output_file = input_file.replace(".csv", " results.xlsx")

moving_average_window = 20

dollar_constant = 100_000
commission_per_share = 0.005


# ============================================================
# READ DATA
# ============================================================

df = pd.read_csv(input_file)

df["DATE"] = pd.to_datetime(
    df["DATE"],
    errors="coerce",
)

for col in ["SPBO", "USIG"]:
    df[col] = pd.to_numeric(
        df[col]
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip(),
        errors="coerce",
    )

df = (
    df.dropna(subset=["DATE", "SPBO", "USIG"])
    .sort_values("DATE")
    .reset_index(drop=True)
)

df = df.rename(
    columns={
        "SPBO": "SPBO_price",
        "USIG": "USIG_price",
    }
)


# ============================================================
# PRICE CHANGES
# ============================================================

df["SPBO_price_chg"] = df["SPBO_price"].diff()
df["USIG_price_chg"] = df["USIG_price"].diff()


# ============================================================
# PRICE RATIO AND SIGNAL
# ============================================================

df["price_ratio"] = (
    df["USIG_price"]
    / df["SPBO_price"]
)

df["price_ratio_moving_avg"] = (
    df["price_ratio"]
    .rolling(
        window=moving_average_window,
        min_periods=moving_average_window,
    )
    .mean()
)

# Use only information available from the preceding row.
df["prior_price_ratio_moving_avg"] = (
    df["price_ratio_moving_avg"]
    .shift(1)
)

# Convert SPBO into an USIG-equivalent price using the
# preceding row's moving-average price ratio.
df["SPBO_scaled_price"] = (
    df["SPBO_price"]
    * df["prior_price_ratio_moving_avg"]
)

df["ln(SPBO*/USIG)"] = np.log(
    df["SPBO_scaled_price"]
    / df["USIG_price"]
)


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

# flatten_at_close is True on the trading day immediately
# preceding an ex-dividend date.
#
# The strategy's target position must be zero at that close.
# The strategy's target position must be zero at that close.
df["flatten_at_close"] = (
    df["ex_div_date"]
    .astype("boolean")
    .shift(-1, fill_value=False)
    .astype(bool)
)


# ============================================================
# LOOP STARTS HERE
# ============================================================

results = {}
grid_results = []

for enter_limit in np.arange(0.0001, 0.0011, 0.0001):
    for exit_limit in np.arange(0.000, enter_limit + 0.0001, 0.0001):

        enter_long_limit = -enter_limit  #-1
        exit_long_limit = -exit_limit  #-1

        enter_short_limit = enter_limit  #1
        exit_short_limit = exit_limit  #1

# ============================================================
# ENTRY AND EXIT CONDITIONS
# ============================================================

        signal = df["ln(SPBO*/USIG)"]

        df["enter_long"] = (
            signal < enter_long_limit
        )

        df["exit_long"] = (
            signal > exit_long_limit
        )

        df["enter_short"] = (
            signal > enter_short_limit
        )

        df["exit_short"] = (
            signal < exit_short_limit
        )


# ============================================================
# POSITION STATE
# ============================================================

        # Position definitions:
        #
        #  1 = Long spread
        #      Long SPBO / Short USIG
        #
        #  0 = Flat
        #
        # -1 = Short spread
        #      Short SPBO / Long USIG

        current_positions = np.zeros(
            len(df),
            dtype=int,
        )

        target_positions = np.zeros(
            len(df),
            dtype=int,
        )

        for i in range(len(df)):

            # Today's current position equals the target position
            # established at the preceding day's close.
            if i == 0:
                current_position = 0
            else:
                current_position = target_positions[i - 1]

            current_positions[i] = current_position

            # Default behavior is to maintain the existing position.
            target_position = current_position

            # Month-end override has first priority.
            if df["flatten_at_close"].iat[i]:

                target_position = 0

            elif current_position == 0:

                if df["enter_long"].iat[i]:
                    target_position = 1

                elif df["enter_short"].iat[i]:
                    target_position = -1

            elif current_position == 1:

                # Allow an immediate reversal from long to short.
                if df["enter_short"].iat[i]:
                    target_position = -1

                elif df["exit_long"].iat[i]:
                    target_position = 0

            elif current_position == -1:

                # Allow an immediate reversal from short to long.
                if df["enter_long"].iat[i]:
                    target_position = 1

                elif df["exit_short"].iat[i]:
                    target_position = 0

            target_positions[i] = target_position


        df["current_position"] = current_positions
        df["target_position"] = target_positions


# ============================================================
# TARGET SHARE CALCULATION
# ============================================================

        # USIG is the dollar-constant leg.
        #
        # target_position = 1:
        #     Short USIG
        #     Long SPBO
        #
        # target_position = -1:
        #     Long USIG
        #     Short SPBO


        df["SPBO_target_shs"] = (df["target_position"] * dollar_constant / df['SPBO_price']).round().astype(int)
        df["USIG_target_shs"] = (-df["target_position"] * dollar_constant / df['USIG_price']).round().astype(int)


# ============================================================
# CURRENT SHARES
# ============================================================

        # Current shares are the target shares established at
        # the preceding day's close.

        df["SPBO_current_shs"] = (
            df["SPBO_target_shs"]
            .shift(1)
            .fillna(0)
            .astype(int)
        )

        df["USIG_current_shs"] = (
            df["USIG_target_shs"]
            .shift(1)
            .fillna(0)
            .astype(int)
        )


# ============================================================
# CURRENT INVESTMENT
# ============================================================

        # Daily P&L is earned by the shares carried into the day.
        # Measure the gross capital deployed over that same
        # close-to-close holding period using the preceding close.
        #
        # Flat days are zero and are intentionally included when
        # calculating average daily investment.

        df["SPBO_current_inv"] = (
            df["SPBO_current_shs"]
            * df["SPBO_price"].shift(1)
        )

        df["USIG_current_inv"] = (
            df["USIG_current_shs"]
            * df["USIG_price"].shift(1)
        )

        df["gross_current_inv"] = (
            df["SPBO_current_inv"].abs()
            + df["USIG_current_inv"].abs()
        ).fillna(0)


# ============================================================
# SHARES TO TRADE AT TODAY'S CLOSE
# ============================================================

        df["SPBO_shs_to_trade"] = (
            df["SPBO_target_shs"]
            - df["SPBO_current_shs"]
        )

        df["USIG_shs_to_trade"] = (
            df["USIG_target_shs"]
            - df["USIG_current_shs"]
        )

        df["SPBO_shs_to_buy"] = (
            df["SPBO_shs_to_trade"]
            .clip(lower=0)
        )

        df["SPBO_shs_to_sell"] = (
            -df["SPBO_shs_to_trade"]
            .clip(upper=0)
        )

        df["USIG_shs_to_buy"] = (
            df["USIG_shs_to_trade"]
            .clip(lower=0)
        )

        df["USIG_shs_to_sell"] = (
            -df["USIG_shs_to_trade"]
            .clip(upper=0)
        )


# ============================================================
# POSITION MARKET VALUES
# ============================================================

        df["SPBO_target_inv"] = (
            df["SPBO_target_shs"]
            * df["SPBO_price"].shift(1)
        )

        df["USIG_target_inv"] = (
            df["USIG_target_shs"]
            * df["USIG_price"].shift(1)
        )

        df["gross_target_inv"] = (
            df["SPBO_target_inv"].abs()
            + df["USIG_target_inv"].abs()
        )

        df["net_target_inv"] = (
            df["SPBO_target_inv"]
            + df["USIG_target_inv"]
        )


# ============================================================
# DAILY P&L
# ============================================================

        # The position carried into today earns today's close-to-close
        # price change.
        #
        # A position entered at today's close does not earn today's
        # price movement.

        df["SPBO_daily_profit"] = (
            df["SPBO_current_shs"]
            * df["SPBO_price_chg"]
        )

        df["USIG_daily_profit"] = (
            df["USIG_current_shs"]
            * df["USIG_price_chg"]
        )

        df["daily_gross_profit"] = (
            df["SPBO_daily_profit"]
            + df["USIG_daily_profit"]
        )


# ============================================================
# COMMISSIONS
# ============================================================

        df["SPBO_commission"] = (
            df["SPBO_shs_to_trade"].abs()
            * commission_per_share
        )

        df["USIG_commission"] = (
            df["USIG_shs_to_trade"].abs()
            * commission_per_share
        )

        df["daily_commission"] = (
            df["SPBO_commission"]
            + df["USIG_commission"]
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

        # Include every backtest day, including flat days with
        # zero investment, so strategies that are rarely invested
        # receive a lower average-capital denominator.
        average_daily_investment = (
            df["gross_current_inv"]
            .fillna(0)
            .mean()
        )

        number_of_days = len(daily_net_profit)

        # Annualize total net profit relative to average gross
        # capital deployed:
        #
        # total profit / average investment / years in backtest
        if (
            average_daily_investment > 0
            and number_of_days > 0
        ):
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
            df["target_position"]
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
                    "target_position",
                    "SPBO_current_shs",
                    "SPBO_target_shs",
                    "USIG_current_shs",
                    "USIG_target_shs",
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

'''
results_df = pd.DataFrame(results)

results_df.to_csv(
    output_file,
    index=True,
)

print(results_df)
'''