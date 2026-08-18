
# IMPORTS

import pandas as pd
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from fin_insts.Make_Single_Leg_Fin_Insts import get_db_df_and_make_single_leg_fin_insts
from input_output.Class_InputOutput import InputOutput
from ibkr.Class_IBKR_IB import IBKR_IB

# CONSTANTS

IBKR_PORT = 7496

STRAT_WB_NAME = "2026 Pairs Trading Inputs.xlsx"
STRAT_WS_NAME = "ADMIN INPUTS"
STRAT_TBL_NAME = STRAT_WS_NAME.replace(" ", "_")

# INSTANTIATE HELPER OBJECTS

io = InputOutput()
ibkr = IBKR_IB(port=IBKR_PORT)

# START SCRIPT

async def group_trade_prep():

# GET INPUTS

    wb, ws = io.set_xw_book_and_sheet(STRAT_WB_NAME, STRAT_WS_NAME)
    input_dict = io.get_xw_dict(ws, STRAT_TBL_NAME, table=True)

    ws = io.set_xw_sheet(wb, input_dict["group_FIs_sheet"])
    df = io.get_xw_df(ws, input_dict["group_FIs_table"], table=True)

    ws = io.set_xw_sheet(wb, input_dict["group_inputs_sheet"])
    group_inputs_df = io.get_xw_df(ws, input_dict['group_inputs_table'], table=True, headerRows=1, style=float) 

    df = df.merge(group_inputs_df, on=["my_fi_name", "my_pf_name", "anchor_fi"], how="left")

# CLEAN INPUTS

    df["extra_shs"] = pd.to_numeric(df["extra_shs"], errors="coerce").fillna(0)
    df['TRUE/FALSE'] = False
    df['buy_size'] = None
    df['sell_size'] = None

# MAKE FINANCIAL INSTRUMENTS

    objs_list = get_db_df_and_make_single_leg_fin_insts(df)

    await ibkr.connect()
    print("IBKR connected:", ibkr.ib.isConnected(), "\n")

    await asyncio.gather(*(ibkr.create_simple_contract(obj) for obj in objs_list))
    await asyncio.gather(*(ibkr.complete_obj(obj) for obj in objs_list))

# GET HISTORICAL PRICES

    contracts = [obj.ibkr_contract for obj in objs_list]

    hist_prices_df = await ibkr.get_historical_closes_df(contracts, remove_last_row=True)

# CALCULATE MULTIPLIERS

    df["multiplier"] = None
    df["closing_price"] = None

    for idx, row in df.iterrows():
        sym = row["my_fi_name"]
        anchor = row["anchor_fi"]
        ma_days = int(row["moving_avg_days"])

        ratio = hist_prices_df[anchor] / hist_prices_df[sym]

        df.loc[idx, "multiplier"] = ratio.rolling(ma_days).mean().iloc[-1]
        df.loc[idx, "closing_price"] = hist_prices_df[sym].iloc[-1]

# CREATE GROUPS

    groups= df.groupby("anchor_fi")["my_fi_name"].apply(list)
    
# CALC SHARES AND PROFIT MARGINS

    for anchor_etf, symbol_list in groups.items():
        tgt_anchor_units = df.loc[df["my_fi_name"].eq(anchor_etf), "tgt_anchor_units"].iloc[0]

        profit_margin_units = df.loc[df["my_fi_name"].eq(anchor_etf), "profit_margin_units"].iloc[0]
        profit_amt = float(df.loc[df["my_fi_name"].eq(anchor_etf), "profit_margin_amt_per_unit"].iloc[0])

        if profit_margin_units == 'pct':
            closing_price = float(df.loc[df["my_fi_name"].eq(anchor_etf), "closing_price"].iloc[0])
            profit_amt = profit_amt * closing_price

        for sym in symbol_list:
            row = df.loc[df["my_fi_name"] == sym].iloc[0]

            extra_shs = row.extra_shs
            tgt_shs = tgt_anchor_units * row.multiplier

            df.loc[df['my_fi_name'] == sym, "buy_size"] = round(tgt_shs + extra_shs)
            df.loc[df['my_fi_name'] == sym, "sell_size"] = round(tgt_shs - extra_shs)

            df.loc[df['my_fi_name'] == sym, "profit_margin"] = profit_amt

# REARRANGE DF COLUMNS

    cols_to_move = ["TRUE/FALSE", "extra_shs", "moving_avg_days", "closing_price", "tgt_anchor_units", 
                    "profit_margin_amt_per_unit", "profit_margin_units"]
    df = df[[c for c in df.columns if c not in cols_to_move] + cols_to_move]

# OUTPUT TO SPREADSHEET

    ws, rng = io.set_xw_sheet_and_range(wb, input_dict["trading_inputs_sheet"], input_dict["trading_inputs_cell"])
    ws.clear_contents()
    io.print_xw_df(rng, df)    

# CLOSE IBKR

    ibkr.ib.disconnect()

asyncio.run(group_trade_prep()) 