
import asyncio

from strategies.Strategy_PairsTrade_Parent import PairsTrade_Parent


class PairsTrade_LimitMarket(PairsTrade_Parent):

    def __init__(self, objs_list, df):
        super().__init__(objs_list, df)  

        #print(vars(self.obj1), '\n')
        #print(vars(self.obj2), '\n')  

     
    def modify_primary_order(self, obj, size, x=None):
        trade =  self.update_market_order(obj=obj, 
                                          size=size, 
                                          trade=obj.primary_trade)
    
        if trade is not None:
            self._placed_order_admin(obj, trade, size, "market")

        return trade
        
 
    def launch_balancing_order(self, obj, size, x=None):
        trade =  self.update_market_order(obj=obj, 
                                          size=size, 
                                          buy_sell=obj.buy_sell,
                                          trade=None)
    
        if trade is not None:
            self._placed_order_admin(obj, trade, size, "market")

        return trade
        