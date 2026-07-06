'''
need to attach a _calc_price (amt vs pct)
need to decide limit vs mkt
'''

# CONSTANTS 

IBKR_PORT      = 7496

STRAT_NAME     = "LimitMarket"

STRAT_WB_NAME  = "2026 Inputs for Pairs Trading.xlsx"
STRAT_WS_NAME  = "SPOT VS ETF INPUTS"
STRAT_TBL_NAME = STRAT_WS_NAME.replace(" ", "_")

# IMPORTS
import asyncio

# --- system setup ---
import sys
import os
sys.path.append(os.path.abspath(".."))

# --- input/output ---
from input_output.Class_InputOutput import InputOutput
io = InputOutput()

# --- IBKR ---
from ibkr.Class_IBKR_IB import IBKR_IB
ibkr = IBKR_IB(port=IBKR_PORT) 

# --- fin inst builders ---
from fin_insts.Make_Single_Leg_Fin_Insts import make_single_leg_fin_insts
# from fin_insts import FutureSpread, BestOf, Synthetic

# --- trading strategy ---
from pairs_trade.PairsTrade_LimitMarket import PairsTrade_LimitMarket
# from pairs_trade.PairsTrade_LimitLimit  import PairsTrade_LimitLimit

strategy_dict = {"LimitMarket" : PairsTrade_LimitMarket,
                 "LimitLimit"  : None}


# CODE

async def main():
    wb, ws = io.set_xw_book_and_sheet(STRAT_WB_NAME, STRAT_WS_NAME)

    strat_df = io.get_xw_df(ws, STRAT_TBL_NAME, table=True).set_index('keys')
    # print(strat_df, '\n')

    objs_list = make_single_leg_fin_insts(strat_df.T)
    for obj in objs_list:
        obj.platform_obj = ibkr  # this is the object not the name 
    # print(objs_list, '\n')

    await ibkr.connect()
    print("IBKR connected:", ibkr.ib.isConnected(), '\n')
    
    await asyncio.gather(*(ibkr.create_simple_contract(obj) for obj in objs_list))
    await asyncio.gather(*(ibkr.complete_obj(obj) for obj in objs_list))
        
    ''' 
    # insert ibkr BAG instruments here (future_spread, option_spread, option_combo, etc.)

    insert synthetic instruments here 
    output_list.extend(syn_objs_list)
    
    insert bestOf instruments here
    output_list[:0] = bo_objs_list   # this puts bestOf instruments at the top of the list
    ''' 

    strat = strategy_dict[STRAT_NAME](objs_list, strat_df)  
    # strat.need_to_print_active_orders   = False
    # strat.need_to_print_finished_orders = False  

    # print('test complete')
    # return
  
    # Run all streams concurrently
    tasks = []
    tasks.append(asyncio.create_task(ibkr.start_streams(objs_list)))

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
