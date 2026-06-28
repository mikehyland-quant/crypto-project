
import asyncio

from strategies.Strategy_PairsTrade_Parent import PairsTrade_Parent


class PairsTrade_LimitLimit(PairsTrade_Parent):

    def __init__(self, objs_list, df):
        super().__init__(objs_list, df)  

        #print(vars(self.obj1), '\n')
        #print(vars(self.obj2), '\n')  
obj.calc_price         = self._calc_price_amount   # assigns function below 
          
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
            unfilled_obj.active_base_price = input_price
            self._placed_order_admin(unfilled_obj, trade)
                
                
    def launch_balancing_order(self):
        pass


