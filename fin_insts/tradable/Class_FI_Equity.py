
from fin_insts.parents.Class_FI import FinancialInstrument

import pandas as pd


class Equity(FinancialInstrument):
    """
    Equity instrument class (child of FinancialInstrument).
    """
    def __init__(self, row):
        super().__init__(row)
        
        self.biz_days_to_comm_pmt  = 1
        self.biz_days_to_trade_pmt = 1
         
    def complete_obj(self): 
        super().complete_obj() 

        # the two lines below overwrite IBKR sizes of 0.0001
        self.size_increment = 1
        self.min_size       = 1
        
        # overwrite previous entries and reattach scalars
        self.scalar_size_raw_to_screen   = 100

        self.scalar_size_FIs_per_unit    = self.get_scalar_crypto()
        self.scalar_size_units_per_FI    = 1 / self.scalar_size_FIs_per_unit

        self.scalar_size_orders_per_unit = self.scalar_size_FIs_per_unit / self.scalar_size_FIs_per_order
        self.scalar_size_units_per_order = self.scalar_size_FIs_per_order / self.scalar_size_FIs_per_unit


    def get_scalar_crypto(self):
        from input_output.Class_InputOutput import InputOutput
        io = InputOutput()

        wb, ws = io.set_xw_book_and_sheet('2026 BTC ETF Ratios.xlsx', 'SCALARS')
        df = io.get_xw_df(ws, 'scalars', table=True)
        
        if self.my_fi_name not in df.columns:
            return 1
        
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        exp_date = self.date_settle_trade
        scalar = self._safe_float(df.loc[df['Date'] == exp_date, self.my_fi_name].to_list()[0])
        return scalar
        
    def get_scalar_stat_arb(self):
        from input_output.Class_InputOutput import InputOutput
        io = InputOutput()

        wb, ws = io.set_xw_book_and_sheet('2026 Stat Arb Mkt Data.xlsx', 'SCALARS')
        df = io.get_xw_df(ws, 'scalars', table=True)
        df = df.T
        
        # df['Date'] = pd.to_datetime(df['Date']).dt.date
        # exp_date = self.date_settle_trade
        scalar = self._safe_float(df.loc["ratios", self.my_fi_name].to_list()[0])
        return scalar
    
    def get_scalar(self):
        from input_output.Class_InputOutput import InputOutput
        io = InputOutput()

        my_fi_name = self.my_fi_name
        family = self.family

        wb_dict = {'Crypto'   : '2026 BTC ETF Ratios.xlsx',
                   "Stat Arb" : '2026 Stat Arb Mkt Data.xlsx'}

        wb_name = wb_dict[family]

        wb, ws = io.set_xw_book_and_sheet(wb_name, 'SCALARS')
        df = io.get_xw_df(ws, 'scalars', table=True)
        
        if my_fi_name not in df.columns:
            df = df.T

        if family == 'Crypto':
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            exp_date = self.date_settle_trade
            row = df.loc[exp_date]

        elif family == 'Stat Arb':
            row = df.loc['ratios']

        scalar = self._safe_float(row[my_fi_name])

        return scalar
        

        
        