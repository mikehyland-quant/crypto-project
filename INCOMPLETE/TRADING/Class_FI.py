#!/usr/bin/env python
# coding: utf-8

# In[1]:


#imports
from   datetime import datetime, timezone, timedelta, date
from   dateutil import parser
import numpy    as np
import pandas   as pd
from   pandas.tseries.offsets import BDay
import pytz #for time zones

#self-written shortcuts
from Methods_Core import *


# In[3]:


class Financial_Instrument():
    
    def __init__(self, tempDict):  
                
        #general information            
        self.product_type             = tempDict['product_type']
        self.platform                 = tempDict['platform']
        self.exch_name                = tempDict['exch_name']
        self.symbol                   = tempDict['symbol']
        
        self.instrument_name          = tempDict['instrument_name']
        self.object_name              = self.instrument_name.replace("-","_")
        
        self.commission_type          = tempDict['commission_type']  
        self.comm_maker               = tempDict['comm_maker']  
        self.comm_taker               = tempDict['comm_taker']  
        self.current_position         = 0
        
        
        #price information
        self.mkt_price                = {"scalar"        : float(tempDict['mkt_price_scalar']),     
                                         "bid_raw"       : 0,    "ask_raw"       : None, 
                                         "bid"           : 0,    "ask"           : None, 
                                         "close_raw"     : None, "close"         : None,
                                         "strike"        : None} 
        
        self.unit_price               = {"scalar"        : float(tempDict['unit_price_scalar']),     
                                         "bid"           : 0,    "ask"           : None, 
                                         "close"         : None,
                                         "strike"        : None} 
                 
        self.unit_cf                  = {"hit_bid"       : 0,    "lift_ask"      : None, 
                                         "hit_bid_comm"  : None, "lift_ask_comm" : None,
                                         "join_bid"      : 0,    "join_ask"      : None, 
                                         "join_bid_comm" : None, "join_ask_comm" : None} 
         
        self.mkt_size                 = {"scalar"        : float(tempDict['mkt_size_scalar']),
                                         "bid_raw"       : None, "ask_raw"       : None,
                                         "bid"           : None, "ask"           : None,
                                         "volume"        : None, "avg_volume"    : None}    
               
        self.unit_size                = {"scalar"        : float(tempDict['unit_size_scalar']),
                                         "bid"           : None, "ask"           : None,
                                         "volume"        : None, "avg_volume"    : None}    
                
        self.cf_date                  = {0 : None, #for commission
                                         1 : None,
                                         2 : None}
        
        self.whole_days_to_cf         = {0 : None, #for commission
                                         1 : None,
                                         2 : None}
        
        
        #expiration information (for options and futures)    
        self.expiration               = {"date_expires"   : None,
                                         "time_expires"   : None, 
                                         "expiry"         : None,         
                                         "yrs_to_expiry"  : None,
                                         "days_to_expiry" : None #every product needs for sorting purposes
                                        }        
        
#platform specific information                                
        if self.platform == "WS":            
            self.streaming_url     = tempDict['streaming_URL']            
            self.connection_string = tempDict['connection_string']
            self.dump_string       = tempDict['dump_string']
            self.num_subs_msgs     = tempDict['numSubsMsgs']
            
            self.price_method      = tempDict['price_method']
            self.bid_side_name     = tempDict['bid_side_name']
            self.ask_side_name     = tempDict['ask_side_name']            
            self.bid_size_name     = tempDict['bid_size_name'] 
            self.bid_price_name    = tempDict['bid_price_name']
            self.ask_price_name    = tempDict['ask_price_name']
            self.ask_size_name     = tempDict['ask_size_name']
        
        
        elif self.platform == "IBKR":    
            self.ibkr_type         = tempDict['ibkr_type'].upper()
            self.ibkr_contractID   = tempDict['ibkr_conID']
            self.ibkr_expiry       = np.nan
            self.ibkr_ticker_id    = np.nan
            self.ibkr_object       = np.nan
                       
                
    def calc_sizes (self, amount, bidAsk):
        bidAskList = getBidAskList(bidAsk)
        for action in bidAskList:
            self.mkt_size  [action + '_raw'] = float(amount)
            self.mkt_size  [action]          = self.mkt_size [action + '_raw'] * self.mkt_size ['scalar']
            self.unit_size [action]          = self.mkt_size [action]          * self.unit_size['scalar']

            
    def calc_prices(self, amount, bidAsk):
        bidAskList = getBidAskList(bidAsk)
        for action in bidAskList:
            self.mkt_price [action + '_raw'] = float(amount)
            self.mkt_price [action]          = self.mkt_price[action + '_raw'] * self.mkt_price ['scalar']
            self.unit_price[action]          = self.mkt_price[action]          * self.unit_price['scalar']
                                        
                
    def calc_cashflows(self, bidAsk): 
        actionsDict     = {'bid' : ['hit_', 'join_'], 'ask' : ['lift_', 'join_']}
        cfDirectionDict = {'hit_bid' : 1, 'join_bid': -1, 'lift_ask' : -1, 'join_ask': 1}
        commissionDict  = {'hit_bid' :  'taker',  'join_bid': 'maker', 
                           'lift_ask' : 'taker', 'join_ask': 'maker'}
                           
        bidAskList = getBidAskList(bidAsk)
        for action in bidAskList:
            for hitLiftJoin in actionsDict[action]:
                order = hitLiftJoin + action
                self.unit_cf[order] = self.unit_price[action] * cfDirectionDict[order]
                self.unit_cf[order + '_comm'] = -float(calc_comm_cf(self, order)) / self.unit_size['scalar']
                    


