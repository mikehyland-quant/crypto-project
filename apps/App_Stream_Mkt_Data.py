# %%
# CONSTANTS

INPUT_WB_NAME  = "2026 Market Data.xlsx"
INPUT_WS_NAME  = "MKT DATA INPUTS"
INPUT_TBL_NAME = "MKT_DATA_INPUTS"

# %%
# --- system setup ---
import sys
import os
sys.path.append(os.path.abspath(".."))

# %%
import asyncio
from collections import defaultdict
import numpy as np

# %%
# --- builders ---
from fin_insts import make_single_leg_fin_insts, FutureSpread, Synthetic, BestOf

# %%
# --- IBKR ---
from ibkr.Class_IBKR_IB import IBKR_IB
# from ibkr.Class_IBKR_TWS import IBKR_TWS
ibkr = IBKR_IB(port=7496)

# %%
# --- feeds ---
from ws_feeds import WSFeedManager

# %%
# --- utils ---
from input_output.Standard_Input_and_Output import standard_input, standard_output
from input_output.Class_InputOutput import InputOutput
io = InputOutput()

# %%
# this cell contains code for creating and calculating bestOf

attr_list = [('price_unit_bid', max), 
             ('price_unit_ask', min),
             ('cf_unit_hit_bid_all_in', max),
             ('cf_unit_lift_ask_all_in', max)]

def create_bo_objs_list(ws_objs_list, ibkr_objs_list, futures_list, syn_objs_list):
    ws_spot_list   = [obj for obj in ws_objs_list if obj.my_prod_type == 'spot']
    ibkr_spot_list = [obj for obj in ibkr_objs_list if obj.my_prod_type == 'spot']
    spot_list      = [*ws_spot_list, *ibkr_spot_list]
    bo_spot        = BestOf("SPOT", spot_list, attr_list)   

    etf_list = [obj for obj in ibkr_objs_list if obj.my_prod_type == 'equity']
    bo_etf   = BestOf("ETF", etf_list, attr_list)   

    futs_dict = defaultdict(list)
    for obj in futures_list:
        futs_dict[obj.my_fi_name].append(obj)
    for obj in syn_objs_list:
        last_name = obj.my_fi_name.split("/")[-1]
        futs_dict[last_name].append(obj)

    bo_objs_list = [bo_spot, bo_etf]
    for key, list_ in futs_dict.items():
        bo_obj = BestOf(key, list_, attr_list)
        bo_objs_list.append(bo_obj)

    return bo_objs_list


def calc_best_of(bo_objs_list):
    
    for obj in bo_objs_list:

        for obj_ in obj.objs_list:
            
            # print(obj_.my_fi_name, obj_.cf_unit_hit_bid, obj_.comm_unit_hit_bid, obj_.cf_unit_lift_ask, obj_.comm_unit_lift_ask)
            
            cf = getattr(obj_, 'cf_unit_hit_bid', np.nan)
            comm = getattr(obj_, 'comm_unit_hit_bid', np.nan)
            setattr(obj_, 'cf_unit_hit_bid_all_in',  cf  - comm)
            
            cf = getattr(obj_, 'cf_unit_lift_ask', np.nan)
            comm = getattr(obj_, 'comm_unit_lift_ask', np.nan)
            setattr(obj_, 'cf_unit_lift_ask_all_in', cf  - comm)

            # print(obj_.my_fi_name, obj_.cf_unit_hit_bid_all_in, obj_.cf_unit_lift_ask_all_in)
        
        obj.update_best_of()
        
        for attr, x in attr_list:

            b_obj = getattr(obj, attr + '_obj')

            if 'bid' in attr:
                new_attr = 'size_unit_bid'
                amt = getattr(b_obj, new_attr)
            elif 'ask' in attr:
                new_attr = 'size_unit_ask'
                amt = getattr(b_obj, new_attr)

            setattr(obj, new_attr, amt)

            if 'cf' in attr:

                if 'bid' in attr:
                    tail = '_hit_bid'
                elif 'ask' in attr:
                    tail = '_lift_ask'

                for new_attr in ['comm_unit', 'cf_unit']:
                    amt = getattr(b_obj, new_attr + tail)
                    setattr(obj, new_attr + tail, amt)
              
    return bo_objs_list

