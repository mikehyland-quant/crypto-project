
# CONSTANTS

INPUT_WB_NAME  = "2026 Inputs for Pairs Trading.xlsx"

####
INPUT_WS_NAME  = "SPOT ETF TRADING INPUTS"
INPUT_TBL_NAME = "SPOT_ETF_TRADING_INPUTS"

STRAT_TBL_NAME = "SPOT_ETF_STRAT"
####

DB_WB_NAME  = "2026 Crypto Products Database.xlsx"

# --- system setup ---
import sys
import os
sys.path.append(os.path.abspath(".."))

# --- autoreload ---
#%load_ext autoreload
#%autoreload 2

import asyncio
from collections import defaultdict

# --- builders ---
from fin_insts import make_single_leg_fin_insts#, FutureSpread, BestOf, Synthetic

# --- IBKR ---
from ibkr.Class_IBKR_IB import IBKR_IB
#from ibkr.Class_IBKR_TWS import IBKR_TWS
ibkr = IBKR_IB(port=7496)

# --- feeds ---
#from ws_feeds import WSFeedManager

# --- utils ---
from input_output.Standard_Input_and_Output import standard_input, standard_output
from input_output.Class_InputOutput import InputOutput
io = InputOutput()

# --- trading strategy ---
from strategies import PairsTrade_SpotETF

async def main():

    input_dict, objs_list = await standard_input(INPUT_WB_NAME, INPUT_WS_NAME, INPUT_TBL_NAME)
    '''
    ws_objs_list = [obj for obj in objs_list if obj.my_pf_name != 'IBKR']
    ws_feed      = WSFeedManager(ws_objs_list)

    await ws_feed.complete_fi_objects()   
    '''

    ibkr_objs_list = [obj for obj in objs_list if obj.my_pf_name == 'IBKR']
    if ibkr_objs_list:
        await ibkr.connect()
        print("IBKR connected:", ibkr.ib.isConnected(), '\n')
        
        await asyncio.gather(*(ibkr.create_simple_contract(obj) for obj in ibkr_objs_list))
        await asyncio.gather(*(ibkr.complete_obj(obj) for obj in ibkr_objs_list))
        
    ''' 
    # insert ibkr BAG instruments here (future_spread, option_spread, option_combo, etc.)

    insert synthetic instruments here 
    output_list.extend(syn_objs_list)
    
    insert bestOf instruments here
    output_list[:0] = bo_objs_list   # this puts bestOf instruments at the top of the list
    ''' 

    #''' 
    #insert trading and analysis scripts here
    wb, ws = io.set_xw_book_and_sheet(INPUT_WB_NAME, INPUT_WS_NAME)
    strat_df = io.get_xw_df(ws, STRAT_TBL_NAME, table=True).set_index('Keys')
    strat_objs_list = [obj for obj in ibkr_objs_list if obj.my_fi_name in strat_df.loc['my_fi_name'].values]
    strat = PairsTrade_SpotETF(strat_objs_list, strat_df)
        
    for obj in strat_objs_list:
        obj.platform_obj = ibkr  # this is the object not the name
        
    strat.print_orders = False
    #'''    
      
    # Run all streams concurrently
    tasks = []

#    tasks.append(asyncio.create_task(ws_feed.run()))
#    tasks.append(asyncio.create_task(create_output(input_dict, output_list, OUTPUT_COLS)))
    if ibkr_objs_list:
        tasks.append(asyncio.create_task(ibkr.start_streams(strat_objs_list)))
        #tasks.append(asyncio.create_task(ibkr.start_streams(strat_objs_list)))

    await strat.done_event.wait()   
    
    # then cancel everything else
    for task in tasks:
        task.cancel()
    
    # optional: wait for clean cancellation
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # disconnect IBKR
    ibkr.ib.disconnect()
    
    print("Program finished cleanly.", '\n')

#await main()

if __name__ == "__main__":
    asyncio.run(main())




