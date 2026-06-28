
import asyncio

from strategies.Strategy_PairsTrade_Parent import PairsTrade_Parent

class PairsTrade_LimitLimit(PairsTrade_Parent):
    """
    Two-leg package strategy.

    Try to keep this to hot path code only, and put any non-essential logic in the parent class.
    """

    def __init__(self, objs_list, df):
        super().__init__(objs_list, df)  

        #print(vars(self.obj1), '\n')
        #print(vars(self.obj2), '\n')  

          
    async def on_trade_exec_modify_unfilled_order(self, unfilled_obj, filled_order):  
        avg_fill_price = filled_order.orderStatus.avgFillPrice
        input_price    = avg_fill_price * filled_obj.filled_scalar
        output_price   = unfilled_obj.calc_price(input_price, unfilled_obj, 1)  

        trade = unfilled_obj.platform_obj.modify_limit_order(obj=unfilled_obj, 
                                                                size=unfilled_obj.order_size, 
                                                                buy_sell=unfilled_obj.buy_sell, 
                                                                trade=unfilled_obj.trade,
                                                                price=output_price)
        
        if trade is not None:
            self._placed_order_admin(unfilled_obj, trade, input_price)

            if self.print_orders:
                self.print_order_message(unfilled_obj.buy_sell, 
                                            unfilled_obj.order_size, 
                                            unfilled_obj.my_fi_name, 
                                            output_price, 
                                            # input_price, 
                                            trade.order.orderId)
                
                
    def launch_balancing_order(self):
        pass


