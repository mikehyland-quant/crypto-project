
import asyncio

from strategies.Strategy_PairsTrade_Parent import PairsTrade_Parent

class PairsTrade_LimitMarket(PairsTrade_Parent):
    """ 
    Two-leg package strategy.

    Try to keep this to hot path code only, and put any non-essential logic in the parent class.
    """

    def __init__(self, objs_list, df):
        super().__init__(objs_list, df)  
        
        #print(vars(self.obj1), '\n')
        #print(vars(self.obj2), '\n')  
         
   
    def on_mkt_data(self, input_obj):
        if self.stage != "ZERO FILLED":
            return  # no need to update price 

        output_obj  = input_obj.opp_obj

        if not input_obj.is_mkt_data_valid() or not output_obj.is_mkt_data_valid():
            return

        input_price = getattr(input_obj, input_obj.input_price_attr)
        active_base_price = output_obj.active_base_price
        
        if active_base_price is not None and abs(input_price - active_base_price) < 1e-9:
            return

        output_price = output_obj.calc_price(input_price, output_obj) #, 0)  
        active_order_price = output_obj.trade.order.lmtPrice if output_obj.trade is not None else None
        
        if active_order_price is not None and abs(output_price - active_order_price) < 1e-9:
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
        remaining = filled_order.orderStatus.remaining
        
        if self.stage == "ZERO FILLED":
            if remaining > 0:
                return
            
            self.stage = "ONE FILLED" 

            unfilled_obj = filled_obj.opp_obj  

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




     