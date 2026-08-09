
import numpy as np
import pandas as pd
import xlwings as xw
from pathlib import Path


# ============================================================
# USER INPUTS
# ============================================================

analysis_folder = "analysis_2026"

strategy_list = [
    "agg_no_IUSB",
    "corps",
    "hi_yld",
    "lt_corps",
]

date_col = "date"
gross_inv_col = "gross_inv_amt"
daily_profit_col = "daily_net_profit"

moving_avg_window = 10


# ============================================================
# PARAMETER RANGES
# ============================================================

first_param_min = 0.0001
first_param_max = 0.001
param_step = 0.0001

third_param = 0.0001
fourth_param = 10


# ============================================================
# MARGIN RATES
# ============================================================

margin_rates = {
    "agg_no_IUSB": 0.165,
    "corps": 0.165,
    "hi_yld": 0.275,
    "lt_corps": 0.165,
}


# ============================================================
# BASE DIRECTORY
# ============================================================

# This script lives in the stat_arb directory.
base_dir = Path(__file__).resolve().parent

analysis_dir = base_dir / analysis_folder


# ============================================================
# GET YEAR FROM ANALYSIS FOLDER
# ============================================================

# Example:
# analysis_2025 -> 2025

analysis_year = analysis_folder.split("_")[-1]


# ============================================================
# START EXCEL
# ============================================================

# Start Excel once and reuse it for all output files.
# This is much faster than opening and closing Excel for
# every parameter combination.

app = xw.App(visible=False)


