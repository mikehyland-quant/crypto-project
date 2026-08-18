'''
need to attach a _calc_price (amt vs pct)
need to decide limit vs mkt
'''

# CONSTANTS 

IBKR_PORT      = 7496

STRAT_NAME     = "LimitLimit"

STRAT_WB_NAME  = "2026 Pairs Trading Inputs.xlsx"
STRAT_WS_NAME  = "ADMIN INPUTS"
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
from fin_insts.Make_Single_Leg_Fin_Insts import get_db_df_and_make_single_leg_fin_insts
# from fin_insts import FutureSpread, BestOf, Synthetic

# --- trading strategy ---
# from pairs_trade.PairsTrade_LimitMarket import PairsTrade_LimitMarket
from pairs_trade.PairsTrade_LimitLimit  import PairsTrade_LimitLimit

strategy_type_dict = {# "LimitMarket" : PairsTrade_LimitMarket,
                      "LimitLimit"  : PairsTrade_LimitLimit}


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

    ws = io.set_xw_sheet(wb, input_dict['trading_inputs_sheet'])
    fi_df = ws.range(input_dict['trading_inputs_cell']).expand().options(pd.DataFrame, index=False).value
    fi_df = fi_df[fi_df['TRUE/FALSE']]
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
# CREATE GROUPS
# ============================================================
    strat_dict = {}

    attr_names = fi_df.columns
    attr_names = attr_names.drop(["my_fi_name", "my_pf_name", "multiplier"])

    groups= fi_df.groupby("anchor_fi")["my_fi_name"].apply(list)

    for anchor_sym, sym_list in groups.items():

        for sym in sym_list:

# ============================================================
# ATTACH SPREADSHEET ATTRIBUTES
# ============================================================ 

            obj = next(obj for obj in objs_list if obj.ibkr_contract.symbol == sym)

            row = fi_df.loc[fi_df["my_fi_name"] == sym].iloc[0]

            obj.scalar_size_FIs_per_unit = float(row['multiplier'])
            obj.reset_scalars()

            for attr in attr_names:
                setattr(obj, attr, row[attr])
                # print(attr)

# ============================================================
# DEFINE STRATEGY
# ============================================================ 

        strat_dict[anchor_sym] = strategy_type_dict[STRAT_NAME](XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX)  
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
