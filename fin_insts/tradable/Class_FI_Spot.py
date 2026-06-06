#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from fin_insts.parents.Class_FI import FinancialInstrument
from fin_insts.parents.Class_FI_Dates import Dates
from fin_insts.parents.Class_FI_MktData import MktData


# In[ ]:

 
class Spot(FinancialInstrument):
    """
    Spot instrument class (child of FinancialInstrument).
    """
    def __init__(self, row):
        super().__init__(row)
        
        self.biz_days_to_comm_pmt  = 0
        self.biz_days_to_trade_pmt = 0
        

        


        