# %%
from datetime import datetime
import pandas as pd
from zoneinfo import ZoneInfo
from IPython.display import display, clear_output

OUTPUT_COLS = [
              'my_prod_type',

              'my_fi_name',
              'my_pf_name',

              'numerator_currency',
              'denominator_currency',

              'size_screen_bid',
              'price_screen_bid',
              'price_screen_ask',
              'size_screen_ask',

              'size_unit_bid',
              'price_unit_bid',
              'price_unit_ask',
              'size_unit_ask',

              'size_unit_bid',
              'comm_unit_hit_bid',
              'cf_unit_hit_bid',
              'cf_unit_hit_bid_all_in',
              'cf_unit_lift_ask_all_in',
              'cf_unit_lift_ask',
              'comm_unit_lift_ask',
              'size_unit_ask',
             
              'days_settle_comm',
              'days_settle_trade',
              'days_settle_expiry',
              'days_settle_expiry_near', 	 
              'days_settle_expiry_far',

              #'time',
            ]

async def edited_standard_output(input_dict, output_list, bo_objs_list, OUTPUT_COLS, FLATTEN_COLS=[]):
    
    refresh      = input_dict.get('timer interval', 10)
    display_mode = input_dict.get('display df onscreen', False)
    csv_mode     = input_dict.get('save df to csv', False)
    xl_mode      = input_dict.get('send df to xl', False)
    print_ts     = input_dict.get('print timestamp onscreen', False)
    add_ts       = input_dict.get('add timestamp to output df', False)

    # print(refresh, display_mode, csv_mode, xl_mode, print_ts, add_ts)

    need_history = any(mode == 'append' for mode in [display_mode, csv_mode, xl_mode])
    history_chunks = []
    history_df = None
    
    if csv_mode != False:
        directory = input_dict['output directory']
        filename  = input_dict['output workbook name']
        path      = os.path.normpath(os.path.join(directory, filename))
    
    if xl_mode != False:
        wb, ws, cell = io.set_xw_book_sheet_and_range(input_dict['output workbook name'],
                                                      input_dict['output worksheet name'],
                                                      input_dict['output cell name'])

    await asyncio.sleep(1)

    while True:

        ts = datetime.now(ZoneInfo("US/Eastern")).strftime("%Y-%m-%d_%H-%M-%S")

        if print_ts:
            print(ts)

        bo_objs_list = calc_best_of(bo_objs_list)
        
        current_df = io.convert_objs_to_printable_df(output_list, OUTPUT_COLS, FLATTEN_COLS)
    
        if add_ts:
            current_df['time'] = ts

        # print(current_df)
            
        if need_history:
            if current_df is None or current_df.empty:
                # nothing to add → exit this block
                pass
            else:
                history_chunks.append(current_df)
                if display_mode == 'append' or xl_mode == 'append':
                    history_df = pd.concat(history_chunks, ignore_index=True)
            
        if display_mode:
            df = history_df if display_mode == 'append' else current_df
            clear_output(wait=True)
            display(df)

        if csv_mode:
            if csv_mode == 'append':
                current_df.to_csv(path, mode='a', header=not os.path.exists(path), index=False)
            else:
                current_df.to_csv(path, index=False)

        if xl_mode:
            df = history_df if xl_mode == 'append' else current_df
            cell.options(index=False, header=True).value = df
        
        await asyncio.sleep(refresh)

# %%
ETF_COLS = ['my_fi_name',
            'price_screen_bid',
            'price_screen_ask']


async def make_etf_inputs(input_dict):
    etf_input_dict = input_dict.copy()

    today = datetime.today().strftime("%Y-%m-%d")

    etf_input_dict['output workbook name']       = 'ETF_' + today + '.csv'
    etf_input_dict['timer interval']             = input_dict['timer interval'] * 60
    
    etf_input_dict['save df to csv']             = 'append'
    etf_input_dict['add timestamp to output df'] = True

    etf_input_dict['display df onscreen']        = False
    etf_input_dict['send df to xl']              = False
    etf_input_dict['print timestamp onscreen']   = False
    
    return etf_input_dict 


