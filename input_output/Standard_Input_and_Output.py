
import os
import asyncio
from datetime import datetime
import pandas as pd
from zoneinfo import ZoneInfo
# from IPython.display import display, clear_output

# import xlwings as xw

from fin_insts.Make_Single_Leg_Fin_Insts import make_single_leg_fin_insts
# from fin_insts import FutureSpread, Synthetic, BestOf

from input_output.Class_InputOutput import InputOutput
io = InputOutput()


def make_objs_list(ws, range, table=True):
    df = io.get_xw_df(ws, range, table)
    #  print(active_fi_df)

    if 'TRUE/FALSE' not in df.columns:
        df = df.set_index('Keys').T

    df = df[df['TRUE/FALSE'] == True]
    # print(df)
    
    obj_list = make_single_leg_fin_insts(df)

    return obj_list


def standard_input(wb_name, ws_name, range, table=True, style=float):
    wb, ws = io.set_xw_book_and_sheet(wb_name, ws_name)

    input_dict = io.get_xw_dict(ws, range, table, style)
    # print(input_dict)

    ws = io.set_xw_sheet(wb, input_dict['true/false sheet name'])

    obj_list = make_objs_list(ws, input_dict['true/false table name'], table)

    return input_dict, obj_list


async def standard_output(input_dict, output_list, OUTPUT_COLS, FLATTEN_COLS=[]):
    # needs async because of the two await asyncio.sleep commands below 
    
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
        
        #for obj in output_list:
         #   for item in obj:
          #      print(vars(item), '\n')


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
            # clear_output(wait=True)
            # display(df)
            print(df)
            
        if csv_mode:
            if csv_mode == 'append':
                current_df.to_csv(path, mode='a', header=not os.path.exists(path), index=False)
            else:
                current_df.to_csv(path, index=False)

        if xl_mode:
            df = history_df if xl_mode == 'append' else current_df
            cell.options(index=False, header=True).value = df
        
        await asyncio.sleep(refresh)

    