
import asyncio
import math
import types
import winsound


class Strategy_Parent:


    def __init__(self, objs_list=None, *args, **kwargs):
        super().__init__()

        self.done_event = asyncio.Event()  # needs to be awaited in main() and set at the end of each strategy
        
        # set to False in main() to disable printing
        self.need_to_print_active_orders   = True  
        self.need_to_print_finished_orders = True
        
        self.objs_list = objs_list if objs_list is not None else []
      
        for obj in self.objs_list:
            obj.strategy = self

            obj.strat_on_closing_price   = True
            obj.strat_on_mkt_data_change = True
            obj.strat_on_trade_exec      = True

            obj.round_price_to_tick      = types.MethodType(type(self).round_price_to_tick, obj)
            obj.round_size_to_increment  = types.MethodType(type(self).round_size_to_increment, obj)       
            
   
    @classmethod    
    def play_fill_sound(self):
        winsound.PlaySound(
            r"C:\Windows\Media\notify.wav",
#            r"C:\Windows\Media\tada.wav"
#            r"C:\Windows\Media\Ring08.wav"
            winsound.SND_FILENAME | winsound.SND_ASYNC)
        

    def round_price_to_tick(self, price, buy_sell=None):
        # best to input price as abs(price) when calling function
        # rounds price to tick conservatively based on buy/bid or sell/ask
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
        # rounds up or down to closest size increment
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
    

    def update_market_order(self, obj=None, size=None, buy_sell=None, trade=None):
        if trade is None:
            return obj.platform_obj.place_market_order(obj=obj, size=size, buy_sell=buy_sell)
        else:
            return obj.platform_obj.modify_to_market_order(obj=obj, size=size, buy_sell=buy_sell, trade=trade)
        raise NotImplementedError(f"No market order handler for platform {obj.my_pf_name}")
            

    def update_limit_order(self, obj=None, size=None, buy_sell=None, trade=None, price=None, all_or_none=None):
        if trade is None:
            if all_or_none is None:
                all_or_none = False
            return obj.platform_obj.place_limit_order(obj=obj, size=size, buy_sell=buy_sell, 
                                                      price=price, all_or_none=all_or_none)
        else:
            return obj.platform_obj.modify_limit_order(obj=obj, size=size, buy_sell=buy_sell, 
                                                       trade=trade, price=price, all_or_none=all_or_none)
        raise NotImplementedError(f"No order handler for platform {obj.my_pf_name}")
    

    def cancel_order(self, obj, trade):
        obj.platform_obj.cancel_order(trade)

     
    def print_orders(self, active_finished, buy_sell, size, fi_name, price, order_id):
        if price == None:
            price = "market"
        print(f"{active_finished} order: {buy_sell} {size} of {fi_name} at {price} - order_id: {order_id}", '\n')


    def calc_final_fills_and_avg_price(self, obj):
        trade_list = obj.finished_trade_dict.values()

        total_filled = sum(t.orderStatus.filled for t in trade_list)

        if total_filled == 0:
            return 0, None

        total_dollars = sum(
            t.orderStatus.filled * t.orderStatus.avgFillPrice
            for t in trade_list
        )

        avg_fill_price = total_dollars / total_filled

        return total_filled, avg_fill_price
    

    def finish_strategy(self):
        self._finalize_results()

        # if using event:
        if self.done_event is not None:
            self.done_event.set()
