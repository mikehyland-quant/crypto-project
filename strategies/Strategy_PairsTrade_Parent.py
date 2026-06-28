
import asyncio

from strategies.Strategy_Parent import Strategy

class PairsTrade_Parent(Strategy):
    """ 
    Two-leg package strategy.

    This is for shared code between different pairs trade strategies. Try to keep this to non-hot path code, and put any hot path code in the child class.
    """

    def __init__(self, objs_list, df):
        super().__init__(objs_list)  
        
        # create self attributes
        self.trade_has_been_cancelled = False

        self.target_spread = df.loc['target_profit_per_unit'].sum()
        self.epsilon       = df.loc['epsilon_per_unit'].sum()
        
        df = df.drop(index=['target_profit_per_unit'])
        df = df.drop(index=['epsilon_per_unit'])

        objs_dict = df.to_dict()

        # attach attributes to objs
        self.obj1, self.obj2 = self._attach_input_attr(objs_list, objs_dict)
                                                 
        self.obj1.opp_obj = self.obj2
        self.obj2.opp_obj = self.obj1

        self.obj1, self.obj2 = self._attach_strat_attr([self.obj1, self.obj2])

                
    def _attach_input_attr(self, objs_list, objs_dict):
        for obj_name, obj_dict in objs_dict.items():
    
            obj = next(
                        (
                        o for o in objs_list
                        if o.my_fi_name == obj_dict['my_fi_name']
                        and o.my_pf_name == obj_dict['my_pf_name']
                        ),
                        None
                    )
    
            if obj is None:
                raise ValueError(f"Could not find object for {obj_name}: {obj_dict}")
    
            # creates self.obj1, self.obj2, etc.
            setattr(self, obj_name.lower(), obj)
     
            # attaches strategy attrs to the object
            for attr_key, attr_val in obj_dict.items():
                setattr(obj, attr_key, attr_val)
    
        return self.obj1, self.obj2
 
 
    def _attach_strat_attr(self, objs_list):
        buy_tuple      = ('BUY', 'cf_unit_lift_ask', -1)
        sell_tuple     = ('SELL', 'cf_unit_hit_bid',  1)
        min_ratio_size = min(self.obj1.ratio_size, self.obj2.ratio_size)
        
        for obj in objs_list:
            obj.active_base_price  = None

            if obj.initial_unit_order_size > 0:
                (obj.buy_sell, obj.input_price_attr, obj.filled_scalar) = buy_tuple 
            elif obj.initial_unit_order_size < 0:
                (obj.buy_sell, obj.input_price_attr, obj.filled_scalar) = sell_tuple  
        
            obj.initial_screens_order_size = obj.round_size_to_increment(abs(obj.unit_order_size * obj.scalar_screens_per_unit))
            obj.order_size                 = obj.initial_screens_order_size     
            
            obj.spread_ratio = obj.opp_obj.ratio_size / min_ratio_size
            obj.adj_spread   = self.target_spread / obj.spread_ratio
    
            if obj.active_passive.lower() == 'passive':
                #was set to True in Strategy_Parent, so now set to False for passive leg
                setattr(obj.opp_obj, 'strat_on_mkt_data', False)   

        return self.obj1, self.obj2
                    

   def on_close_update(self, obj):
        #creates a placeholder limit order to get trade opened and in system
        mkt_close = obj.price_screen_close

        if obj.buy_sell == 'BUY':
            placeholder_price = mkt_close * 0.5
        elif obj.buy_sell == 'SELL':
            placeholder_price = mkt_close * 2.0

        placeholder_price = obj.round_price_to_tick(placeholder_price)

        size=obj.order_size
        buy_sell=obj.
        
        trade = self.update_limit_order(obj=obj, 
                                        size=size, 
                                        buy_sell=buy_sell, 
                                        price=placeholder_price)
        
        if trade is not None:
            obj.strat_on_close_update = False 
            
            if self.print_orders:
                self.print_order_message(buy_sell, size, obj.my_fi_name, placeholder_price, trade.order.orderId)

            obj.active_base_price = mkt_close 
            self._placed_order_admin(obj, trade)


    def on_mkt_data_update(self, input_obj):

        output_obj  = input_obj.opp_obj
        if not input_obj.is_mkt_data_valid() or not output_obj.is_mkt_data_valid():
            return

        active_base_price = output_obj.active_base_price
        input_price = getattr(input_obj, input_obj.input_price_attr)
        if active_base_price is not None and abs(input_price - active_base_price) < 1e-9:
            return

        output_price = output_obj.calc_price(input_price, output_obj) 
        active_order_price = output_obj.trade.order.lmtPrice if output_obj.trade is not None else None
        if active_order_price is not None and abs(output_price - active_order_price) < 1e-9:
            return     
        
        trade = output_obj.platform_obj.modify_limit_order(obj=output_obj, 
                                                           size=output_obj.order_size, 
                                                           buy_sell=output_obj.buy_sell, 
                                                           trade=output_obj.trade, 
                                                           price=output_price)

        if trade is not None:
            output_obj.active_base_price = input_price
            self._placed_order_admin(output_obj, trade)
            
            if self.print_orders:
                self.print_order_message(output_obj.buy_sell, 
                                         output_obj.order_size, 
                                         output_obj.my_fi_name, 
                                         output_price, 
                                         trade.order.orderId)
       
 
    async def on_trade_exec(self, filled_obj, filled_order):  
        # print(filled_order, '\n')
        status = filled_order.orderStatus

        filled = status.filled
        if filled == 0:   # this will be the case many times
            return
        
        remaining = status.remaining
        
        unfilled_obj = filled_obj.opp_obj
        
        if self.trade_has_been_cancelled:
            return self._filled_after_cancellation(filled_obj, unfilled_obj, filled_order, remaining)
        
        return self._filled_before_cancellation(filled_obj, unfilled_obj, filled_order, remaining)
        

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
        self.on_trade_exec_modify_unfilled_order(unfilled_obj, filled_order) # see specialty code

        filled_obj.trading_complete    = True
        filled_obj.strat_on_trade_exec = False
        filled_obj.strat_on_mkt_data   = False
        unfilled_obj.strat_on_mkt_data = False

        self._finished_order_admin(filled_obj, filled_order)  


    def _filled_before_cancellation_partially_opp_obj_trading_incomplete(self, filled_obj, unfilled_obj, filled_order):
        self.cancel_order(filled_obj, filled_order)

        pct_filled = filled_order.orderStatus.filled / filled_obj.initial_screens_order_size
        unfilled_obj.order_size = unfilled_obj.round_size_to_increment(unfilled_obj.order_size * pct_filled)

        self.on_trade_exec_modify_unfilled_order(unfilled_obj, filled_order) # see specialty code

        self.trade_has_been_cancelled= True


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
        
        # neither object has any active trades outstanding
        for object in [filled_obj, unfilled_obj]:
            object.trading_complete    = True
            object.strat_on_trade_exec = False
            object.strat_on_mkt_data   = False

        self._finish_routine()

        
    def _placed_order_admin(self, obj, trade):   
        if trade not in obj.active_trade_list:
            obj.active_trade_list.append(trade)

        self._update_trading_amounts(obj)    
        

    def _finished_order_admin(self, obj, trade):
        if trade in obj.active_trade_list:
            obj.active_trade_list.remove(trade)

        if trade not in obj.inactive_trade_list:
            obj.inactive_trade_list.append(trade)

        self._update_trading_amounts(obj)


    def _update_trading_amounts(self, obj):
        print(obj.my_fi_name, obj.active_trade_list, obj.inactive_trade_list)

        obj.active_screens = sum(t.orderStatus.filled for t in obj.active_trade_list)
        obj.active_units   = obj.active_screens * obj.scalar_units_per_screen

        obj.traded_screens = sum(t.orderStatus.filled for t in obj.inactive_trade_list)
        obj.traded_units   = obj.traded_screens * obj.scalar_units_per_screen
        
        obj.active_plus_traded_units = obj.active_units + obj.traded_units


    def _finish_routine(self):
        self._finalize_results()

        # if using event:
        if self.done_event is not None:
            self.done_event.set()


    def _finalize_results(self):
        final_spread = (self.obj2.trade.orderStatus.avgFillPrice * self.obj2.spread_ratio * self.obj2.filled_scalar + 
                        self.obj1.trade.orderStatus.avgFillPrice * self.obj1.spread_ratio * self.obj1.filled_scalar)  
        
        self.obj1.units_filled = self.obj1.trade.orderStatus.filled * self.obj1.scalar_units_per_screen
        self.obj2.units_filled = self.obj2.trade.orderStatus.filled * self.obj2.scalar_units_per_screen 
        net_units = self.obj1.units_filled - self.obj2.units_filled

        print("\nTRADE PACKAGE FINISHED")
        print("----------------------")
    
        for obj in [self.obj1, self.obj2]:
            print(
                obj.my_fi_name,
                obj.buy_sell,
                ", order_id:", obj.trade.order.orderId,
                ", status:", obj.trade.orderStatus.status,
                ", filled:", obj.trade.orderStatus.filled,
                ", units:", obj.units_filled,
                ", avg_price:", obj.trade.orderStatus.avgFillPrice,
                ", last_price:", obj.trade.orderStatus.lastFillPrice,
            )

        print('Final spread: ', final_spread, 'Net open units: ', net_units, '\n')

        
    def _calc_price_amount(self, unit_input_price, output_obj, epsilon_scalar=0):     
        unit_fair_value   = output_obj.adj_spread - (unit_input_price * output_obj.spread_ratio)
        unit_output_price = unit_fair_value - (epsilon_scalar * self.epsilon)
        mkt_output_price = unit_output_price * output_obj.scalar_units_per_self
        mkt_output_price = output_obj.round_price_to_tick(abs(mkt_output_price))    
        # print(unit_input_price, unit_fair_value, mkt_output_price)                                         
        return mkt_output_price
    

    def _calc_price_pct():
        pass

    