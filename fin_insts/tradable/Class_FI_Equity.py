#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd

from fin_insts.parents.Class_FI import FinancialInstrument
from fin_insts.parents.Class_FI_Dates import Dates
from fin_insts.parents.Class_FI_MktData import MktData

from input_output.Class_InputOutput import InputOutput
io = InputOutput()


# In[ ]:


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
        
        self.scalar_price_mkt_to_unit = self.get_scalar()
        self.scalar_price_unit_to_mkt = 1 / self.scalar_price_mkt_to_unit

        self.scalar_size_mkt_per_unit = self.scalar_price_mkt_to_unit
        self.scalar_size_unit_per_mkt = 1 / self.scalar_size_mkt_per_unit

        # the two lines below overwrite IBKR sizes of 0.0001
        self.size_increment = 1
        self.min_size       = 1
 
        # the line below overwrites MktData assignment of 1
        self.scalar_size_raw_to_mkt = 100

    def get_scalar(self):

        wb, ws = io.set_xw_book_and_sheet('2026 BTC ETF Ratios.xlsx', 'BTC RATIOS')
        df = io.get_xw_df(ws, 'btc_ratios', table=True)
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        exp_date = self.date_settle_trade
        scalar = self._safe_float(df.loc[df['Date'] == exp_date, self.my_fi_name].to_list()[0])
        return scalar
        
 
        