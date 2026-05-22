


#imports
from datetime import datetime, time, timedelta, date
from dateutil import parser
from zoneinfo import ZoneInfo

import numbers

import pandas_market_calendars as mcal
_NYSE = mcal.get_calendar("NYSE")   # module-level, built once


class Dates():
    """
    Build date-related fields for a simple instrument without mutating it.
    """
    '''
    called for simple contracts (not BAGs) from 
    Class_IBKRClient at 
    async def create_simple_contract(self, obj):
    '''

    @staticmethod
    def calc(obj):  

        trade_date            = date.today()

        date_comm_pmt         = trade_date + timedelta(days=obj.biz_days_to_comm_pmt)
        settlement_date_comm  = Dates.next_nyse_trading_day(date_comm_pmt)

        time_diff             = obj.biz_days_to_trade_pmt - obj.biz_days_to_comm_pmt
        date_trade_pmt        = settlement_date_comm + timedelta(days=time_diff)
        settlement_date_trade = Dates.next_nyse_trading_day(date_trade_pmt)

        calendar_days_comm    = (settlement_date_comm  - trade_date).days
        calendar_days_trade   = (settlement_date_trade - trade_date).days
        
        return {
            'trade_date'            : trade_date,
            'settlement_date_comm'  : settlement_date_comm,
            'settlement_date_trade' : settlement_date_trade,
            'calendar_days_comm'    : calendar_days_comm,
            'calendar_days_trade'   : calendar_days_trade
        }


    @staticmethod
    def calc_and_attach(obj):        
        results_dict = Dates.calc(obj)

        obj.date_trade        = results_dict['trade_date']    
        obj.date_settle_comm  = results_dict['settlement_date_comm'] 
        obj.date_settle_trade = results_dict['settlement_date_trade'] 
        obj.days_settle_comm  = results_dict['calendar_days_comm'] 
        obj.days_settle_trade = results_dict['calendar_days_trade'] 

    
    @staticmethod
    def date_from_string(date_string): 
        if isinstance(date_string, str) and date_string.strip():
            answer = parser.parse(date_string)
            return answer.date()
        else:
            return None


    @staticmethod
    def time_from_string(time_string):
        if isinstance(time_string, str) and time_string.strip():
            h, m = map(int, time_string.split(":"))
            return time(hour=h, minute=m)
        else:
            return None


    @staticmethod
    def time_from_number(time_number, multiplier=1): 
        if isinstance(time_number, numbers.Real):
            product =  time_number * multiplier            
            hours = int(product) % 24
            minutes = int(round((product - int(product)) * 60))

            # handle rounding edge case (e.g. 1.999 -> 2:00)
            if minutes == 60:
                hours = (hours + 1) % 24
                minutes = 0

            return time(hour=hours, minute=minutes)        
        else:
            return None


    @staticmethod
    def next_nyse_trading_day(date_):
        if date_ is not None:
            schedule = _NYSE.valid_days(start_date=date_, end_date=date_ + timedelta(days=10))
            return schedule[schedule.date >= date_].min().date()
        return None            
