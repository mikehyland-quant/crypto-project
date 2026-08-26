
# ============================================================
# IMPORTS
# ============================================================

import asyncio
import pandas as pd

# --- system setup ---
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# --- input/output ---
from input_output.Class_InputOutput import InputOutput

# --- IBKR ---
from ibkr.Class_IBKR_IB import IBKR_IB

# --- fin inst builders ---
from fin_insts.Make_Single_Leg_Fin_Insts import get_db_df_and_make_single_leg_fin_insts
from fin_insts.derived.Class_FI_BestOf import BestOf #, FutureSpread,  

original_update_subscriber_data = BestOf.update_subscriber_data

def update_subscriber_data(self, obj):  # if self.mode == 'auto'
    obj.strat_hit_bid  = obj.cf_unit_hit_bid  - obj.comm_unit_hit_bid
    obj.strat_bid_size = obj.size_unit_bid
            
    obj.strat_lift_ask = obj.cf_unit_lift_ask - obj.comm_unit_lift_ask
    obj.strat_ask_size = obj.size_unit_ask

    original_update_subscriber_data(self, obj)
    # print(self.my_fi_name, self.strat_bid_size, self.strat_bid, self.strat_ask, self.strat_ask_size)

BestOf.update_subscriber_data = update_subscriber_data

# --- trading strategy ---
# from stat_arb_trading.StatArb_LimitMarket import StatArb_LimitMarket
from stat_arb.StatArb_LimitLimit  import StatArb_LimitLimit

# ============================================================
# CONSTANTS
# ============================================================

IBKR_PORT      = 7496

STRAT_NAME     = "LimitLimit"

STRAT_WS_NAME  = "ADMIN INPUTS"
STRAT_TBL_NAME = STRAT_WS_NAME.replace(" ", "_")

strategy_type_dict = {# "LimitMarket" : StatArb_LimitMarket,
                      "LimitLimit"  : StatArb_LimitLimit}

# ============================================================
# # INSTANTIATE HELPER OBJECTS
# ============================================================

io = InputOutput()
ibkr = IBKR_IB(port=IBKR_PORT)

# ============================================================
# START
# ============================================================

async def main():

# ============================================================
# GET VARIABLES FROM SPREADSHEET
# ============================================================

    STRAT_WB_NAME = "2026 Group Trading Inputs.xlsm"
    wb, ws = io.set_xw_book_and_sheet(STRAT_WB_NAME, STRAT_WS_NAME)

    input_dict = io.get_xw_dict(ws, STRAT_TBL_NAME, table=True)
    # print(input_dict, '\n')

# ============================================================
# GET ETFs FROM SPREADSHEET
# ============================================================

    ws = io.set_xw_sheet(wb, input_dict['trading_inputs_sheet'])
    fi_df = ws.range(input_dict['trading_inputs_upload_cell']).expand().options(pd.DataFrame, index=False).value
    fi_df = fi_df[fi_df['TRUE/FALSE']]
    # print(fi_df, '\n')

# ============================================================
# GET GROUP OR PAIR
# ============================================================  

    g_or_p = fi_df['g_or_p'].unique()
    if len(g_or_p) != 1:
        raise ValueError(f"Expected exactly one g_or_p value, found: {g_or_p}")
    else:
        group_or_pair = g_or_p[0]

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
# CREATE GROUPS
# ============================================================
    strat_dict = {}

    attr_names = fi_df.columns
    attr_names = attr_names.drop(["my_fi_name", "my_pf_name", "multiplier"])

    groups= fi_df.groupby("anchor_fi")["my_fi_name"].apply(list)

    for anchor_sym, sym_list in groups.items():

        anchor_objs_list = []
        for sym in sym_list:

# ============================================================
# ATTACH SPREADSHEET ATTRIBUTES
# ============================================================ 

            obj = next(obj for obj in objs_list if obj.ibkr_contract.symbol == sym)

            row = fi_df.loc[fi_df["my_fi_name"] == sym].iloc[0]

            obj.scalar_size_FIs_per_unit = float(row['multiplier'])
            obj.reset_scalars()

            for attr in attr_names:
                value = row[attr]

                if isinstance(value, str):
                    value = value.upper()

                setattr(obj, attr, value)
                # print(attr)

# ============================================================
# BUILD BEST OF OBJS LIST
# ============================================================ 
            
            anchor_objs_list.append(obj)

# ============================================================
# MAKE BEST OF OBJECT
# ============================================================ 
        
        if group_or_pair == 'group':
            bo_obj = BestOf(anchor_sym, 
                            anchor_objs_list, 
                            [("strat_hit_bid", max), ("strat_lift_ask", min)],
                            mode="auto",
                            ranked_list=True)    
        
# ============================================================
# DEFINE STRATEGY
# ============================================================ 

            strat_dict[anchor_sym] = strategy_type_dict[STRAT_NAME](group_or_pair, bo_obj)  

        else: # group_or_pair == 'pair'

            strat_dict[anchor_sym] = strategy_type_dict[STRAT_NAME](group_or_pair, anchor_objs_list)  

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

# await stat_arb_trade()

if __name__ == "__main__":
    asyncio.run(main()) 
