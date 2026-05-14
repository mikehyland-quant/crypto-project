#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import asyncio
import math
import types
import winsound


from datetime import datetime


class Strategy:
    _RULE_FIELD_MAP = {
        'min_tick': 'minTick',
        'min_size': 'minSize',
        'size_increment': 'sizeIncrement',
    }

    def __init__(self, objs_list=None):
        self.done_event = asyncio.Event()  # needs to be awaited in main() and set at the end of each strategy
        self.print_orders = True  # set to False in main() to disable order printing
        
        self.objs_list = objs_list if objs_list is not None else []
               
        for obj in self.objs_list:
            self._attach_trading_helpers(obj)
            
            obj.strategy             = self

            obj.order_id             = None
            obj.trade_status         = None
            obj.filled               = 0
            obj.remaining            = None
            obj.avg_fill_price       = None
            obj.last_fill_price      = None
            
            obj.strat_on_mkt_data    = True
            obj.strat_on_trade_exec  = True
            obj.strat_on_close_data  = True
        
            
    def on_mkt_data(self, obj):
        pass
        

    def on_trade_exec(self, obj):
        pass


    def on_close_data(self, obj):
        if obj.buy_sell == 'BUY':
            obj.placeholder_price = obj.price_mkt_close * 0.5
        elif obj.buy_sell == 'SELL':
            obj.placeholder_price = obj.price_mkt_close * 2.0

        obj.placeholder_price = obj.round_price_to_tick(abs(obj.placeholder_price)) 

        order_id = self.place_limit_order(obj, obj.placeholder_price, obj.price_mkt_close)

        return order_id         

    @classmethod
    def _attach_trading_helpers(cls, obj):
        obj.my_trading_rules = cls._extract_trading_rules(obj)

        obj.round_price_to_tick = types.MethodType(cls.round_price_to_tick, obj)
        obj.round_size_to_increment = types.MethodType(cls.round_size_to_increment, obj)
        

    @classmethod
    def _extract_trading_rules(cls, obj):
        details = getattr(obj, 'ibkr_details', None)

        for my_key, ibkr_key in cls._RULE_FIELD_MAP.items():
            raw_val = getattr(details, ibkr_key, None) if details is not None else None
            val = obj._safe_float(raw_val, default=1.0)

            if val in (None, 0):
                val = None

            setattr(obj, my_key, val)

    
    @classmethod    
    def play_fill_sound(self):
        winsound.PlaySound(
            r"C:\Windows\Media\notify.wav",
#            r"C:\Windows\Media\tada.wav"
#            r"C:\Windows\Media\Ring08.wav"
            winsound.SND_FILENAME | winsound.SND_ASYNC)
        

    def round_price_to_tick(self, price):
        # best to input price as abs(price) when calling function
        if price is None:
            return None
    
        price = self._safe_float(price, default=None)
        tick  = self._safe_float(self.min_tick, default=None)
        side  = self.buy_sell.upper()

        if price is None:
            return None
    
        if tick in (None, 0):
            return price
    
        scaled = price / tick
    
        if side == 'BUY':
            rounded = math.floor(scaled) * tick
        elif side == 'SELL':
            rounded = math.ceil(scaled) * tick
        else:
            raise ValueError("side must be 'BUY' or 'SELL'")
    
        return round(rounded, 10)
        

    def round_size_to_increment(self, size):
        # best to input size asabs(size) when calling function
        if size is None:
            return None

        size = self._safe_float(size, default=None)
        if size is None:
            return None

        inc = self.size_increment
        min_size = self.min_size

        if inc in (None, 0):
            rounded = size
        else:
            rounded = math.floor(size / inc) * inc

        if min_size not in (None, 0) and rounded < min_size:
            return 0.0

        return round(rounded, 10)

    
    def place_market_order(self, obj):  # very literal to improve speed
            if obj.is_mkt_data_valid():
                side         = obj.buy_sell
                size         = abs(obj.order_size) 
                order_id     = obj.order_id
                # output_price = abs(obj.placeholder_price)  no need for price when placing market order
                
                order_id = self.update_market_order(obj=obj,                                      
                                                    #price=output_price, 
                                                    side=side, 
                                                    size=size, 
                                                    order_id=order_id)   
                if self.print_orders:
                    self.print_order_message(side, size, obj.my_fi_name, "market", "backup", order_id)
        
                return order_id


    def update_market_order(self, obj=None, side=None, size=None, order_id=None):
        if obj.my_pf_name.upper() == "IBKR":
            if order_id is None:
                return obj.platform_obj.place_market_order(obj=obj, side=side, size=size)
            else:
                return obj.platform_obj.modify_to_market_order(order_id=order_id, obj=obj, side=side, size=size)

        raise NotImplementedError(f"No market order handler for platform {obj.my_pf_name}")
    
    
    def place_limit_order(self, obj, output_price, input_price):  # very literal to improve speed
        if obj.is_mkt_data_valid():
            side         = obj.buy_sell
            size         = abs(obj.order_size)
            order_id     = obj.order_id
            output_price = abs(output_price)
            
            order_id = self.update_limit_order(obj=obj,                                      
                                         price=output_price, 
                                         side=side, 
                                         size=size, 
                                         order_id=order_id)   
            if self.print_orders:
                self.print_order_message(side, size, obj.my_fi_name, output_price, input_price, order_id)
    
            return order_id
            

    def update_limit_order(self, obj=None, side=None, price=None, size=None, order_id=None):
        if obj.my_pf_name.upper() == "IBKR":
            if order_id is None:
                return obj.platform_obj.place_limit_order(obj=obj, side=side, price=price, size=size)
            else:
                return obj.platform_obj.modify_limit_order(order_id=order_id, obj=obj, price=price, size=size)
   
        raise NotImplementedError(f"No order handler for platform {obj.my_pf_name}")
        
    
    def print_order_message(self, side, size, name, output_price, input_price, order_id):
        print(f"{datetime.now():%H:%M:%S.%f}", 
              side, size, name, 
              ', order price = ', output_price, 
              ', base price = ' , input_price, 
              ', order id = '   , order_id,
              '\n')


    
                