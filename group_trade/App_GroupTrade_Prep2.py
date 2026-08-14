
# IMPORTS

import pandas as pd
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from fin_insts.Make_Single_Leg_Fin_Insts import get_db_df_and_make_single_leg_fin_insts
from input_output.Class_InputOutput import InputOutput

# CONSTANTS

STRAT_WB_NAME = "2026 Inputs for Group Trading.xlsx"
STRAT_WS_NAME = "INPUTS"
STRAT_TBL_NAME = STRAT_WS_NAME.replace(" ", "_")

# INSTANTIATE HELPER OBJECTS

io = InputOutput()

# START SCRIPT

async def group_trade_prep_two():

    # GET INPUTS

    wb, ws = io.set_xw_book_and_sheet(STRAT_WB_NAME, STRAT_WS_NAME)
    input_dict = io.get_xw_dict(ws, STRAT_TBL_NAME, table=True)

    ws = io.set_xw_sheet(wb, input_dict["fi_mults_sheet"])
    df = ws.range(input_dict["fi_mults_cell"]).expand().options(pd.DataFrame, header=1, index=False).value

    ws = io.set_xw_sheet(wb, input_dict["group_inputs_sheet"])
    group_inputs_df = io.get_xw_df(ws, input_dict['group_inputs_table'], table=True, headerRows=1, style=float) 

    df = df.merge(group_inputs_df, on=["my_fi_name", "my_pf_name", "anchor_fi"], how="left")

    # CLEAN INPUTS

    df["extra_shs"] = pd.to_numeric(df["extra_shs"], errors="coerce").fillna(0)
    df['shs_to_buy'] = None
    df['shs_to_sell'] = None

    # CREATE GROUPS

    groups= df.groupby("anchor_fi")["my_fi_name"].apply(list)
    
    #  SHARES

    for anchor_etf, symbol_list in groups.items():
        tgt_anchor_units = df.loc[df["my_fi_name"].eq(anchor_etf), "tgt_anchor_units"].iloc[0]

        for sym in symbol_list:
            row = df.loc[df["my_fi_name"] == sym].iloc[0]

            extra_shs = row.extra_shs
            tgt_shs = tgt_anchor_units * row.multiplier

            df.loc[df['my_fi_name'] == sym, "shs_to_buy"] = round(tgt_shs + extra_shs)
            df.loc[df['my_fi_name'] == sym, "shs_to_sell"] = round(tgt_shs - extra_shs)

    #  PROFIT MARGIN

    for anchor_etf, symbol_list in groups.items():
        profit_margin_units = df.loc[df["my_fi_name"].eq(anchor_etf), "profit_margin_units"].iloc[0]
        buy_profit_amt = float(df.loc[df["my_fi_name"].eq(anchor_etf), "profit_margin_unit_buy"].iloc[0])
        sell_profit_amt = float(df.loc[df["my_fi_name"].eq(anchor_etf), "profit_margin_unit_sell"].iloc[0])

        if profit_margin_units == 'pct':
            closing_price = float(df.loc[df["my_fi_name"].eq(anchor_etf), "closing_price"].iloc[0])
            buy_profit_amt = buy_profit_amt * closing_price
            sell_profit_amt = sell_profit_amt * closing_price

        for sym in symbol_list:
            df.loc[df['my_fi_name'] == sym, "buy_profit_margin"] = buy_profit_amt
            df.loc[df['my_fi_name'] == sym, "sell_profit_margin"] = sell_profit_amt

    # REARRANGE DF COLUMNS

    cols_to_move = ["TRUE/FALSE", "extra_shs", "moving_avg_days", "closing_price", "tgt_anchor_units", 
                    "profit_margin_unit_buy", "profit_margin_unit_sell", "profit_margin_units"]
    df = df[[c for c in df.columns if c not in cols_to_move] + cols_to_move]

    # OUTPUT TO SPREADSHEET

    ws, rng = io.set_xw_sheet_and_range(wb, input_dict["trading_inputs_sheet"], input_dict["trading_inputs_cell"])
    ws.clear_contents()
    io.print_xw_df(rng, df)    

asyncio.run(group_trade_prep_two())