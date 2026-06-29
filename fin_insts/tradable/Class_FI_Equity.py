
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

        self.scalar_size_FIs_per_unit    = self.get_scalar()
        self.scalar_size_units_per_FI    = 1 / self.scalar_size_FIs_per_unit

        self.scalar_size_orders_per_unit = self.scalar_size_FIs_per_unit / self.scalar_size_FIs_per_order
        self.scalar_size_units_per_order = self.scalar_size_FIs_per_order / self.scalar_size_FIs_per_unit


    def get_scalar(self):
        from input_output.Class_InputOutput import InputOutput
        io = InputOutput()

        wb, ws = io.set_xw_book_and_sheet('2026 BTC ETF Ratios.xlsx', 'BTC RATIOS')
        df = io.get_xw_df(ws, 'btc_ratios', table=True)
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        exp_date = self.date_settle_trade
        scalar = self._safe_float(df.loc[df['Date'] == exp_date, self.my_fi_name].to_list()[0])
        return scalar
        
 
        