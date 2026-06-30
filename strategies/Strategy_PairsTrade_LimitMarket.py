
import asyncio

from strategies.Strategy_PairsTrade_Parent import PairsTrade_Parent


class PairsTrade_LimitMarket(PairsTrade_Parent):

    def __init__(self, objs_list, df):
        super().__init__(objs_list, df)  

        #print(vars(self.obj1), '\n')
        #print(vars(self.obj2), '\n')  

        for obj in objs_list:
            obj.calc_price = self._calc_price_amount   # assigns function below
            # print(vars(obj), '\n')

     
    def on_trade_exec_modify_unfilled_order(self, unfilled_obj, order_size, filled_order):
        trade = self.modify_market_order(obj=unfilled_obj, 
                                         size=order_size, 
                                         trade=unfilled_obj.on_mkt_data_change_trade)
        
        if trade is not None:
            unfilled_obj.active_base_price  = None
            unfilled_obj.active_order_price = None            
            self._placed_order_admin(unfilled_obj, trade)
                

    def launch_balancing_order(self, net_units):
        if net_units > 0:
            order_obj = self.obj2
        else:
            order_obj = self.obj1

        order_size = net_units * order_obj.scalar_size_orders_per_unit

        trade = self.modify_market_order(obj=order_obj, 
                                         size=order_size, 
                                         buy_sell=order_obj.buy_sell,
                                         trade=None)
        
        if trade is not None:           
            self._placed_order_admin(order_obj, trade)
            