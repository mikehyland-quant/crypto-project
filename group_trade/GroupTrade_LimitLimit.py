
from group_trade.GroupTrade_Parent import GroupTrade_Parent


class GroupTrade_LimitLimit(GroupTrade_Parent):

    def __init__(self, bo_obj):
        super().__init__(bo_obj) 

 
    def modify_primary_order(self, obj, size, filled_order):  
        avg_fill_price = filled_order.orderStatus.avgFillPrice
        #input_price    = avg_fill_price * obj.opp_obj.filled_scalar
        output_price   = self._calc_price(filled_order.orderStatus.avgFillPrice, 
                                          obj, 1)  

        trade = self.update_limit_order(obj=obj, 
                                        size=size,       
                                        trade=obj.primary_trade,
                                        price=output_price)
        
        if trade is not None:
            # self._primary_trade_placed_order_admin(obj, trade, input_price, output_price)
            self._placed_order_admin(obj, trade, size, output_price)

            return trade

    '''
    #  if initial trades are all-or-none then no need for balancing orders
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
    '''


