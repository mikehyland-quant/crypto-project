
import asyncio
import math
import types
import winsound

from datetime import datetime

class Strategy:
    _RULE_FIELD_MAP = {
        'min_tick'       : 'minTick',
        'min_size'       : 'minSize',
        'size_increment' : 'sizeIncrement',
                    }


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
        
            
    def on_mkt_data(self, obj):
        pass
        

    def on_trade_exec(self, obj):
        pass


    def on_close_data(self, obj):
        pass


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
        buy_sell  = self.buy_sell.upper()

        if price is None:
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


    def update_market_order(self, obj=None, size=None, buy_sell=None, order_id=None):
        if order_id is None:
            return obj.platform_obj.place_market_order(obj=obj, size=size, buy_sell=buy_sell)
        else:
            return obj.platform_obj.modify_to_market_order(obj=obj, size=size, buy_sell=buy_sell, order_id=order_id)
        raise NotImplementedError(f"No market order handler for platform {obj.my_pf_name}")
            

    def update_limit_order(self, obj=None, size=None, buy_sell=None, order_id=None, price=None):
        print(order_id)
        if order_id is None:
            return obj.platform_obj.place_limit_order(obj=obj, size=size, buy_sell=buy_sell, price=price)
        else:
            return obj.platform_obj.modify_limit_order(obj=obj, size=size, buy_sell=buy_sell, order_id=order_id, price=price)
        raise NotImplementedError(f"No order handler for platform {obj.my_pf_name}")
    

    def print_order_message(self, buy_sell, size, fi_name, price, mkt_price, order_id):
        print(f"{buy_sell} {size} of {fi_name} at {price} (mkt: {mkt_price}) - order_id: {order_id}")
