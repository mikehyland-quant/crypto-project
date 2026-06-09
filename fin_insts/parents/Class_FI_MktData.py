#!/usr/bin/env python
# coding: utf-8

# In[ ]:

'''
This class assigns a number of attributes to each object.  The attribute names are organized as follows:
    first  - cf / comm / price / size
    second - mkt / raw / unit
    third  - ask / bid / hit_bid / join_ask / join_bid / lift_ask 

For scalars, the first is always "scalar".  Then price / size.  Then raw_to_mkt / mkt_to_unit.
'''


import numpy as np
import pandas as pd
import time

class MktData:
    
    def __init__(self):
        self.subscribers = []
        
        self.need_close_data   = True
        self.price_raw_close   = np.nan
        self.price_mkt_close   = np.nan
        self.price_unit_close  = np.nan
               
        for bid_ask in ['bid', 'ask']:
              
            setattr(self, 'price_raw_'   + bid_ask, np.nan)       
            setattr(self, 'price_mkt_'   + bid_ask, np.nan)        
            setattr(self, 'price_unit_'  + bid_ask, np.nan)    

            setattr(self, 'size_raw_'    + bid_ask, np.nan)   
            setattr(self, 'size_mkt_'    + bid_ask, np.nan)        
            setattr(self, 'size_unit_'   + bid_ask, np.nan)    

        for bid_ask in ['hit_bid', 'join_bid', 'join_ask', 'lift_ask']:   
            setattr(self, 'cf_mkt_'      + bid_ask, np.nan)        
            setattr(self, 'cf_unit_'     + bid_ask, np.nan)  
            
            setattr(self, 'comm_mkt_'    + bid_ask, np.nan)        
            setattr(self, 'comm_unit_'   + bid_ask, np.nan)
            
        # the settings below are initial; they may get overwritten later in complete object phase
        self.scalar_price_raw_to_mkt  = 1
        self.scalar_price_mkt_to_unit = 1
        self.scalar_price_unit_to_mkt = 1
        
        self.scalar_size_raw_to_mkt   = 1
        self.scalar_size_mkt_per_unit = 1
        self.scalar_size_unit_per_mkt = 1

                    
    @staticmethod
    def _safe_float(x, default=np.nan):
        try:
            return float(x)
        except (TypeError, ValueError):
            return default
        

    def is_mkt_data_valid(self):
        bid = self.price_mkt_bid
        ask = self.price_mkt_ask
        b_sz = self.size_mkt_bid
        a_sz = self.size_mkt_ask
        return (pd.notna(bid) and pd.notna(ask) and pd.notna(b_sz) and pd.notna(a_sz) and bid < ask)
       
        
    def on_close_data(self, close_price=np.nan):
        if close_price is not np.nan:
            self.need_close_data  = False

            self.price_raw_close  = self._safe_float(close_price, default=np.nan)
        
            self.price_mkt_close  = self.price_raw_close * self.scalar_price_raw_to_mkt
            self.price_unit_close = self.price_mkt_close * self.scalar_price_mkt_to_unit

            strategy = getattr(self, "strategy", np.nan)
            if getattr(self, "strat_on_close_data", False):  
                strategy.on_close_data(self)

 
    def on_mkt_data(self, bid_price=np.nan, ask_price=np.nan, bid_size=np.nan, ask_size=np.nan): 
        changed = self.update_mkt_data(bid_price=bid_price, ask_price=ask_price, bid_size=bid_size, ask_size=ask_size) 
            #self.update_mkt_data() is overwritten in strategy classes to update additional attributes when necessary

        if not changed:
             return 
              
        for subscriber in self.subscribers:
            subscriber.update_subscriber_data(self)

        strategy = getattr(self, "strategy", None)
        if strategy is not None and getattr(self, "strat_on_mkt_data", False):
            strategy.on_mkt_data(self)


    def update_mkt_data(self, bid_price=np.nan, ask_price=np.nan, bid_size=np.nan, ask_size=np.nan):        
        changed = False
        ts = np.nan
    
        bid_price = self._safe_float(bid_price, default=np.nan)
        ask_price = self._safe_float(ask_price, default=np.nan)
        bid_size  = self._safe_float(bid_size,  default=np.nan)
        ask_size  = self._safe_float(ask_size,  default=np.nan)
        
        if pd.notna(bid_price) and bid_price != self.price_raw_bid:
            changed = True
            
            if pd.isna(ts):
                ts = time.time_ns()
            self.ts_price_bid = ts
                    
            # calc at the instrument level
            self.price_raw_bid        =  bid_price     
            self.price_mkt_bid        =  self.price_raw_bid * self.scalar_price_raw_to_mkt

            self.cf_mkt_join_bid      = -self.price_mkt_bid 
            self.cf_mkt_hit_bid       =  self.price_mkt_bid 

            self.comm_mkt_join_bid    =  self.calc_comm(self.price_mkt_bid, 'maker')
            self.comm_mkt_hit_bid     =  self.calc_comm(self.price_mkt_bid, 'taker')

            # calc at the unit level
            self.price_unit_bid       =  self.price_mkt_bid * self.scalar_price_mkt_to_unit

            self.cf_unit_join_bid     = -self.price_unit_bid 
            self.cf_unit_hit_bid      =  self.price_unit_bid 
    
            self.comm_unit_join_bid   =  self.comm_mkt_join_bid * self.scalar_size_mkt_per_unit
            self.comm_unit_hit_bid    =  self.comm_mkt_hit_bid  * self.scalar_size_mkt_per_unit
    
        if pd.notna(ask_price) and ask_price != self.price_raw_ask:
            changed = True
            
            if pd.isna(ts):
                ts = time.time_ns()
            self.ts_price_ask = ts
                    
            # calc at the instrument level
            self.price_raw_ask        =  ask_price     
            self.price_mkt_ask        =  self.price_raw_ask * self.scalar_price_raw_to_mkt

            self.cf_mkt_join_ask      =  self.price_mkt_ask 
            self.cf_mkt_lift_ask      = -self.price_mkt_ask 

            self.comm_mkt_join_ask    =  self.calc_comm(self.price_mkt_ask, 'maker')
            self.comm_mkt_lift_ask    =  self.calc_comm(self.price_mkt_ask, 'taker')

            # calc at the unit level
            self.price_unit_ask       =  self.price_mkt_ask * self.scalar_price_mkt_to_unit
    
            self.cf_unit_join_ask     =  self.price_unit_ask 
            self.cf_unit_lift_ask     = -self.price_unit_ask 
    
            self.comm_unit_join_ask   =  self.comm_mkt_join_ask * self.scalar_size_mkt_per_unit
            self.comm_unit_lift_ask   =  self.comm_mkt_lift_ask * self.scalar_size_mkt_per_unit
 
        if pd.notna(bid_size) and bid_size != self.size_raw_bid:
            changed = True
             
            if pd.isna(ts):
                ts = time.time_ns()
            self.ts_size_bid = ts
                    
            self.size_raw_bid   =  bid_size     
            self.size_mkt_bid   =  self.size_raw_bid * self.scalar_size_raw_to_mkt
            self.size_unit_bid  =  self.size_mkt_bid * self.scalar_size_unit_per_mkt
              
        if pd.notna(ask_size) and ask_size != self.size_raw_ask:
            changed = True
            
            if pd.isna(ts):
                ts = time.time_ns()
            self.ts_size_ask = ts
            
            self.size_raw_ask   =  ask_size     
            self.size_mkt_ask   =  self.size_raw_ask * self.scalar_size_raw_to_mkt
            self.size_unit_ask  =  self.size_mkt_ask * self.scalar_size_unit_per_mkt
    
        return changed
        
    
    def calc_comm(self, price, maker_taker):
        type_ = self.comm_type
        amount = getattr(self, 'comm_' + maker_taker + '_amount')

        if type_ == 'flat_amt':
            return float(amount)
        elif type_ == 'flat_pct':
            return price * amount  
        elif type_ == 'flat_pct_with_min':
            initial_estimate = price * amount
            return max(initial_estimate, self.comm_misc_amount)
        else:
            return 0 


    


    