
from pairs_trade.PairsTrade_Parent  import PairsTrade_Parent


class PairsTrade_LimitMarket(PairsTrade_Parent):

     
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
        