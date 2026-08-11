
# handles the on trade execution event and updates the trades accordingly
class GroupTrade_OnTradeExec:
  
 
    def on_trade_exec(self, filled_obj, filled_order):  
        # this gets called on every trade execution



# cancel all outstanding orders








        status = filled_order.orderStatus

        filled = status.filled
        if filled == 0:   # this will be the case many times
            return
                
        unfilled_obj = filled_obj.opp_obj

        filled_obj.strat_on_mkt_data_change   = False
        unfilled_obj.strat_on_mkt_data_change = False 

        remaining = filled_order.orderStatus.remaining

        if unfilled_obj.strat_on_trade_exec:  # unfilled obj is still active
            x = self.modify_primary_order(unfilled_obj, 
                                          unfilled_obj.primary_trade_initial_order_size, 
                                          filled_order) # see specialty code
            
        # regardless of which fill, the filled obj needs to be "turned off"
        filled_obj.strat_on_trade_exec        = False
        #filled_obj.trading_complete           = True
        
        self._finished_order_admin(filled_obj, filled_order) 
