

class PairsTrade_OnTradeExecHotPath:
 
    def on_trade_exec(self, filled_obj, filled_order):  
        # this gets called on every trade execution

        status = filled_order.orderStatus

        filled = status.filled
        if filled == 0:   # this will be the case many times
            return
                
        unfilled_obj = filled_obj.opp_obj
        
        if self.no_partial_trades_yet:
            self._filled_before_partial(filled_obj, unfilled_obj, filled_order)
        else:
            self._filled_after_partial(filled_obj, unfilled_obj, filled_order)

        
    def _filled_before_partial(self, filled_obj, unfilled_obj, filled_order):
        # this is the only function called prior to a partial fill

        remaining = filled_order.orderStatus.filled
        if not unfilled_obj.trading_complete: # trading in other object wasn't complete
            if remaining == 0:  # this trade is complete
                return self._pre_partial_completely_filled(filled_obj, unfilled_obj, filled_order) 

            else:  # this trade is only partially filled
                return self._pre_partial_partially_filled(filled_obj, unfilled_obj, filled_order)
            
        else: #trading in other object was complete
            if remaining == 0:  # this trade is complete
                # else remaining > 0 and trading in this object is not yet complete so wait for complete fill
                filled_obj.trading_complete    = True
                filled_obj.strat_on_trade_exec = False

                self._finished_order_admin(filled_obj, filled_order)  
                
                self._finish_routine()   
            
            # else:  # this trade is only partially filled
            

    def _pre_partial_completely_filled(self, filled_obj, unfilled_obj, filled_order):
        # modify second object's order based on first object's COMPLETE fill - send revised price

        self.modify_unfilled_order(unfilled_obj, unfilled_obj.on_mkt_data_update_order_size, filled_order) # see specialty code

        filled_obj.strat_on_mkt_data_update   = False
        unfilled_obj.strat_on_mkt_data_update = False
        
        filled_obj.trading_complete           = True
        filled_obj.strat_on_trade_exec        = False

        self._finished_order_admin(filled_obj, filled_order)  


    def _pre_partial_partially_filled(self, filled_obj, unfilled_obj, filled_order):
        # modify second object's order based on first object's PARTIAL fill - send revised size and price

        self.no_partial_trades_yet = False
        
        self.cancel_order(filled_obj, filled_order)

        pct_filled = filled_order.orderStatus.filled / filled_obj.on_mkt_data_change_order_size
        new_order_size = unfilled_obj.round_size_to_increment(unfilled_obj.on_mkt_data_update_order_size * pct_filled)

        self.modify_unfilled_order(unfilled_obj, new_order_size, filled_order) # see specialty code

        
    def _filled_after_partial(self, filled_obj, unfilled_obj, filled_order, tolerance=0.02):
        # this is the only function called after a partial fill - gets called multiple times





















#########
        if remaining > 0:
            return  # can't make any decisions until remaining = 0
        





















        net_units = self.obj1.active_plus_traded_units - self.obj2.active_plus_traded_units
        need_balancing_order = (abs(net_units) > tolerance)
        if need_balancing_order:
            self.launch_balancing_order(net_units)
            
        # now that order amounts are balanced between the two objects
        self._finished_order_admin(filled_obj, filled_order)  

        if filled_obj.active_trade_list or unfilled_obj.active_trade_list: 
            return  # because there is at least one active trade outstanding
        
        self._finish_routine()
