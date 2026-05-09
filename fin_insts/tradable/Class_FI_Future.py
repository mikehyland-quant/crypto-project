#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from fin_insts.parents.Class_FI import FinancialInstrument
from fin_insts.parents.Class_FI_Dates import Dates
from fin_insts.parents.Class_FI_MktData import MktData

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas_market_calendars as mcal
_NYSE = mcal.get_calendar("NYSE")   # module-level, built once

# In[ ]:

'''
Adds the following attributes: self.date_expire / self.date_expiry_settle / self.days_expiry_settle / self.last_trade_date_time_nyc
'''

class Future(FinancialInstrument):
    """
    Future instrument class (child of FinancialInstrument).
    """
    def __init__(self, row):
        super().__init__(row)
        
        self.settlement_days_trade  = 0
        self.settlement_days_comm   = 0
        self.settlement_days_expiry = 0

    def complete_obj(self):
        super().complete_obj() 
        
        if self.my_pf_name == 'IBKR':
            expiration_date  = Dates.date_from_string(self.ibkr_details.realExpirationDate) 
            last_trade_time  = Dates.time_from_number(self.ibkr_details.lastTradeTime, 24)
            tz_exch          = ZoneInfo(self.ibkr_details.timeZoneId or "US/Central")
                
        self.date_expiry              = expiration_date
        date_expiry_pmt               = expiration_date + timedelta(days=self.settlement_days_expiry)
        self.date_expiry_settle       = Dates.next_nyse_trading_day(date_expiry_pmt)
        self.days_expiry_settle       = (self.date_expiry_settle - self.date_trade).days

        if last_trade_time is None:
            last_trade_time           = Dates.time_from_string('16:00')
        last_trade_date_time_exch     = datetime.combine(expiration_date, last_trade_time, tzinfo=tz_exch)   
        tz_nyc                        = ZoneInfo("America/New_York")
        self.last_trade_date_time_nyc = last_trade_date_time_exch.astimezone(tz_nyc)


        