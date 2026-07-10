
# CONSTANTS 

IBKR_PORT      = 7496

INPUT_WB_NAME  = "2026 Stat Arb Mkt Data.xlsx"
INPUT_WS_NAME  = "MKT DATA INPUTS"
INPUT_TBL_NAME = "MKT_DATA_INPUTS"

MKT_DATA_COLS = [   'my_prod_type',

                    'my_fi_name',
                    'my_pf_name',

                    'size_screen_bid',
                    'price_screen_bid',
                    'price_screen_ask',
                    'size_screen_ask'
                ]


# --- python imports ---
import asyncio
from collections import defaultdict
from datetime import datetime
import numpy as np
import pandas as pd
from zoneinfo import ZoneInfo

# --- system setup ---
import sys
import os
sys.path.append(os.path.abspath(".."))

# --- utils ---
# from IPython.display import display, clear_output
from input_output.Standard_Input_and_Output import standard_input, standard_output
from input_output.Class_InputOutput         import InputOutput
io = InputOutput()

# --- IBKR ---
from ibkr.Class_IBKR_IB import IBKR_IB
ibkr = IBKR_IB(port=IBKR_PORT)

# --- builders ---
from fin_insts.Make_Single_Leg_Fin_Insts      import make_single_leg_fin_insts

 
async def main():

    input_dict, objs_list = standard_input(INPUT_WB_NAME, INPUT_WS_NAME, INPUT_TBL_NAME)
        
    ibkr_objs_list = [obj for obj in objs_list if obj.my_pf_name == 'IBKR']

    if ibkr_objs_list:
        await ibkr.connect()
        print("IBKR connected:", ibkr.ib.isConnected())
        
        await asyncio.gather(*(ibkr.create_simple_contract(obj) for obj in ibkr_objs_list))
        await asyncio.gather(*(ibkr.complete_obj(obj) for obj in ibkr_objs_list))


    output_list = ibkr_objs_list


    # Run all streams concurrently
    tasks = []
#    tasks.append(asyncio.create_task(ws_feed.run()))
    if ibkr_objs_list:
        tasks.append(asyncio.create_task(ibkr.start_streams(ibkr_objs_list)))
#        tasks.append(asyncio.create_task(ibkr.start_streams(ibkr_fut_spds_objs_list)))

    await asyncio.sleep(input_dict.get('timer interval', 10))

    tasks.append(asyncio.create_task(standard_output(input_dict, output_list, MKT_DATA_COLS)))
#    tasks.append(asyncio.create_task(standard_output(etf_input_dict, ibkr_etf_list, ETF_COLS)))

    await asyncio.gather(*tasks)  # expose this for .py usage


# for ipynb usage
# await main()

# for .py usage and remember to expose await at end of main and comment out the two autoreload lines
if __name__ == "__main__":
   asyncio.run(main())
