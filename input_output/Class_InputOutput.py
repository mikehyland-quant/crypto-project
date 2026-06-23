
#imports
import os
import pandas as pd
import xlwings as xw

class InputOutput():

    def __init__(self):
        pass


    # xlWings shortcuts

    def set_xw_book(self, wb_name):
        return xw.Book(wb_name)

    def set_xw_sheet(self, wb, ws_name):
        return wb.sheets(ws_name)
    
    def set_xw_range(self, ws, range_name):
        return ws.range(range_name)

    def set_xw_book_and_sheet(self, wb_name, ws_name):
        wb = self.set_xw_book(wb_name)
        ws = self.set_xw_sheet(wb, ws_name)
        return wb, ws
    
    def set_xw_sheet_and_range(self, wb, ws_name, range_name):
        ws    = self.set_xw_sheet(wb, ws_name)
        range = self.set_xw_range(ws, range_name)
        return ws, range
    
    def set_xw_book_sheet_and_range(self, wb_name, ws_name, range_name):
        wb, ws = self.set_xw_book_and_sheet(wb_name, ws_name)
        range  = self.set_xw_range(ws, range_name)
        return wb, ws, range
    
    def get_xw_range(self, ws, range_name):
        return ws.range(range_name).value

    def get_xw_dict(self, ws, range, table=False, style=float):  
        if table == False:
            return ws.range(range).options(dict, numbers=style).value
        else:
            tbl = ws.tables[range]
            tbl_range = tbl.range
            return tbl_range.options(dict, numbers=style).value
        
    def get_xw_df(self, ws, range, table=False, headerRows=1, style=float):    
        if table == False:
            return ws.range(range).options(pd.DataFrame, index = False, numbers=style, header=int(headerRows)).value
        else:
            tbl = ws.tables[range]
            tbl_range = tbl.range
            return tbl_range.options(pd.DataFrame, index=False).value

    def print_xw_df(self, range, df, headerRows=1):       
        range(range).options(index = False, header=headerRows).value = df


    # additional shortcuts  

    def convert_objs_to_printable_df(self, list_, OUTPUT_COLS, FLATTEN_COLS=[]):
        df = self.objs_list_to_df(list_)
        for col in FLATTEN_COLS:
            df = self.flatten_df_columns(df, col, sep='_')
        df = df.reindex(columns=OUTPUT_COLS)
        return df
        
    def objs_list_to_df(self, list_of_objs):
        return pd.DataFrame([obj.__dict__ for obj in list_of_objs])
        
    def objs_dict_to_df(self, dict_of_objs):
        return pd.DataFrame([vars(obj) for obj in dict_of_objs.values()])

    def flatten_df_columns(self, df, col_name, sep='_'):
        """
        Flatten a column of dictionaries (including nested dicts) into separate columns.
        """    
        # safe_series works with obj or dict
        # also replaces NaN/None with empty dict so json_normalize doesn't choke
        # safe_series = df[col_name].apply(lambda x: x if isinstance(x, dict) else {})
        safe_series = df[col_name].apply(lambda x: (vars(x) if hasattr(x, "__dict__") 
                                                    else x if isinstance(x, dict)
                                                    else {}))

        flattened = pd.json_normalize(safe_series, sep=sep)

        # Prefix columns to avoid name collisions
        flattened.columns = [f"{col_name}{sep}{c}" for c in flattened.columns]

        # Join back to original df
        df = df.drop(columns=[col_name]).join(flattened)

        return df

    def list_unprintable_columns(self, df):
        bad_type_list = (list, tuple, set, dict)
        bad_cols      = df.map(lambda x: isinstance(x, bad_type_list))
        print(df.columns[bad_cols.any()])

    def save_df_to_csv(self, df, directory, filename):
        path = os.path.normpath(os.path.join(directory, filename))
        df.to_csv(path, index=False)




