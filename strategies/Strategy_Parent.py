
import asyncio
import math
import types
import winsound

from datetime import datetime

class Strategy:

    def __init__(self, objs_list=None):
        self.done_event = asyncio.Event()  # needs to be awaited in main() and set at the end of each strategy
        self.print_orders = True  # set to False in main() to disable order printing
        
        self.objs_list = objs_list if objs_list is not None else []
               
        for obj in self.objs_list:
            self._attach_trading_helpers(obj)
            obj.strategy             = self
            obj.strat_on_mkt_data    = True
            obj.strat_on_trade_exec  = True
            obj.strat_on_close_data  = True
        
            
    @classmethod
    def _attach_trading_helpers(cls, obj):
        #obj.my_trading_rules = cls._extract_trading_rules(obj)

        obj.round_price_to_tick = types.MethodType(cls.round_price_to_tick, obj)
        obj.round_size_to_increment = types.MethodType(cls.round_size_to_increment, obj)
        
   
    @classmethod    
    def play_fill_sound(self):
        winsound.PlaySound(
            r"C:\Windows\Media\notify.wav",
#            r"C:\Windows\Media\tada.wav"
#            r"C:\Windows\Media\Ring08.wav"
            winsound.SND_FILENAME | winsound.SND_ASYNC)
        

    def round_price_to_tick(self, price, buy_sell=None):
        # best to input price as abs(price) when calling function
        if price is None:
            return None
    
        price = self._safe_float(price, default=None)
        tick  = self._safe_float(self.min_tick, default=None)
        buy_sell = buy_sell.upper() if buy_sell else self.buy_sell.upper() if hasattr(self, 'buy_sell') else None

        if price is None or buy_sell not in ('BUY', 'SELL'):
            return None
    
        if tick in (None, 0):
            return price
    
        scaled = price / tick
    
        if buy_sell == 'BUY':
            rounded = math.floor(scaled) * tick
        elif buy_sell == 'SELL':   
            rounded = math.ceil(scaled) * tick
        else:
            raise ValueError("buy_sell must be 'BUY' or 'SELL'")
    
        return round(rounded, 10)
        

    def round_size_to_increment(self, size):
        # best to input size as abs(size) when calling function
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
            rounded = round(size / inc) * inc

        if min_size not in (None, 0) and rounded < min_size:
            return 0.0
 
        return round(rounded, 10)


    def update_market_order(self, obj=None, size=None, buy_sell=None, order_id=None):
        if order_id is None:
            return obj.platform_obj.place_market_order(obj=obj, size=size, buy_sell=buy_sell)
        else:
            return obj.platform_obj.modify_to_market_order(obj=obj, size=size, buy_sell=buy_sell, order_id=order_id)
        raise NotImplementedError(f"No market order handler for platform {obj.my_pf_name}")
            

    def update_limit_order(self, obj=None, size=None, buy_sell=None, order_id=None, price=None):
        if order_id is None:
            return obj.platform_obj.place_limit_order(obj=obj, size=size, buy_sell=buy_sell, price=price)
        else:
            return obj.platform_obj.modify_limit_order(obj=obj, size=size, buy_sell=buy_sell, order_id=order_id, price=price)
        raise NotImplementedError(f"No order handler for platform {obj.my_pf_name}")
    

    def print_order_message(self, buy_sell, size, fi_name, price, order_id):
        print(f"{buy_sell} {size} of {fi_name} at {price} - order_id: {order_id}")


    def on_close_data(self, obj):
        pass


    def on_mkt_data(self, obj):
        pass
        

    def on_trade_exec(self, obj, trade):
        pass



