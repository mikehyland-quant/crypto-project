
import asyncio

from strategies.Strategy_PairsTrade_Parent import PairsTrade_Parent

class PairsTrade_SpotETF(PairsTrade_Parent):
    """ 
    Two-leg package strategy.

    Try to keep this to hot path code only, and put any non-essential logic in the parent class.
    """

    def __init__(self, objs_list, df):
        super().__init__(objs_list, df)  
        
        #print(vars(self.obj1), '\n')
        #print(vars(self.obj2), '\n') 

        [spot_obj] = [obj in objs_list if obj.my_prod_type == "SPOT"]
            
        if spot_obj.buy_sell == 'BUY':
            spot_obj.spot_scalar = 1 - self.target_spread
        elif spot_obj.buy_sell == 'SELL':
            spot_obj.spot_scalar = 1 + self.target_spread
            
        print("SPOT", spot_obj.buy_sell, spot_obj.spot_scalar)   
         
    
    def on_close_data(self, obj):
        #creates a placeholder limit order to get trade opened and in system

        if obj.my_prod_type == 'SPOT':
            obj.strat_on_close_data = False 

            return

        mkt_close = obj.price_screen_close
        if obj.buy_sell == 'BUY':
            placeholder_price = mkt_close * 0.5
        elif obj.buy_sell == 'SELL':
            placeholder_price = mkt_close * 2.0

        placeholder_price = obj.round_price_to_tick(placeholder_price)

        size=obj.order_size
        buy_sell=obj.buy_sell
        
        trade = obj.platform_obj.place_limit_order(obj=obj, 
                                                   size=size, 
                                                   buy_sell=buy_sell, 
                                                   price=placeholder_price)
        
        if trade is not None:
            obj.strat_on_close_data = False 
            
            if self.print_orders:
                self.print_order_message(buy_sell, size, obj.my_fi_name, placeholder_price, trade.order.orderId)

            self._placed_order_admin(obj, trade, mkt_close)
            
    
    def _calc_price(self, unit_input_price, output_obj):     
        unit_output_price = unit_input_price * output_obj.spot_scalar
        unit_output_price = output_obj.round_price_to_tick(abs(unit_output_price))    
        # print(unit_input_price, unit_output_price)                                         
        return unit_output_price
    
    
    def on_mkt_data(self, input_obj):
        if self.stage != "ZERO FILLED":
            return  # no need to update price 

        output_obj  = input_obj.opp_obj

        if not input_obj.is_mkt_data_valid() or not output_obj.is_mkt_data_valid():
            return

        input_price = getattr(input_obj, input_obj.input_price_attr)
        # active_base_price = output_obj.active_base_price
        
        # if active_base_price is not None and abs(input_price - active_base_price) < 1e-9:
            # return

        output_price = output_obj.calc_price(input_price, output_obj) #, 0)  
        active_order_price = output_obj.trade.order.lmtPrice if output_obj.trade is not None else None
        
        # if active_order_price is not None and abs(output_price - active_order_price) < 1e-9:
            # return
             
        if output_obj.buy_sell == 'BUY' and output_price > active_order_price:
            return
        
        if output_obj.buy_sell == 'SELL' and output_price < active_order_price:
            return

        trade = output_obj.platform_obj.modify_limit_order(obj=output_obj, 
                                                           size=output_obj.order_size, 
                                                           buy_sell=output_obj.buy_sell, 
                                                           trade=output_obj.trade, 
                                                           price=output_price)

        if trade is not None:
            self._placed_order_admin(output_obj, trade, input_price)
            
            if self.print_orders:
                self.print_order_message(output_obj.buy_sell, 
                                         output_obj.order_size, 
                                         output_obj.my_fi_name, 
                                         output_price, 
                                         input_price, 
                                         trade.order.orderId)
    

          
    async def on_trade_exec(self, filled_obj, filled_order):  
        filled = filled_order.orderStatus.filled
        remaining = filled_order.orderStatus.remaining
        
        if self.stage == "ZERO FILLED":
            if filled == 0:
                return
            
            self.stage = "ONE FILLED" 

            unfilled_obj = filled_obj.opp_obj  
 
            if remaining > 0:
                self.cancel_trade(filled_order)
                pct_filled = filled_order.orderStatus.filled / remaining
                unfilled_obj.order_size = unfilled_obj.round_size_to_increment(unfilled_obj.order_size * pct_filled)

            trade = unfilled_obj.platform_obj.modify_to_market_order(obj=unfilled_obj, 
                                                                     size=unfilled_obj.order_size, 
                                                                     buy_sell=unfilled_obj.buy_sell, 
                                                                     trade=unfilled_obj.trade)
         
            if trade is not None:
                self._placed_order_admin(unfilled_obj, trade, None)

                if self.print_orders:
                    self.print_order_message(unfilled_obj.buy_sell, 
                                             unfilled_obj.order_size, 
                                             unfilled_obj.my_fi_name, 
                                             "market order", 
                                             "market order", 
                                             trade.order.orderId)
                           
            #_filled_obj_admin is called below

            filled_obj.strat_on_mkt_data    = False
            unfilled_obj.strat_on_mkt_data  = False           

        elif self.stage == "ONE FILLED":
            if remaining > 0:
                return   

            self.stage = "TWO FILLED"
            
            #_filled_obj_admin is called below
        
        self._filled_order_admin(filled_obj) 
        self.play_fill_sound()    

        if self.stage == "TWO FILLED":
            self._finalize_results()

            # if using event:
            if self.done_event is not None:
                self.done_event.set()




     