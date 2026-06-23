
import os
import asyncio
from datetime import datetime
import pandas as pd
from zoneinfo import ZoneInfo
from IPython.display import display, clear_output

# import xlwings as xw

from fin_insts import make_single_leg_fin_insts, FutureSpread, Synthetic, BestOf

from input_output.Class_InputOutput import InputOutput
io = InputOutput()
 

database_wb  = '2026 Crypto Products Database.xlsx'
database_ws  = 'Crypto'
database_tbl = 'crypto_static_data_table'


async def standard_input(INPUT_WB_NAME, INPUT_WS_NAME, INPUT_TBL_NAME):

    wb, ws = io.set_xw_book_and_sheet(INPUT_WB_NAME, INPUT_WS_NAME)
    df = io.get_xw_df(ws, INPUT_TBL_NAME, table=True)
    input_dict = df.set_index('Keys')['Values'].to_dict()
    
    wb, ws = io.set_xw_book_and_sheet(input_dict['input workbook name'], input_dict['true/false sheet name'])
    true_false_df = io.get_xw_df(ws, input_dict['true/false table name'], table=True)
    # print(true_false_df)
    
    if 'TRUE/FALSE' not in true_false_df.columns:
        true_false_df = true_false_df.set_index('Keys').T

    true_false_df = true_false_df[true_false_df['TRUE/FALSE'] == True]
    
    wb, ws = io.set_xw_book_and_sheet(database_wb, database_ws)
    tbl = database_tbl
    db_df = io.get_xw_df(ws, tbl, table=True)
    # print(db_df)
    
    merged_df = true_false_df.merge(db_df,how='left',on=['my_fi_name', 'my_pf_name'])
    # print(merged_df)

    fin_inst_objs_list = make_single_leg_fin_insts(merged_df)

    return input_dict, fin_inst_objs_list


async def standard_output(input_dict, output_list, OUTPUT_COLS, FLATTEN_COLS=[]):
    
    refresh      = input_dict.get('timer interval', 10)
    display_mode = input_dict.get('display df onscreen', False)
    csv_mode     = input_dict.get('save df to csv', False)
    xl_mode      = input_dict.get('send df to xl', False)
    print_ts     = input_dict.get('print timestamp onscreen', False)
    add_ts       = input_dict.get('add timestamp to output df', False)

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

    