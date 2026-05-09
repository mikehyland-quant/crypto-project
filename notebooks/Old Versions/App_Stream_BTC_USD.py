#!/usr/bin/env python
# coding: utf-8

# In[ ]:


INPUT_WB_NAME  = "2026 Inputs for Apps.xlsx"
INPUT_WS_NAME  = "BTC-USD INPUTS"
INPUT_TBL_NAME = "BTC_USD_INPUTS"

FLATTEN_COLS = ['unit_scalar_dict', 
                'mkt_data_dict', 
                'mkt_comm_dict',      
                'unit_cf_dict'
        ]

OUTPUT_COLS = ['time',
               'my_prod_type',
               'my_platform',
               'crypto_currency',
               'quote_currency',
               'my_name',
               'unit_scalar_dict_price',
               'mkt_data_dict_bid_price',
               'mkt_data_dict_ask_price',
           #    'mkt_comm_dict_join_bid',
               'unit_cf_dict_hit_bid',
               'unit_cf_dict_lift_ask'
        ]


# In[ ]:


import asyncio, json, websockets, os
import pandas as pd
import xlwings as xw

from datetime import datetime, UTC
from zoneinfo import ZoneInfo

from Methods_Make_Simple_Instruments import *
from Class_WSFeed import *

from Class_IBKRClient import *
ibkr = IBKRClient()

from Class_xlWings import *
xlw = xlWings()


# In[ ]:


def prepare_output(output_dict, output_df, input_dict, FLATTEN_COLS, OUTPUT_COLS):
    df = xlw.dictToDF(output_dict)

    for col in FLATTEN_COLS:
        df = xlw.flattenColumn(df, col, sep='_')

    now_datetime_nyc = datetime.now().replace(tzinfo=ZoneInfo("US/Eastern"))
    ts = now_datetime_nyc.strftime("%Y-%m-%d_%H-%M-%S")
    df['time'] = ts
    df = df[OUTPUT_COLS]

    if input_dict['replace or append'].lower() == 'replace':
        output_df = df
    elif input_dict['replace or append'].lower() == 'append':
        output_df = pd.concat([output_df, df], ignore_index=True)

    return output_df, now_datetime_nyc



def write_output(output_df, input_dict):
    if input_dict['csv or xls'].lower() == 'xls':
        xlw.printDFToXL(input_dict['output workbook name'],
                        input_dict['output worksheet name'],
                        input_dict['output cell name'],
                        output_df)

    elif input_dict['csv or xls'].lower() == 'csv':   # <-- fixes your bug here too
        directory = input_dict['output directory']
        filename  = input_dict['output workbook name']
        path = os.path.normpath(os.path.join(directory, filename))
        output_df.to_csv(path, index=False)



async def create_output(input_dict, output_dict):
    refresh = input_dict['timer interval']
    output_df = pd.DataFrame(columns=OUTPUT_COLS)

    while True:
        output_df, now_nyc = prepare_output(output_dict, output_df, 
                                               input_dict, FLATTEN_COLS, OUTPUT_COLS)
        write_output(output_df, input_dict)
        print(now_nyc)
        await asyncio.sleep(refresh)



# In[ ]:


async def main():

    df = xlw.getDF(INPUT_WB_NAME, INPUT_WS_NAME, INPUT_TBL_NAME, table=True)
    input_dict = df.set_index('Keys')['Values'].to_dict()


    objs_dict = make_simple_instruments(input_dict, xlw)


    ws_obj_dict   = {k: v for k, v in objs_dict.items() if v.platform_id != 'IBKR'}
    ws_feed = WSFeed(ws_obj_dict)


    ibkr_obj_dict = {}  # need for ibkr_start_streams below
    ibkr_list = [v for v in objs_dict.values() if v.platform_id == 'IBKR']
    if ibkr_list:
        await ibkr.connect()
        print("IBKR connected:", ibkr.ib.isConnected())

        await asyncio.gather(*(ibkr.create_simple_contract(o) for o in ibkr_list))

        if input_dict['create ibkr futures spreads']:
            fut_spd_list = make_futures_spreads(ibkr_list)        
            await asyncio.gather(*(ibkr.create_bag_contract(o.far_obj, o.near_obj, o) for o in fut_spd_list))
            ibkr_list.extend(fut_spd_list)

        ibkr_obj_dict = {obj.my_name : obj for obj in ibkr_list}


    output_dict = {**ws_obj_dict, **ibkr_obj_dict}


    # Run all streams concurrently
    await asyncio.gather(
        ws_feed.run(),
        ibkr.start_streams(ibkr_obj_dict),
        # add analysis methods here,    
        create_output(input_dict, output_dict)
    )


# In[ ]:


asyncio.run(main())