# In[4]:


def calc_date(dateString): 
    if dateString != "NONE":
        answer = parser.parse(dateString)
        answer = answer.date()
    else:
        answer = "NONE"
    return answer


def calc_expiry(date_expires, time_expires):
    expiryTime = datetime.strptime(time_expires.split()[0], '%H:%M').time()
    expiry     = datetime.combine(date_expires, expiryTime)  

    timeZone   = time_expires.split()[1]        
    if timeZone == "LONDON":
        tz = pytz.timezone('Europe/London')
    else:
        tz = pytz.timezone('America/New_York')
    expiry = tz.localize(expiry)

    tzNY = pytz.timezone('America/New_York')        
    return expiry.astimezone(tzNY)


def calc_time_diff(date_in_question, daysYrs):
    tzNY = pytz.timezone('America/New_York')

    now = datetime.now()        
    now = tzNY.localize(now)

    diff = date_in_question - now

    if daysYrs == "days":
        return diff / pd.Timedelta(days=1)
    else:
        return diff / pd.Timedelta(days=365)

    
def calc_whole_days_diff(date_in_question):
    diff = date_in_question - date.today()
    return diff.days


def calc_ibkr_expiry(rawDate):
    day   = double_digit(rawDate.day)
    month = double_digit(rawDate.month)
    
    returnDate = str(rawDate.year) + month + day

    return returnDate


def double_digit(rawData):
    returnData = str(rawData)
    
    if rawData < 10:
        returnData = str(0) + returnData
        
    return returnData


# In[ ]:


def calc_comm_cf(self, action): 
    bidAsk = action[-3:]
    
    if action[:4] == 'join':
        makerTaker = 'maker'
    else:
        makerTaker = 'taker'

    if   self.commission_type == 'flat':
        commission = getattr(self, 'comm_' + makerTaker) 
    elif self.commission_type == 'percentage':
        commission = getattr(self, 'comm_' + makerTaker) * self.mkt_price[bidAsk]
    elif self.commission_type == 'flatWithCap':
        calc_commission_flat_with_pct_cap(self, bidAsk, makerTaker)
        
    return commission
            
        

           
def calc_commission_flat_with_pct_cap(self, bidAsk):
    calc_commission_flat(self, bidAsk)
 
    if bidAsk == 'bid' or bidAsk == 'both':
        if not np.isnan(mkt_price["bid"]) and mkt_price["bid"] >= 0:
            commCap                    = self.mkt_price["bid"] * self.comm_cap
            self.mkt_price["bid_comm"] = max(self.mkt_price["bid_comm"], commCap)
        else:
            self.mkt_price["bid_comm"] = np.nan  
    
    if bidAsk == 'ask' or bidAsk == 'both':
        if not np.isnan(mkt_price["ask"]) and mkt_price["ask"] >= 0:
            commCap                    = self.mkt_price["ask"] * self.comm_cap
            self.mkt_price["ask_comm"] = max(self.mkt_price["ask_comm"], commCap)
        else:
            self.mkt_price["ask_comm"] = np.nan  

