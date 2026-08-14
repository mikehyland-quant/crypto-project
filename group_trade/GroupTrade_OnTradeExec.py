
# handles the on trade execution event and updates the trades accordingly
class GroupTrade_OnTradeExec:
  
    def on_trade_exec(self, filled_obj, filled_trade):  
        filled_trade_status = filled_trade.orderStatus

        filled = filled_trade_status.filled
        if filled == 0:   # this will be the case many times
            return

        filled_trade_order = filled_trade.order
        filled_action = filled_trade_order.action

        if filled_obj.strat_on_mkt_data_change:
            # then this is first fill
            self._on_first_fill(filled_obj, filled_trade_order, filled_trade_status, filled_action)
        else:
            # this is second fill
            self._on_second_fill(filled_obj, filled_trade_order, filled_trade_status, filled_action)


    def _on_first_fill(self, filled_obj, filled_trade_order, filled_trade_status, filled_action):
        if filled_action.upper() == 'BUY':
            opp_action = 'sell'
            opp_task = 'lift_ask'
        else:
            opp_action = 'buy'
            opp_task = 'hit_bid'

        best_obj = getattr(self.bo_obj, f'strat_{opp_task}_obj')
        x = self.send_follow_up_order(filled_obj, best_obj, filled_trade_status, opp_action) # see specialty code

        for obj in self.objs_list:
            if obj == filled_obj:
                opp_action_trade = getattr(obj, f'{opp_action}_trade')
                self.cancel_order(obj, opp_action_trade)
                obj.strat_on_trade_exec = False  
            else:
                filled_action_trade = getattr(obj, f'{filled_action.lower()}_trade')                
                self.cancel_order(obj, filled_action_trade)
                # x = self.send_follow_up_order(filled_obj, obj, filled_trade_order, opp_action) # see specialty code

            obj.strat_on_mkt_data_change = False
            self._finished_order_admin(filled_obj, filled_trade_order, filled_trade_status) 


    def _on_second_fill(self, filled_obj, filled_trade_order, filled_trade_status, filled_action):
         for obj in self.objs_list:
            filled_action_trade = getattr(obj, f'{filled_action.lower()}_trade')            
            if filled_action_trade.isActive():
                self.cancel_order(obj, filled_action_trade)
            obj.strat_on_trade_exec = False
            self._finished_order_admin(filled_obj, filled_trade_order, filled_trade_status) 






            
  

        

