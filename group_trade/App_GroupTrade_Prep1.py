
# IMPORTS

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from fin_insts.Make_Single_Leg_Fin_Insts import get_db_df_and_make_single_leg_fin_insts
from input_output.Class_InputOutput import InputOutput
from ibkr.Class_IBKR_IB import IBKR_IB

# CONSTANTS

IBKR_PORT = 7496

STRAT_WB_NAME = "2026 Inputs for Group Trading.xlsx"
STRAT_WS_NAME = "INPUTS"
STRAT_TBL_NAME = STRAT_WS_NAME.replace(" ", "_")

# INSTANTIATE HELPER OBJECTS

io = InputOutput()
ibkr = IBKR_IB(port=IBKR_PORT)

# START SCRIPT

async def group_trade_prep_one():

    # GET INPUTS

    wb, ws = io.set_xw_book_and_sheet(STRAT_WB_NAME, STRAT_WS_NAME)
    input_dict = io.get_xw_dict(ws, STRAT_TBL_NAME, table=True)

    ws = io.set_xw_sheet(wb, input_dict["group_FIs_sheet"])
    df = io.get_xw_df(ws, input_dict["group_FIs_table"], table=True)
    df = df[df["TRUE/FALSE"]].copy()

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

    # OUTPUT TO SPREADSHEET

    ws, rng = io.set_xw_sheet_and_range(wb, input_dict["fi_mults_sheet"], input_dict["fi_mults_cell"])
    ws.clear_contents()
    io.print_xw_df(rng, df)    

    # CLOSE IBKR

    ibkr.ib.disconnect()

asyncio.run(group_trade_prep_one())