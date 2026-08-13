
from group_trade.GroupTrade_Parent import GroupTrade_Parent


class GroupTrade_LimitLimit(GroupTrade_Parent):

    def __init__(self, bo_obj):
        super().__init__(bo_obj) 
 
    def senf_follow_up_order(self, filled_obj, unfilled_obj, filled_order, unfilled_action):  
        avg_fill_price = filled_order.orderStatus.avgFillPrice
        avg_fill_cf = avg_fill_price - filled_obj.calc_comm(avg_fill_price, 'maker')
        filled_unit_cf = avg_fill_cf * filled_obj.scalar_size_FIs_per_unit

        profitable_unit_cf = filled_unit_cf + getattr(self, f"{unfilled_action}_profit_margin")

        unfilled_price = unfilled_obj.decompose_unit_cf(profitable_unit_cf, maker_taker="taker")
        unfilled_price = unfilled_obj.round_price_to_tick(abs(unfilled_price[0]), unfilled_action)

        unfilled_trade = getattr(obj, f"{unfilled_action}_trade")
     
        new_trade = self.update_limit_order(obj=unfilled_obj,  
                                            trade=unfilled_trade,
                                            price=unfilled_price)
        
        if new_trade is not None:
            self._placed_order_admin(unfilled_obj, new_trade, avg_fill_price)

        return new_trade

    '''
    #  if initial trades are all-or-none then no need for balancing orders



    '''
            new_unit_price = bo_obj_price + margin
            new_fi_price = obj.decompose_unit_cf(new_unit_price, 'taker')
            new_fi_price = obj.round_price_to_tick(abs(new_fi_price[0]), buy_sell)

            if new_fi_price != prev_order_price:
                trade = self.update_limit_order(obj=obj, 
                                                trade=prev_trade, 
                                                price=new_fi_price)
                
                if trade is not None:
                    self._placed_order_admin(obj, trade, bo_obj_price)
