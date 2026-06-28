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

        self.scalar_price_raw_to_screen = 1 
        self.scalar_size_raw_to_screen  = 1  

        self.scalar_selfs_per_unit   = 1 
        self.scalar_order_multiplier = 1 

        # the next two lines are calculated as part of complete object
        # self.scalar_screens_per_unit  = self.scalar_selfs_per_unit / self.scalar_order_multiplier
        # self.scalar_units_per_screen  = self.scalar_order_multiplier / self.scalar_selfs_per_unit

        self.need_to_update_mkt_data    = False
        self.need_to_save_closing_price = True
        
        self.price_raw_close    = np.nan
        self.price_screen_close = np.nan
        self.price_unit_close   = np.nan
               
        for bid_ask in ['bid', 'ask']:
            setattr(self, 'price_raw_'    + bid_ask, np.nan)     
            setattr(self, 'price_screen_' + bid_ask, np.nan)       
            setattr(self, 'price_unit_'   + bid_ask, np.nan)    

            setattr(self, 'size_raw_'     + bid_ask, np.nan) 
            setattr(self, 'size_screen_'  + bid_ask, np.nan)               
            setattr(self, 'size_unit_'    + bid_ask, np.nan)    

        for bid_ask in ['hit_bid', 'join_bid', 'join_ask', 'lift_ask']:   
            setattr(self, 'cf_mkt_'      + bid_ask, np.nan)        
            setattr(self, 'cf_unit_'     + bid_ask, np.nan)  
            
            setattr(self, 'comm_mkt_'    + bid_ask, np.nan)        
            setattr(self, 'comm_unit_'   + bid_ask, np.nan)
        
             
    @staticmethod
    def _safe_float(x, default=np.nan):
        try:
            return float(x)
        except (TypeError, ValueError):
            return default
        

    def is_mkt_data_valid(self):
        bid = self.price_screen_bid
        ask = self.price_screen_ask
        b_sz = self.size_screen_bid
        a_sz = self.size_screen_ask
        return (pd.notna(bid) and pd.notna(ask) and pd.notna(b_sz) and pd.notna(a_sz) and bid < ask)
       
 
    def on_mkt_data_update(self, bid_price=np.nan, ask_price=np.nan, bid_size=np.nan, ask_size=np.nan): 
        changed = self.update_mkt_data(bid_price=bid_price, ask_price=ask_price, bid_size=bid_size, ask_size=ask_size) 
            #self.update_mkt_data() is overwritten in strategy classes to update additional attributes when necessary

        if not changed:
             return 
               
        for subscriber in self.subscribers:
            subscriber.update_subscriber_data(self)

        strategy = getattr(self, "strategy", None)
        if strategy is not None and getattr(self, "strat_on_mkt_data_update", False):
            strategy.on_mkt_data_update(self)


    def update_mkt_data(self, bid_price=np.nan, ask_price=np.nan, bid_size=np.nan, ask_size=np.nan):        
        changed = False
        ts = np.nan
    
        bid_price = self._safe_float(bid_price, default=np.nan)
        ask_price = self._safe_float(ask_price, default=np.nan)
        bid_size  = self._safe_float(bid_size,  default=np.nan)
        ask_size  = self._safe_float(ask_size,  default=np.nan)

        # print(bid_price, ask_price, bid_size, ask_size)

        if pd.notna(bid_price) and bid_price != self.price_raw_bid:
            changed = True
            
            if pd.isna(ts):
                ts = time.time_ns()
            self.ts_price_bid = ts
                    
            self.price_raw_bid        =  bid_price
            self.price_screen_bid     =  self.price_raw_bid    * self.scalar_price_raw_to_screen    
            self.price_order_bid      =  self.price_screen_bid * self.scalar_order_multiplier
            self.price_unit_bid       =  self.price_order_bid  * self.scalar_screens_per_unit

            self.cf_order_join_bid    = -self.price_order_bid 
            self.cf_order_hit_bid     =  self.price_order_bid 

            self.cf_unit_join_bid     = -self.price_unit_bid 
            self.cf_unit_hit_bid      =  self.price_unit_bid 

            self.comm_order_join_bid  =  self.calc_comm(self.price_screen_bid, 'maker')
            self.comm_order_hit_bid   =  self.calc_comm(self.price_screen_bid, 'taker')
    
            self.comm_unit_join_bid   =  self.comm_order_join_bid * self.scalar_screens_per_unit
            self.comm_unit_hit_bid    =  self.comm_order_hit_bid  * self.scalar_screens_per_unit
    
        if pd.notna(ask_price) and ask_price != self.price_raw_ask:
            changed = True
            
            if pd.isna(ts):
                ts = time.time_ns()
            self.ts_price_ask = ts
                     
            self.price_raw_ask        =  ask_price
            self.price_screen_ask     =  self.price_raw_ask    * self.scalar_price_raw_to_screen    
            self.price_order_ask      =  self.price_screen_ask * self.scalar_order_multiplier
            self.price_unit_ask       =  self.price_order_ask  * self.scalar_screens_per_unit

            self.cf_order_join_ask    =  self.price_order_ask 
            self.cf_order_lift_ask    = -self.price_order_ask 

            self.cf_unit_join_ask     =  self.price_unit_ask 
            self.cf_unit_lift_ask     = -self.price_unit_ask 

            self.comm_order_join_ask  =  self.calc_comm(self.price_screen_ask, 'maker')
            self.comm_order_lift_ask  =  self.calc_comm(self.price_screen_ask, 'taker')
    
            self.comm_unit_join_ask   =  self.comm_order_join_ask * self.scalar_screens_per_unit
            self.comm_unit_lift_ask   =  self.comm_order_lift_ask * self.scalar_screens_per_unit

        if pd.notna(bid_size) and bid_size != self.size_raw_bid:
            changed = True
             
            if pd.isna(ts):
                ts = time.time_ns()
            self.ts_size_bid = ts
                    
            self.size_raw_bid    =  bid_size    
            self.size_screen_bid =  self.size_raw_bid    * self.scalar_size_raw_to_screen
            self.size_unit_bid   =  self.size_screen_bid * self.scalar_units_per_screen  

        if pd.notna(ask_size) and ask_size != self.size_raw_ask:
            changed = True
            
            if pd.isna(ts):
                ts = time.time_ns()
            self.ts_size_ask = ts
            
            self.size_raw_ask    =  ask_size    
            self.size_screen_ask =  self.size_raw_ask    * self.scalar_size_raw_to_screen
            self.size_unit_ask   =  self.size_screen_ask * self.scalar_units_per_screen
    
        # print(self.price_unit_ask, self.price_unit_bid, self.size_unit_bid, self.size_unit_ask)

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
        

    def on_close_update(self, close_price=np.nan):
        close_price = self._safe_float(close_price, default=np.nan)
        if close_price is not None and not np.nan:
            self.price_raw_close    = close_price 

            self.price_screen_close = self.price_raw_close    * self.scalar_price_raw_to_screen
            self.price_unit_close   = self.price_screen_close * self.scalar_screens_per_unit

            strategy = getattr(self, "strategy", np.nan)
            if getattr(self, "strat_on_close_update", False):  
                strategy.on_close_uodate(self)

            self.need_to_update_mkt_data     = True
            self.need_to_save_closing_price  = False



    


    