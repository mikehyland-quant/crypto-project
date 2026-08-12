
# handles the on trade execution event and updates the trades accordingly
class GroupTrade_OnTradeExec:
  
    def on_trade_exec(self, filled_obj, filled_order):  
        status = filled_order.orderStatus

        filled = status.filled
        if filled == 0:   # this will be the case many times
            return

        filled_order_order = filled_order.order
        filled_action = filled_order_order_order.action

        if filled_obj.strat_on_mkt_data_change:
            # then this is first fill
            self._on_first_fill(filled_obj, filled_order_order, filled_action)
        else:
            # this is second fill
            self._on_second_fill(filled_action)


    def _on_first_fill(self, filled_obj, filled_order_order, filled_action):
        if filled_action.upper() == 'BUY':
            opp_action = 'sell'
        else:
            opp_action = 'buy'

        for obj in self.objs_list:
            if obj == filled_obj:
                opp_action_trade = getattr(obj, f"{opp_action}_trade")
                self.cancel_order(obj, opp_action_trade)
                obj.strat_on_trade_exec = False  
                self._finished_order_admin(filled_obj, filled_order_order) 

            else:
                filled_action_trade = getattr(obj, f"{filled_action}_trade")                
                self.cancel_order(obj, filled_action_trade)
                x = self.modify_primary_order(filled_obj, obj, filled_order_order, opp_action) # see specialty code

            obj.strat_on_mkt_data_change = False  # must be after self._finished_order_admin for filled_obj


    def _on_second_fill(self, filled_action):
         for obj in self.objs_list:
            filled_action_trade = getattr(obj, f"{filled_action}_trade")            
            if filled_action_trade.isActive():
                self.cancel_order(obj, filled_action_trade)
            obj.strat_on_trade_exec = False








            
  

        

