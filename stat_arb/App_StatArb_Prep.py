
# IMPORTS

# import pandas as pd
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from fin_insts.Make_Single_Leg_Fin_Insts import get_db_df_and_make_single_leg_fin_insts
from input_output.Class_InputOutput import InputOutput
from ibkr.Class_IBKR_IB import IBKR_IB

# CONSTANTS

IBKR_PORT = 7496

STRAT_WS_NAME = "ADMIN INPUTS"
STRAT_TBL_NAME = STRAT_WS_NAME.replace(" ", "_")

# INSTANTIATE HELPER OBJECTS

io = InputOutput()
ibkr = IBKR_IB(port=IBKR_PORT)

# START SCRIPT

async def stat_arb_prep(group_or_pairs):

# GET INPUTS

    STRAT_WB_NAME = f"2026 {group_or_pairs} Trading Inputs.xlsm"

    wb, ws = io.set_xw_book_and_sheet(STRAT_WB_NAME, STRAT_WS_NAME)
    input_dict = io.get_xw_dict(ws, STRAT_TBL_NAME, table=True)

    ws = io.set_xw_sheet(wb, input_dict["FIs_sheet"])
    df = io.get_xw_df(ws, input_dict["FIs_table"], table=True)

# MAKE FINANCIAL INSTRUMENTS

    objs_list = get_db_df_and_make_single_leg_fin_insts(df)

    await ibkr.connect()
    print("IBKR connected:", ibkr.ib.isConnected(), "\n")

    await asyncio.gather(*(ibkr.create_simple_contract(obj) for obj in objs_list))
    await asyncio.gather(*(ibkr.complete_obj(obj) for obj in objs_list))

# GET HISTORICAL PRICES

    contracts = [obj.ibkr_contract for obj in objs_list]
    hist_prices_df = await ibkr.get_historical_closes_df(contracts, remove_today=True)

# CALCULATE MULTIPLIERS

    df["multiplier"] = float("nan")

    for idx, row in df.iterrows():
        sym = row["my_fi_name"]
        anchor = row["anchor"]
        ma_days = int(row["moving_avg_days"])

        ratio = hist_prices_df[anchor] / hist_prices_df[sym]
        df.at[idx, "multiplier"] = ratio.rolling(ma_days).mean().iloc[-1]

    df = df.drop(columns=['moving_avg_days', 'div_treatment'])

# OUTPUT TO SPREADSHEET

    ws, rng = io.set_xw_sheet_and_range(wb, input_dict["trading_inputs_sheet"], 
                                            input_dict["trading_inputs_download_cell"])
    # ws.clear_contents()
    io.print_xw_df(rng, df)    

# FINISH UP

    ibkr.ib.disconnect()
    print()
    print("Finished")
    print()

if __name__ == "__main__":
    asyncio.run(stat_arb_prep("group"))  # "group" or "pairs"