# %%
async def main():

    input_dict, objs_list = await standard_input(INPUT_WB_NAME, INPUT_WS_NAME, INPUT_TBL_NAME)
    etf_input_dict = await make_etf_inputs(input_dict)

    ws_objs_list = [obj for obj in objs_list if obj.my_pf_name != 'IBKR']
    ws_feed      = WSFeedManager(ws_objs_list)

    await ws_feed.complete_fi_objects()   
        
    ibkr_objs_list     = [obj for obj in objs_list if obj.my_pf_name == 'IBKR']
    if ibkr_objs_list:
        await ibkr.connect()
        print("IBKR connected:", ibkr.ib.isConnected())
        
        await asyncio.gather(*(ibkr.create_simple_contract(obj) for obj in ibkr_objs_list))
        await asyncio.gather(*(ibkr.complete_obj(obj) for obj in ibkr_objs_list))

    #for obj in ibkr_objs_list:
    #   print(obj.ibkr_details)


#rarely change anything above here
    
    ws_spot_list   = [obj for obj in ws_objs_list if obj.my_prod_type == 'spot']
    ws_futs_list   = [obj for obj in ws_objs_list if obj.my_prod_type == 'future']
    
    ibkr_spot_list = [obj for obj in ibkr_objs_list if obj.my_prod_type == 'spot']
    ibkr_etf_list  = [obj for obj in ibkr_objs_list if obj.my_prod_type == 'equity']
    ibkr_futs_list = [obj for obj in ibkr_objs_list if obj.my_prod_type == 'future']
    ibkr_opts_list = [obj for obj in ibkr_objs_list if obj.my_prod_type == 'option']

    ibkr_futs_list_btc = [obj for obj in ibkr_futs_list if "BTC" in obj.my_fi_name]
    ibkr_futs_list_eth = [obj for obj in ibkr_futs_list if "ETH" in obj.my_fi_name]

    #''' 
    # insert ibkr BAG instruments here (future_spread, option_spread, option_combo, etc.
    ibkr_fut_spds_objs_list_btc = FutureSpread.make_spreads(ibkr_futs_list_btc)                                    
    ibkr_fut_spds_objs_list_eth = FutureSpread.make_spreads(ibkr_futs_list_eth)  

    ibkr_fut_spds_objs_list  = [*ibkr_fut_spds_objs_list_btc, *ibkr_fut_spds_objs_list_eth]
    await asyncio.gather(*(obj.make_ibkr_spread_contract(ibkr) for obj in ibkr_fut_spds_objs_list))
    #'''                
 
    #''' 
    #insert synthetic instruments here 
    syn_objs_list_btc = Synthetic.make_syn_futures_list(ibkr_futs_list_btc, ibkr_fut_spds_objs_list_btc)
    syn_objs_list_eth = Synthetic.make_syn_futures_list(ibkr_futs_list_eth, ibkr_fut_spds_objs_list_eth)
    syn_objs_list = (*syn_objs_list_btc, *syn_objs_list_eth)
    #''' 

    #''' 
    #insert bestOf instruments here
    bo_objs_list = create_bo_objs_list(ws_objs_list, ibkr_objs_list, ibkr_futs_list, syn_objs_list)
    #''' 

    output_list = [
        *bo_objs_list,
        *ws_spot_list,
        *ibkr_spot_list, 
        *ibkr_etf_list,
        *ws_futs_list,
        *ibkr_futs_list,
        *ibkr_opts_list,
        *ibkr_fut_spds_objs_list_btc,                                   
        *ibkr_fut_spds_objs_list_eth,
        *syn_objs_list
                   ]
    
    # Run all streams concurrently
    tasks = []
    tasks.append(asyncio.create_task(ws_feed.run()))
    if ibkr_objs_list:
        tasks.append(asyncio.create_task(ibkr.start_streams(ibkr_objs_list)))
        tasks.append(asyncio.create_task(ibkr.start_streams(ibkr_fut_spds_objs_list)))

    await asyncio.sleep(input_dict.get('timer interval', 10))

    tasks.append(asyncio.create_task(edited_standard_output(input_dict, output_list, bo_objs_list, OUTPUT_COLS)))
    tasks.append(asyncio.create_task(standard_output(etf_input_dict, ibkr_etf_list, ETF_COLS)))

    await asyncio.gather(*tasks)  # expose this for .py usage


# %%
# for ipynb usage
# await main()

# for .py usage and remember to expose await at end of main and comment out the two autoreload lines
if __name__ == "__main__":
   asyncio.run(main())

# %%



