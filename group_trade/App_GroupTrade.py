'''
need to attach a _calc_price (amt vs pct)
need to decide limit vs mkt
'''
 
# CONSTANTS 

IBKR_PORT      = 7497

STRAT_NAME     = "LimitLimit"

STRAT_WB_NAME  = "2026 Inputs for Pairs Trading.xlsx"
STRAT_WS_NAME  = "INPUTS"
STRAT_TBL_NAME = STRAT_WS_NAME.replace(" ", "_")

# IMPORTS
import asyncio
import pandas as pd

# --- system setup ---
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# --- input/output ---
from input_output.Class_InputOutput import InputOutput
io = InputOutput()

# --- IBKR ---
from ibkr.Class_IBKR_IB import IBKR_IB
ibkr = IBKR_IB(port=IBKR_PORT) 

# --- fin inst builders ---
from fin_insts.Make_Single_Leg_Fin_Insts import get_db_df_and_make_single_leg_fin_insts
from fin_insts.derived.Class_FI_BestOf import BestOf #, FutureSpread,  

def update_subscriber_data(self, obj):  # if self.mode == 'auto'
    obj.strat_hit_bid  = obj.cf_unit_hit_bid  - obj.comm_unit_hit_bid
    obj.strat_bid_size = obj.size_unit_bid
            
    obj.strat_lift_ask = obj.cf_unit_lift_ask - obj.comm_unit_lift_ask
    obj.strat_ask_size = obj.size_unit_ask

    self.update_best_of()
    # print(self.my_fi_name, self.strat_bid_size, self.strat_bid, self.strat_ask, self.strat_ask_size)

BestOf.update_subscriber_data = update_subscriber_data

# --- trading strategy ---
#from group_trade.GroupTrade_LimitMarket import GroupTrade_LimitMarket
from group_trade.GroupTrade_LimitLimit  import GroupTrade_LimitLimit

strategy_type_dict = {# "LimitMarket" : GroupTrade_LimitMarket,
                      "LimitLimit"  : GroupTrade_LimitLimit}

# ============================================================
# START
# ============================================================

async def main():

# ============================================================
# GET VARIABLES FROM SPREADSHEET
# ============================================================
    wb, ws = io.set_xw_book_and_sheet(STRAT_WB_NAME, STRAT_WS_NAME)

    input_dict = io.get_xw_dict(ws, STRAT_TBL_NAME, table=True)
    # print(input_dict, '\n')

# ============================================================
# GET ETFs FROM SPREADSHEET
# ============================================================

    fi_df = io.get_xw_df(ws, input_dict['fin_inst_table'], table=True)
    columns_to_delete = ["TRUE/FALSE", "extra_shs", "moving_avg_days", "closing_price",	"tgt_anchor_units",	 
                         "profit_margin_unit_buy", "profit_margin_unit_sell", "profit_margin_units"]
    fi_df = fi_df.drop(columns=columns_to_delete)
    # print(fi_df, '\n')

# ============================================================
# MAKE FIs
# ============================================================

    objs_list = get_db_df_and_make_single_leg_fin_insts(fi_df)
    for obj in objs_list:
        obj.platform_obj = ibkr  # this is the object not the name 
    # print(objs_list, '\n')

    await ibkr.connect()
    print("IBKR connected:", ibkr.ib.isConnected(), '\n')
    
    await asyncio.gather(*(ibkr.create_simple_contract(obj) for obj in objs_list))
    await asyncio.gather(*(ibkr.complete_obj(obj) for obj in objs_list))

# ============================================================
# GET HISTORICAL PRICES
# ============================================================ 

    contract_list = [obj.ibkr_contract for obj in objs_list]
    hist_prices_df = await ibkr.get_historical_closes_df(contract_list, remove_last_row=True)
    # print(hist_prices_df)

# ============================================================
# CREATE GROUPS
# ============================================================
    strat_dict = {}

    attr_names = fi_df.columns
    attr_names = attr_names.drop(["my_fi_name", "my_pf_name", "multiplier"])

    groups= fi_df.groupby("anchor_fi")["my_fi_name"].apply(list)

    for anchor_sym, sym_list in groups.items():

        bo_objs_list = []
        for sym in sym_list:

# ============================================================
# ATTACH SPREADSHEET ATTRIBUTES
# ============================================================ 

            obj = next(obj for obj in objs_list if obj.ibkr_contract.symbol == sym)

            row = fi_df.loc[fi_df["my_fi_name"] == sym].iloc[0]

            obj.scalar_size_FIs_per_unit = row['multiplier']
            obj.reset_scalars()

            for attr in attr_names:
                setattr(obj, attr, row[attr])
                # print(attr)

# ============================================================
# BUILD BEST OF OBJS LIST
# ============================================================ 
            
            bo_objs_list.append(obj)

# ============================================================
# MAKE BEST OF OBJECT
# ============================================================ 
        
        bo_obj = BestOf(anchor_sym, 
                        bo_objs_list, 
                        [("strat_hit_bid", max), ("strat_lift_ask", min)],
                        mode="auto")    
        
# ============================================================
# DEFINE STRATEGY
# ============================================================ 

        strat_dict[anchor_sym] = strategy_type_dict[STRAT_NAME](bo_obj)  
        # strat_dict[anchor_sym].need_to_print_active_orders   = False
        # strat_dict[anchor_sym].need_to_print_finished_orders = False  

# ============================================================
# RUN TASKS
# ============================================================ 

    tasks = []
    tasks.append(asyncio.create_task(ibkr.start_streams(objs_list)))
    
    await asyncio.sleep(1)

    await asyncio.gather(*(strat.done_event.wait() for strat in strat_dict.values()))

# ============================================================
# SHUT DOWN
# ============================================================ 
    
    # then cancel everything else
    for task in tasks:
        task.cancel()
    
    # optional: wait for clean cancellation
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # disconnect IBKR
    ibkr.ib.disconnect()
    
    print("Program finished cleanly.", '\n')

# ============================================================
# MAIN
# ============================================================ 

#await main()

if __name__ == "__main__":
    asyncio.run(main())
