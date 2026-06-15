
from fin_insts.parents.Class_FI import FinancialInstrument
from fin_insts.parents.Class_FI_Dates import Dates

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

        if self.my_pf_name == "Coinbase-Derivs":
            row = self.fi_row
            expiration_dt_utc = datetime.fromisoformat(row.future_product_details_contract_expiry.replace("Z", "+00:00"))
            self.tz_exch = ZoneInfo(row.future_product_details_contract_expiry_timezone or "UTC")

            expiration_dt_exch = expiration_dt_utc.astimezone(self.tz_exch)
            self.date_expiry = expiration_dt_exch.date()
            self.last_trade_time = expiration_dt_exch.time()

        date_expiry_pmt               = self.date_expiry + timedelta(days=self.biz_days_to_expiry_pmt)
        self.date_settle_expiry       = Dates.next_nyse_trading_day(date_expiry_pmt)
        self.days_settle_expiry       = (self.date_settle_expiry - self.date_trade).days

        if self.last_trade_time is None:
            self.last_trade_time      = Dates.time_from_string('16:00')
        last_trade_date_time_exch     = datetime.combine(self.date_expiry, self.last_trade_time, tzinfo=self.tz_exch)   
        tz_nyc                        = ZoneInfo("America/New_York")
        self.last_trade_date_time_nyc = last_trade_date_time_exch.astimezone(tz_nyc)