try:

    # ========================================================
    # LOOP THROUGH FIRST PARAMETER
    # ========================================================

    first_param_values = np.arange(
        first_param_min,
        first_param_max + param_step / 2,
        param_step,
    )

    for first_param in first_param_values:

        # Round to avoid floating-point values such as
        # 0.00030000000000000003.
        first_param = round(first_param, 4)


        # ====================================================
        # LOOP THROUGH SECOND PARAMETER
        # ====================================================

        second_param_values = np.arange(
            0.0001,
            first_param + param_step / 2,
            param_step,
        )

        for second_param in second_param_values:

            second_param = round(second_param, 4)


            # =================================================
            # FORMAT PARAMETERS FOR FILENAMES
            # =================================================

            first_param_str = f"{first_param:.4f}"
            second_param_str = f"{second_param:.4f}"
            third_param_str = f"{third_param:.4f}"


            # =================================================
            # FILE SUFFIX
            # =================================================

            file_suffix = (
                f"_analysis_"
                f"{first_param_str}_"
                f"{second_param_str}_"
                f"{third_param_str}_"
                f"{fourth_param}.csv"
            )


            # =================================================
            # OUTPUT FILE
            # =================================================

            output_file = (
                f"combined_analysis_"
                f"{analysis_year}_"
                f"{first_param_str}_"
                f"{second_param_str}.xlsx"
            )

            output_path = (
                base_dir
                / output_file
            )


            print()
            print("=" * 70)
            print(
                f"Running: "
                f"{first_param_str} / "
                f"{second_param_str}"
            )
            print("=" * 70)


            # =================================================
            # READ EACH STRATEGY FILE
            # =================================================

            combined_df = None

            for strategy in strategy_list:

                folder = (
                    analysis_dir
                    / strategy
                )

                input_file = (
                    folder
                    / f"{strategy}{file_suffix}"
                )

                print(
                    f"Reading: {input_file.name}"
                )

                df = pd.read_csv(
                    input_file
                )


                # =============================================
                # KEEP ONLY REQUIRED COLUMNS
                # =============================================

                strategy_df = df[
                    [
                        date_col,
                        gross_inv_col,
                        daily_profit_col,
                    ]
                ].copy()


                # =============================================
                # RENAME STRATEGY COLUMNS
                # =============================================

                strategy_df.rename(
                    columns={
                        gross_inv_col:
                            f"{strategy}_gross_inv",

                        daily_profit_col:
                            f"{strategy}_daily_profit",
                    },
                    inplace=True,
                )


                # =============================================
                # MERGE BY DATE
                # =============================================

                if combined_df is None:

                    combined_df = (
                        strategy_df
                    )

                else:

                    combined_df = (
                        combined_df.merge(
                            strategy_df,
                            on=date_col,
                            how="outer",
                        )
                    )


            # =================================================
            # SORT BY DATE
            # =================================================

            combined_df[date_col] = pd.to_datetime(
                combined_df[date_col],
                format="mixed",
                errors="coerce",
            )

            combined_df.sort_values(
                by=date_col,
                inplace=True,
            )

            combined_df.reset_index(
                drop=True,
                inplace=True,
            )


            # =================================================
            # IDENTIFY STRATEGY COLUMNS
            # =================================================

            gross_inv_cols = [
                f"{strategy}_gross_inv"
                for strategy in strategy_list
            ]

            daily_profit_cols = [
                f"{strategy}_daily_profit"
                for strategy in strategy_list
            ]


            # =================================================
            # PORTFOLIO TOTAL GROSS INVESTMENT
            # =================================================

            combined_df["gross_inv_amt"] = (
                combined_df[
                    gross_inv_cols
                ]
                .fillna(0)
                .sum(axis=1)
            )


            # =================================================
            # PORTFOLIO TOTAL DAILY NET PROFIT
            # =================================================

            combined_df["daily_net_profit"] = (
                combined_df[
                    daily_profit_cols
                ]
                .fillna(0)
                .sum(axis=1)
            )


            # =================================================
            # CREATE MARGIN CAPITAL COLUMNS
            # =================================================

            margin_capital_cols = []

            for strategy in strategy_list:

                gross_col = (
                    f"{strategy}_gross_inv"
                )

                margin_col = (
                    f"{strategy}_margin_capital"
                )

                combined_df[margin_col] = (
                    combined_df[gross_col]
                    .fillna(0)
                    * margin_rates[strategy]
                )

                margin_capital_cols.append(
                    margin_col
                )


            # =================================================
            # TOTAL MARGIN CAPITAL
            # =================================================

            combined_df[
                "total_margin_capital"
            ] = (
                combined_df[
                    margin_capital_cols
                ]
                .sum(axis=1)
            )


            # =================================================
            # EXCLUDE MOVING-AVERAGE WARM-UP
            # =================================================

            valid_df = (
                combined_df
                .iloc[moving_avg_window:]
                .copy()
            )


            # =================================================
            # BASIC P&L SERIES
            # =================================================

            daily_net_profit = (
                valid_df[
                    "daily_net_profit"
                ]
            )

            number_of_days = (
                len(valid_df)
            )

            total_net_profit = (
                daily_net_profit.sum()
            )


            # =================================================
            # CUMULATIVE NET PROFIT
            # =================================================

            valid_df[
                "cumulative_net_profit"
            ] = (
                valid_df[
                    "daily_net_profit"
                ]
                .cumsum()
            )


            # =================================================
            # GROSS INVESTMENT STATISTICS
            # =================================================

            average_daily_investment = (
                valid_df[
                    "gross_inv_amt"
                ]
                .mean()
            )

            peak_gross_investment = (
                valid_df[
                    "gross_inv_amt"
                ]
                .max()
            )


            # =================================================
            # ANNUALIZED RETURN ON AVERAGE GROSS INVESTMENT
            # =================================================

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

                annualized_return_on_avg_investment = (
                    np.nan
                )


            # =================================================
            # MARGIN CAPITAL STATISTICS
            # =================================================

            average_daily_margin_capital = (
                valid_df[
                    "total_margin_capital"
                ]
                .mean()
            )

            p95_margin_capital = (
                valid_df[
                    "total_margin_capital"
                ]
                .quantile(0.95)
            )

            p99_margin_capital = (
                valid_df[
                    "total_margin_capital"
                ]
                .quantile(0.99)
            )

            peak_margin_capital = (
                valid_df[
                    "total_margin_capital"
                ]
                .max()
            )


            # =================================================
            # RETURN ON AVERAGE MARGIN CAPITAL
            # =================================================

            if (
                average_daily_margin_capital > 0
                and number_of_days > 0
            ):

                annualized_return_on_capital = (
                    total_net_profit
                    / average_daily_margin_capital
                    * 252
                    / number_of_days
                )

            else:

                annualized_return_on_capital = (
                    np.nan
                )


            # =================================================
            # RETURN ON PEAK MARGIN CAPITAL
            # =================================================

            if (
                peak_margin_capital > 0
                and number_of_days > 0
            ):

                annualized_return_on_peak_capital = (
                    total_net_profit
                    / peak_margin_capital
                    * 252
                    / number_of_days
                )

            else:

                annualized_return_on_peak_capital = (
                    np.nan
                )


            # =================================================
            # RETURN ON P95 MARGIN CAPITAL
            # =================================================

            if (
                p95_margin_capital > 0
                and number_of_days > 0
            ):

                annualized_return_on_p95_capital = (
                    total_net_profit
                    / p95_margin_capital
                    * 252
                    / number_of_days
                )

            else:

                annualized_return_on_p95_capital = (
                    np.nan
                )


            # =================================================
            # DOLLAR P&L SHARPE
            # =================================================

            daily_pnl_mean = (
                daily_net_profit.mean()
            )

            daily_pnl_std = (
                daily_net_profit.std()
            )

            if (
                daily_pnl_std != 0
                and not pd.isna(
                    daily_pnl_std
                )
            ):

                annualized_pnl_sharpe = (
                    daily_pnl_mean
                    / daily_pnl_std
                    * np.sqrt(252)
                )

            else:

                annualized_pnl_sharpe = (
                    np.nan
                )


            # =================================================
            # DAILY RETURN ON CAPITAL
            # =================================================

            valid_df[
                "daily_return_on_capital"
            ] = np.where(
                valid_df[
                    "total_margin_capital"
                ] > 0,

                valid_df[
                    "daily_net_profit"
                ]
                / valid_df[
                    "total_margin_capital"
                ],

                0.0,
            )


            # =================================================
            # RETURN-ON-CAPITAL SHARPE
            # =================================================

            daily_roc_mean = (
                valid_df[
                    "daily_return_on_capital"
                ]
                .mean()
            )

            daily_roc_std = (
                valid_df[
                    "daily_return_on_capital"
                ]
                .std()
            )

            if (
                daily_roc_std != 0
                and not pd.isna(
                    daily_roc_std
                )
            ):

                annualized_roc_sharpe = (
                    daily_roc_mean
                    / daily_roc_std
                    * np.sqrt(252)
                )

            else:

                annualized_roc_sharpe = (
                    np.nan
                )


            # =================================================
            # DRAWDOWN
            # =================================================

            running_max_profit = (
                valid_df[
                    "cumulative_net_profit"
                ]
                .cummax()
            )

            valid_df["drawdown"] = (
                valid_df[
                    "cumulative_net_profit"
                ]
                - running_max_profit
            )

            max_drawdown = (
                valid_df[
                    "drawdown"
                ]
                .min()
            )


            # =================================================
            # MAX DRAWDOWN / AVERAGE CAPITAL
            # =================================================

            if (
                average_daily_margin_capital
                > 0
            ):

                max_drawdown_pct_capital = (
                    max_drawdown
                    / average_daily_margin_capital
                )

            else:

                max_drawdown_pct_capital = (
                    np.nan
                )


            # =================================================
            # RETURN / DRAWDOWN
            # =================================================

            if (
                not pd.isna(
                    max_drawdown_pct_capital
                )
                and
                max_drawdown_pct_capital != 0
            ):

                return_to_drawdown = (
                    annualized_return_on_capital
                    / abs(
                        max_drawdown_pct_capital
                    )
                )

            else:

                return_to_drawdown = (
                    np.nan
                )


            # =================================================
            # INVESTMENT FREQUENCY
            # =================================================

            number_days_invested = (
                (
                    valid_df[
                        "gross_inv_amt"
                    ] > 0
                )
                .sum()
            )

            percent_days_invested = (
                (
                    valid_df[
                        "gross_inv_amt"
                    ] > 0
                )
                .mean()
            )


            # =================================================
            # POSITIVE / NEGATIVE / FLAT DAYS
            # =================================================

            number_positive_days = (
                (
                    valid_df[
                        "daily_net_profit"
                    ] > 0
                )
                .sum()
            )

            number_negative_days = (
                (
                    valid_df[
                        "daily_net_profit"
                    ] < 0
                )
                .sum()
            )

            number_flat_days = (
                (
                    valid_df[
                        "daily_net_profit"
                    ] == 0
                )
                .sum()
            )

            percent_positive_days = (
                number_positive_days
                / number_of_days
                if number_of_days > 0
                else np.nan
            )


            # =================================================
            # ACTIVE-DAY WIN RATE
            # =================================================

            active_pnl_days = (
                number_positive_days
                + number_negative_days
            )

            if active_pnl_days > 0:

                percent_positive_active_days = (
                    number_positive_days
                    / active_pnl_days
                )

            else:

                percent_positive_active_days = (
                    np.nan
                )


            # =================================================
            # PUT CALCULATED SERIES BACK
            # =================================================

            combined_df[
                "cumulative_net_profit"
            ] = np.nan

            combined_df[
                "daily_return_on_capital"
            ] = np.nan

            combined_df[
                "drawdown"
            ] = np.nan


            combined_df.loc[
                valid_df.index,
                "cumulative_net_profit"
            ] = (
                valid_df[
                    "cumulative_net_profit"
                ]
            )

            combined_df.loc[
                valid_df.index,
                "daily_return_on_capital"
            ] = (
                valid_df[
                    "daily_return_on_capital"
                ]
            )

            combined_df.loc[
                valid_df.index,
                "drawdown"
            ] = (
                valid_df[
                    "drawdown"
                ]
            )


            # =================================================
            # CREATE SUMMARY DATAFRAME
            # =================================================

            summary_df = pd.DataFrame(
                {
                    "stat": [

                        "first_parameter",
                        "second_parameter",

                        "number_of_days",

                        "total_net_profit",

                        "average_daily_investment",
                        "peak_gross_investment",

                        "average_daily_margin_capital",
                        "p95_margin_capital",
                        "p99_margin_capital",
                        "peak_margin_capital",

                        "annualized_return_on_avg_investment",
                        "annualized_return_on_capital",
                        "annualized_return_on_p95_capital",
                        "annualized_return_on_peak_capital",

                        "annualized_pnl_sharpe",
                        "annualized_roc_sharpe",

                        "max_drawdown",
                        "max_drawdown_pct_capital",
                        "return_to_drawdown",

                        "number_days_invested",
                        "percent_days_invested",

                        "number_positive_days",
                        "number_negative_days",
                        "number_flat_days",

                        "percent_positive_days",
                        "percent_positive_active_days",
                    ],

                    "value": [

                        first_param,
                        second_param,

                        number_of_days,

                        total_net_profit,

                        average_daily_investment,
                        peak_gross_investment,

                        average_daily_margin_capital,
                        p95_margin_capital,
                        p99_margin_capital,
                        peak_margin_capital,

                        annualized_return_on_avg_investment,
                        annualized_return_on_capital,
                        annualized_return_on_p95_capital,
                        annualized_return_on_peak_capital,

                        annualized_pnl_sharpe,
                        annualized_roc_sharpe,

                        max_drawdown,
                        max_drawdown_pct_capital,
                        return_to_drawdown,

                        number_days_invested,
                        percent_days_invested,

                        number_positive_days,
                        number_negative_days,
                        number_flat_days,

                        percent_positive_days,
                        percent_positive_active_days,
                    ],
                }
            )


            # =================================================
            # PRINT SUMMARY
            # =================================================

            print()
            print(
                summary_df.to_string(
                    index=False
                )
            )


            # =================================================
            # CREATE EXCEL WORKBOOK
            # =================================================

            wb = app.books.add()


            try:

                # =============================================
                # COMBINED ANALYSIS SHEET
                # =============================================

                ws = wb.sheets[0]

                ws.name = (
                    "combined_analysis"
                )

                ws.range(
                    "A1"
                ).options(
                    index=False,
                    header=True,
                ).value = combined_df

                ws.autofit()


                # =============================================
                # SUMMARY SHEET
                # =============================================

                summary_ws = (
                    wb.sheets.add(
                        "summary"
                    )
                )

                summary_ws.range(
                    "A1"
                ).options(
                    index=False,
                    header=True,
                ).value = summary_df

                summary_ws.autofit()


                # =============================================
                # FORMAT HEADER
                # =============================================

                summary_ws.range(
                    "A1:B1"
                ).api.Font.Bold = True


                # =============================================
                # FORMAT PERCENTAGE STATISTICS
                # =============================================

                percent_stats = [

                    "annualized_return_on_avg_investment",

                    "annualized_return_on_capital",

                    "annualized_return_on_p95_capital",

                    "annualized_return_on_peak_capital",

                    "max_drawdown_pct_capital",

                    "percent_days_invested",

                    "percent_positive_days",

                    "percent_positive_active_days",
                ]


                for row in range(
                    2,
                    len(summary_df) + 2
                ):

                    stat_name = (
                        summary_ws.range(
                            f"A{row}"
                        ).value
                    )

                    if (
                        stat_name
                        in percent_stats
                    ):

                        summary_ws.range(
                            f"B{row}"
                        ).number_format = (
                            "0.00%"
                        )


                # =============================================
                # SAVE WORKBOOK
                # =============================================

                wb.save(
                    output_path
                )


            finally:

                wb.close()


            print()
            print(
                f"Saved: {output_file}"
            )


finally:

    app.quit()


print()
print("=" * 70)
print("ALL PARAMETER COMBINATIONS COMPLETE")
print("=" * 70)
