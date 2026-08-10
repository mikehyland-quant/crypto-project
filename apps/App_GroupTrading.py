'''
need to attach a _calc_price (amt vs pct)
need to decide limit vs mkt
'''

# CONSTANTS 

IBKR_PORT      = 7496

STRAT_NAME     = "LimitLimit"

STRAT_WB_NAME  = "2026 Inputs for Pairs Trading.xlsx"
STRAT_WS_NAME  = "GROUP INPUTS"
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
# from fin_insts import FutureSpread, BestOf, Synthetic

# --- trading strategy ---
from pairs_trade.PairsTrade_LimitMarket import PairsTrade_LimitMarket
from pairs_trade.PairsTrade_LimitLimit  import PairsTrade_LimitLimit

strategy_dict = {"LimitMarket" : PairsTrade_LimitMarket,
                 "LimitLimit"  : PairsTrade_LimitLimit}


# CODE

async def get_historical_prices(objs_list, lookback_days, buffer_days):

    lookback_period = int(lookback_days + buffer_days)
    lookback_period = f"{lookback_period} D"

    length_of_each_period = "1 day"
    use_regular_trading_hours = True
    prices_to_use = "TRADES"

    df_list = []

    for obj in objs_list:

        contract = obj.ibkr_contract
        sym = contract.symbol

        bars = await ibkr.ib.reqHistoricalDataAsync(
            contract=contract,
            endDateTime="",          # "" means now
            durationStr=lookback_period,
            barSizeSetting=length_of_each_period,
            whatToShow=prices_to_use,
            useRTH=use_regular_trading_hours,
            formatDate=1
        )

        df = pd.DataFrame([(bar.date, bar.close) for bar in bars], columns=["date", "close"])
        df['date'] = pd.to_datetime(df['date']).dt.date
        df[sym] = df['close']
        df = df.set_index("date")

        df_list.append(df[sym])

    big_df = pd.concat(df_list, axis=1)
    big_df = big_df.iloc[:-1]

    return big_df




def calc_unit_scalars(hist_prices_df, anchor_etf, moving_avg_days):
    
    return unit_scalars_dict





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

    strat_df = io.get_xw_df(ws, input_dict['fin_inst_table'], table=True)
    strat_df = strat_df[strat_df["TRUE/FALSE"]]
    # print(strat_df, '\n')

# ============================================================
# MAKE FIs
# ============================================================

    objs_list = get_db_df_and_make_single_leg_fin_insts(strat_df)
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

    moving_avg_days = input_dict['moving_avg_days']
    # print(moving_avg_days)
    hist_prices_df = await get_historical_prices(objs_list, moving_avg_days, input_dict['buffer_days'])
    # print(hist_prices_df)

# ============================================================
# DEFINE ANCHOR ETF
# ============================================================ 

    anchor_etf = hist_prices_df.iloc[-1].idxmax()
    # print(anchor_etf)

# ============================================================
# CALC MOVING AVERAGES
# ============================================================ 

    ratio_df = hist_prices_df.rdiv(hist_prices_df[anchor_etf], axis=0)
    moving_avg_df = ratio_df.rolling(int(moving_avg_days)).mean()
    unit_scalars_dict = moving_avg_df.iloc[-1].to_dict()
    # print(unit_scalars_df)

    for obj in objs_list:
        sym = obj.ibkr_contract.symbol
        obj.scalar_size_FIs_per_unit = unit_scalars_dict[sym]
        obj.reset_scalars()
        # print(scalar)

# ============================================================
# SET PROFIT TARGET 
# ============================================================ 

    if input_dict['target_profit_units'] == 'amt':
        self.target_profit_amt = input_dict['target_profit_constant']
    else:
        self.target_profit_amt = (2 * input_dict['target_profit_constant'] * 
                                  hist_prices_df[anchor_etf].iloc[-1])

# ============================================================
# MAKE BEST OF OBJECT
# ============================================================ 

    bo_obj = BestOf(input_dict['group_name'], 
                    objs_list, 
                    [("cf_plus_comm_unit_hit_bid", "max"), ("cf_plus_comm_unit_lift_ask", "min")],
                    mode="auto")    

# ============================================================
# DEFINE STRATEGY
# ============================================================ 

    strat = strategy_dict[STRAT_NAME](objs_list, strat_df)  
    # strat.need_to_print_active_orders   = False
    # strat.need_to_print_finished_orders = False  

# ============================================================
# RUN TASKS
# ============================================================ 

    tasks = []
    tasks.append(asyncio.create_task(ibkr.start_streams(objs_list)))

    await strat.done_event.wait()   

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
