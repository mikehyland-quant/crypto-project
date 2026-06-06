
# CONSTANTS

INPUT_WB_NAME  = "2026 Inputs for Apps.xlsx"

####
INPUT_WS_NAME  = "PAIRS TRADING INPUTS"
INPUT_TBL_NAME = "PAIRS_TRADING_INPUTS"

STRAT_TBL_NAME = "ACTIVE_STRAT"
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
ibkr = IBKR_IB(port=7497)

# --- feeds ---
#from ws_feeds import WSFeedManager

# --- utils ---
from input_output.Standard_Output import standard_output
from input_output.Class_InputOutput import InputOutput
io = InputOutput()

# --- trading strategy ---
from strategies import PairsTrade_LimitMarket, PairsTrade_LimitLimit 

OUTPUT_COLS = []

async def standard_startup(io, INPUT_WB_NAME, INPUT_WS_NAME, INPUT_TBL_NAME):

    wb, ws = io.set_xw_book_and_sheet(INPUT_WB_NAME, INPUT_WS_NAME)
    df = io.get_xw_df(ws, INPUT_TBL_NAME, table=True)
    input_dict = df.set_index('Keys')['Values'].to_dict()
    
    wb, ws = io.set_xw_book_and_sheet(input_dict['input workbook name'], input_dict['true/false sheet name'])
    true_false_df = io.get_xw_df(ws, input_dict['true/false table name'], table=True)
    
    if 'TRUE/FALSE' not in true_false_df.columns:
        true_false_df = true_false_df.set_index('Keys').T

    true_false_df = true_false_df[true_false_df['TRUE/FALSE'] == True]
    
    wb, ws = io.set_xw_book_and_sheet(DB_WB_NAME, input_dict['crypto long name'])
    tbl = input_dict['crypto abbrev'] + "_static_data_table"
    db_df = io.get_xw_df(ws, tbl, table=True)
    
    merged_df = true_false_df.merge(db_df,how='left',on=['my_fi_name', 'my_pf_name'])

    fin_inst_objs_list = make_single_leg_fin_insts(merged_df)

    return input_dict, fin_inst_objs_list

async def main():

    input_dict, objs_list = await standard_startup(io, INPUT_WB_NAME, INPUT_WS_NAME, INPUT_TBL_NAME)
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
    futures_list = [obj for obj in ibkr_objs_list if obj.my_prod_type == 'future']
    bag_objs_list = FutureSpread.make_spreads(futures_list)                                    
    await asyncio.gather(*(ibkr.create_bag_contract(obj) for obj in bag_objs_list))
    '''                
        
    ''' 
    insert synthetic instruments here 
    output_list.extend(syn_objs_list)
    ''' 

    ''' 
    insert bestOf instruments here
    output_list[:0] = bo_objs_list   # this puts bestOf instruments at the top of the list
    ''' 

    #''' 
    #insert trading and analysis scripts here
    wb, ws = io.set_xw_book_and_sheet(INPUT_WB_NAME, INPUT_WS_NAME)
    strat_df = io.get_xw_df(ws, STRAT_TBL_NAME, table=True).set_index('Keys')
    strat_objs_list = [obj for obj in ibkr_objs_list if obj.my_fi_name in strat_df.loc['my_fi_name'].values]
    strat = PairsTrade_LimitLimit(strat_objs_list, strat_df)
        
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




