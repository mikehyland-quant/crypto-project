
from pairs_trade.PairsTrade_Parent import PairsTrade_Parent


class PairsTrade_LimitLimit(PairsTrade_Parent):


    async def modify_unfilled_order(self, obj, size, filled_order):  
        avg_fill_price = filled_order.orderStatus.avgFillPrice
        input_price    = avg_fill_price * obj.opp_obj.filled_scalar
        output_price   = self.calc_price(input_price, obj, 1)  

        trade = self.update_limit_order(obj=obj, 
                                        size=size,       
                                        trade=obj.primary_trade,
                                        price=output_price)
        
        if trade is not None:
            self._primary_trade_placed_order_admin(obj, trade, input_price, output_price)
            self._placed_order_admin(obj, trade, size, output_price)

            return trade


    def launch_balancing_order(self, obj, size, filled_order):
        opp_obj fillavg_fill_price = 
        input_price    = avg_fill_price * obj.opp_obj.filled_scalar


        output_price   = self.calc_price(input_price, obj, 1) 
    
        trade =  self.update_limit_order(obj=obj, 
                                         size=size, 
                                         buy_sell=obj.buy_sell,
                                         price=output_price,
                                         trade=None)
    
        if trade is not None:
            self._placed_order_admin(obj, trade, size, output_price)

            return trade
        


