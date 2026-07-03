
# handles the on trade execution event and updates the trades accordingly
class PairsTrade_OnTradeExec:
  
 
    def on_trade_exec(self, filled_obj, filled_order):  
        # this gets called on every trade execution

        status = filled_order.orderStatus

        filled = status.filled
        if filled == 0:   # this will be the case many times
            return
                
        unfilled_obj = filled_obj.opp_obj

        filled_obj.strat_on_mkt_data_update   = False
        unfilled_obj.strat_on_mkt_data_update = False 
        
        if self.no_partial_trades_yet:
            self._filled_before_partial(filled_obj, unfilled_obj, filled_order)
        else:
            self._filled_after_partial(filled_obj, unfilled_obj, filled_order)

       
    def _filled_before_partial(self, filled_obj, unfilled_obj, filled_order):
        # this is the only function called prior to a partial fill

        remaining = filled_order.orderStatus.remaining

        if remaining == 0:  # this trade is complete
            self._pre_partial_completely_filled(filled_obj, unfilled_obj, filled_order) 

        else:  # this trade is only partially filled
            self._pre_partial_partially_filled(filled_obj, unfilled_obj, filled_order)
       

    def _pre_partial_completely_filled(self, filled_obj, unfilled_obj, filled_order):
        # this is either the first or second complete fill
        # if this is first complete fill then modify other obj's primary order based on this fill
        if unfilled_obj.strat_on_trade_exec:  # unfilled obj is still active
            x = self.modify_primary_order(unfilled_obj, unfilled_obj.primary_trade_initial_order_size, filled_order) # see specialty code
            
        # regardless of which fill, the filled obj needs to be "turned off"
        filled_obj.strat_on_trade_exec        = False
        #filled_obj.trading_complete           = True
        
        self._finished_order_admin(filled_obj, filled_order) 


    def _pre_partial_partially_filled(self, filled_obj, unfilled_obj, filled_order):
        # if other object is already complete then just wait for this object to complete
        if not unfilled_obj.strat_on_trade_exec:  # unfilled obj is not active
            return

        # this is the first fill and it is only partial
        # first object's primary order needs to be cancelled
        # second object's primary order needs a modified size based on first object's partial fill
        self.no_partial_trades_yet = False
        
        self.cancel_order(filled_obj, filled_order)

        pct_filled = filled_order.orderStatus.filled / filled_obj.primary_trade_initial_order_size
        new_order_size = unfilled_obj.round_size_to_increment(unfilled_obj.primary_trade_initial_order_size * pct_filled)

        x = self.modify_primary_order(unfilled_obj, new_order_size) # see specialty code

        
    def _filled_after_partial(self, filled_obj, unfilled_obj, filled_order, tolerance=0.02):
        # this is the only function called after a partial fill - gets called multiple times

        if filled_order.orderStatus.status not in filled_obj.platform_obj.DONE_STATUSES:
            return  # trade is still open, can't make any decisions until remaining = 0
        
        self._finished_order_admin(filled_obj, filled_order)  
        
        net_units = self.obj1.active_plus_traded_units - self.obj2.active_plus_traded_units
        print('net units = ', self.obj1.my_fi_name, self.obj1.active_plus_traded_units, 
                              self.obj2.my_fi_name, self.obj2.active_plus_traded_units, '\n')

        need_balancing_order = (abs(net_units) > tolerance)
        if need_balancing_order:
            x = self.prep_and_launch_balancing_order(net_units)

        if (filled_obj.active_orders + unfilled_obj.active_orders == 0): 
            filled_obj.strat_on_trade_exec        = False
            unfilled_obj.strat_on_trade_exec      = False

            self.finish_strategy()
        
   
        