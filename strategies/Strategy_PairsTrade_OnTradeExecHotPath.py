
import asyncio


class PairsTrade_OnTradeExecHotPath:
 
    def on_trade_exec(self, filled_obj, filled_order):  
        status = filled_order.orderStatus

        filled = status.filled
        if filled == 0:   # this will be the case many times
            return
        
        remaining = status.remaining
        
        unfilled_obj = filled_obj.opp_obj
        
        if self.trade_has_been_cancelled:
            return self._filled_after_cancellation(filled_obj, unfilled_obj, filled_order, remaining)
        
        return self._filled_before_cancellation(filled_obj, unfilled_obj, filled_order, remaining)
        

    def _filled_after_cancellation(self, filled_obj, unfilled_obj, filled_order, remaining, tolerance=0.02):
        if remaining > 0:
            return  # can't make any decisions until remaining = 0
        
        need_balancing_order = (abs(filled_obj.active_plus_traded_units - 
                                    unfilled_obj.active_plus_traded_units) > tolerance)
        if need_balancing_order:
            self.launch_balancing_order()
            
        # total order amounts are balanced between the two objects
        self._finished_order_admin(filled_obj, filled_order)  

        if filled_obj.active_trade_list or unfilled_obj.active_trade_list: 
            return
        
        '''
        # neither object has any active trades outstanding
        for object in [filled_obj, unfilled_obj]:
            object.trading_complete         = True
            object.strat_on_trade_exec      = False
            object.strat_on_mkt_data_update = False
        '''
        
        self._finish_routine()

        
    def _filled_before_cancellation(self, filled_obj, unfilled_obj, filled_order, remaining):
        if unfilled_obj.trading_complete: # trading in other object is complete
            return self._filled_before_cancellation_opp_obj_trading_complete(filled_obj, filled_order, remaining)
    
        else:  # trading in other object is not yet complete
            if remaining == 0:  # this trade is completely filled
                return self._filled_before_cancellation_completely_opp_obj_trading_incomplete(filled_obj, unfilled_obj, filled_order) 

            else:  # this trade is only partially filled
                return self._filled_before_cancellation_partially_opp_obj_trading_incomplete(filled_obj, unfilled_obj, filled_order)
                

    def _filled_before_cancellation_opp_obj_trading_complete(self, filled_obj, filled_order, remaining):
        if remaining == 0:  # this trade is completely filled
            filled_obj.trading_complete    = True
            filled_obj.strat_on_trade_exec = False

            self._finished_order_admin(filled_obj, filled_order)  
            self._finish_routine()   
        # else:  # remaining > 0 and trading in this object is not yet complete


    def _filled_before_cancellation_completely_opp_obj_trading_incomplete(self, filled_obj, unfilled_obj, filled_order):
        self.on_trade_exec_modify_unfilled_order(unfilled_obj, filled_order, unfilled_obj.initial_order_size) # see specialty code

        filled_obj.trading_complete           = True
        filled_obj.strat_on_trade_exec        = False
        filled_obj.strat_on_mkt_data_update   = False
        unfilled_obj.strat_on_mkt_data_update = False

        self._finished_order_admin(filled_obj, filled_order)  


    def _filled_before_cancellation_partially_opp_obj_trading_incomplete(self, filled_obj, unfilled_obj, filled_order):
        self.cancel_order(filled_obj, filled_order)

        pct_filled = filled_order.orderStatus.filled / filled_obj.initial_order_size
        new_order_size = unfilled_obj.round_size_to_increment(unfilled_obj.initial_order_size * pct_filled)

        self.on_trade_exec_modify_unfilled_order(unfilled_obj, filled_order, new_order_size) # see specialty code

        self.trade_has_been_cancelled = True
