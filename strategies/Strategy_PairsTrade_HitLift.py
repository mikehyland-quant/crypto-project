
import asyncio

from strategies.Strategy_Parent import Strategy

class PairsTrade_LimitLimit(Strategy):
    """
    Two-leg package strategy.

    Try to keep this to hot path code only, and put any non-essential logic in the parent class.
    """

    def __init__(self, objs_list, df):
        super().__init__(objs_list)  
        

        self.epsilon       = df.loc['epsilon'].sum()

        df = df.drop(index=['epsilon'])

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
        active_order_price = output_obj.active_order_price
        
        if active_order_price is not None and abs(output_price - active_order_price) < 1e-9:
            return     
        
        order_id = self.update_limit_order(obj=output_obj,   
                                           size=output_obj.order_size,
                                           buy_sell=output_obj.buy_sell,
                                           order_id=output_obj.order_id,
                                           price=output_price)

        if order_id is not None:
            output_obj.active_base_price   = input_price
            output_obj.active_order_price  = output_price        
            output_obj.order_id            = order_id  
        
            if self.print_orders:
                self.print_order_message(output_obj.buy_sell, 
                                         output_obj.order_size, 
                                         output_obj.my_fi_name, 
                                         output_price, 
                                         input_price, 
                                         order_id)

          
    async def on_trade_exec(self, filled_obj, filled_order):  
        remaining = filled_order.orderStatus.remaining
        
        if self.stage == "ZERO FILLED":
            if remaining > 0:
                return
            self.stage   = "ONE FILLED" 
            self._on_first_fill(filled_obj, filled_order)

        elif self.stage == "ONE FILLED":
            if remaining > 0:
                return   
            self.stage = "TWO FILLED"
        
        self._fill_obj_trade_attr(filled_obj, filled_order) 
        self.play_fill_sound()    

        if self.stage == "TWO FILLED":
            self._finalize_results()
                      
            
    def _on_first_fill(self, filled_obj, filled_order):     
        unfilled_obj = filled_obj.opp_obj
        order_id     = self.update_market_order(obj=unfilled_obj, 
                                                size=unfilled_obj.order_size,
                                                buy_sell=unfilled_obj.buy_sell,
                                                order_id=unfilled_obj.order_id)

        '''
        update_limit_order alternative
        
        input_price  = filled_order.orderStatus.avgFillPrice * filled_obj.filled_scalar
        output_price = unfilled_obj.calc_price(input_price, unfilled_obj, 1)  
    
        order_id = self.update_limit_order(obj=obj,                                      
                                            price=output_price,    
                                            order_id=order_id)   

        if order_id is not None:
            unfilled_obj.active_base_price   = input_price
            unfilled_obj.active_order_price  = output_price        
        '''
 
        filled_obj.strat_on_mkt_data    = False
        
        unfilled_obj.strat_on_mkt_data  = False

        unfilled_obj.active_order_price = None
        unfilled_obj.active_base_price = None


        
    def _calc_price(self, input_price, output_obj, epsilon_scalar=0):     
        fair_value   = output_obj.adj_spread - (input_price * output_obj.spread_ratio)
        output_price = fair_value - (epsilon_scalar * self.epsilon)
        output_price = output_obj.round_price_to_tick(abs(output_price))                                             
        return output_price

    