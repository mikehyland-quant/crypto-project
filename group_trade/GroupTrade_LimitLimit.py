
from group_trade.GroupTrade_Parent import GroupTrade_Parent


class GroupTrade_LimitLimit(GroupTrade_Parent):

    def __init__(self, bo_obj):
        super().__init__(bo_obj) 
 
    def send_follow_up_order(self, filled_obj, unfilled_obj, filled_status, unfilled_action):  
        avg_fill_price = filled_status.avgFillPrice
        avg_fill_cf = avg_fill_price - filled_obj.calc_comm(avg_fill_price, 'maker')
        filled_unit_cf = avg_fill_cf * filled_obj.scalar_size_FIs_per_unit

        profitable_unit_cf = getattr(self, f"{unfilled_action}_profit_margin") - filled_unit_cf

        unfilled_price = unfilled_obj.decompose_unit_cf(profitable_unit_cf, 'taker')
        unfilled_price = unfilled_obj.round_price_to_tick(abs(unfilled_price[0]), unfilled_action)

        unfilled_trade = getattr(unfilled_obj, f"{unfilled_action}_trade")
     
        new_trade = self.update_limit_order(obj=unfilled_obj,  
                                            trade=unfilled_trade,
                                            price=unfilled_price)
        
        if new_trade is not None:
            self._placed_order_admin(unfilled_obj, new_trade, avg_fill_price)

        return new_trade

    '''
    #  if initial trades are all-or-none then no need for balancing orders
    '''
      