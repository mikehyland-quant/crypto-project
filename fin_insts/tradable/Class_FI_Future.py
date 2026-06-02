


from fin_insts.parents.Class_FI import FinancialInstrument
from fin_insts.parents.Class_FI_Dates import Dates
from fin_insts.parents.Class_FI_MktData import MktData

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas_market_calendars as mcal
_NYSE = mcal.get_calendar("NYSE")   # module-level, built once


'''
Adds the following attributes: self.date_expire / self.date_expiry_settle / self.days_expiry_settle / self.last_trade_date_time_nyc
'''

class Future(FinancialInstrument):
    """
    Future instrument class (child of FinancialInstrument).
    """
    def __init__(self, row):
        super().__init__(row)
        
        self.biz_days_to_comm_pmt  = 0
        self.biz_days_to_trade_pmt = 0
        self.biz_days_to_expiry_pmt  = 0
    
    def complete_obj(self):
        super().complete_obj() 
        
        if self.my_pf_name == 'IBKR':
            expiration_date  = Dates.date_from_string(self.ibkr_details.realExpirationDate) 
            last_trade_time  = Dates.time_from_number(self.ibkr_details.lastTradeTime, 24)
            tz_exch          = ZoneInfo(self.ibkr_details.timeZoneId or "US/Central")

        elif self.my_pf_name == "Coinbase-Derivs":
            row = self.fi_row
            expiration_dt_utc = datetime.fromisoformat(row.future_product_details_contract_expiry.replace("Z", "+00:00"))
            tz_exch = ZoneInfo(row.future_product_details_contract_expiry_timezone or "UTC")

            expiration_dt_exch = expiration_dt_utc.astimezone(tz_exch)
            expiration_date = expiration_dt_exch.date()
            last_trade_time = expiration_dt_exch.time()
            
        self.date_expiry              = expiration_date
        date_expiry_pmt               = expiration_date + timedelta(days=self.biz_days_to_expiry_pmt)
        self.date_settle_expiry       = Dates.next_nyse_trading_day(date_expiry_pmt)
        self.days_settle_expiry       = (self.date_settle_expiry - self.date_trade).days

        if last_trade_time is None:
            last_trade_time           = Dates.time_from_string('16:00')
        last_trade_date_time_exch     = datetime.combine(expiration_date, last_trade_time, tzinfo=tz_exch)   
        tz_nyc                        = ZoneInfo("America/New_York")
        self.last_trade_date_time_nyc = last_trade_date_time_exch.astimezone(tz_nyc)


        