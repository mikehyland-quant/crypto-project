
import asyncio

from strategies.Strategy_Parent import Strategy
from strategies.Strategy_PairsTrade_OnMktDataHotPath import PairsTrade_OnMktDataHotPath
from strategies.Strategy_PairsTrade_OnTradeExecHotPath import PairsTrade_OnTradeExecHotPath


class PairsTrade_Parent(PairsTrade_OnMktDataHotPath,
                        PairsTrade_OnTradeExecHotPath, 
                        Strategy):

    def __init__(self, objs_list, df):
        super().__init__(objs_list, df)
        
        # create self attributes
        self.no_partial_trades_yet = True

        self.target_spread = float(df.loc['target_profit_per_unit'].sum())
        self.epsilon       = float(df.loc['epsilon_per_unit'].sum())
        
        df = df.drop(index=['target_profit_per_unit', 'epsilon_per_unit'], errors='ignore')

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
    
            setattr(self, obj_name.lower(), obj)
     
            for attr_key, attr_val in obj_dict.items():
                setattr(obj, attr_key, attr_val)
    
        return self.obj1, self.obj2
 
 
    def _attach_strat_attr(self, objs_list):
        buy_tuple      = ('BUY',  'cf_unit_lift_ask', -1)
        sell_tuple     = ('SELL', 'cf_unit_hit_bid',   1)
        min_ratio_size = min(self.obj1.ratio_size, self.obj2.ratio_size)
        
        for obj in objs_list:
            obj.active_base_price  = None
            obj.active_order_price = None

            if obj.initial_order_size_units > 0:
                (obj.buy_sell, obj.input_price_attr, obj.filled_scalar) = buy_tuple 
            elif obj.initial_order_size_units < 0:
                (obj.buy_sell, obj.input_price_attr, obj.filled_scalar) = sell_tuple  

            obj.on_mkt_data_change_order_size = obj.round_size_to_increment(abs(obj.initial_order_size_units *
                                                                                obj.scalar_size_orders_per_unit))
                                                                
            obj.spread_ratio = obj.opp_obj.ratio_size / min_ratio_size
            obj.adj_spread   = self.target_spread / obj.spread_ratio
    
            if obj.active_passive.lower() == 'passive':
                #was set to True in Strategy_Parent, so now set to False for passive leg
                setattr(obj.opp_obj, 'strat_on_mkt_data_change', False)   

        return self.obj1, self.obj2
                    

    def on_closing_price_update(self, obj):
        #creates a placeholder limit order to get trade opened and in system
        mkt_close = obj.price_screen_close

        if obj.buy_sell == 'BUY':
            placeholder_price = mkt_close * 0.5
        elif obj.buy_sell == 'SELL': 
            placeholder_price = mkt_close * 2.0

        placeholder_price = obj.round_price_to_tick(placeholder_price)

        size = obj.on_mkt_data_change_order_size
        buy_sell = obj.buy_sell
 
        trade = self.update_limit_order(obj=obj, 
                                        size=size, 
                                        buy_sell=buy_sell, 
                                        price=placeholder_price)
        
        if trade is not None:
            self._on_mkt_data_change_placed_order_admin(obj, trade, placeholder_price, placeholder_price)  # don't use market price as that may slow down hot path
            self._placed_order_admin(obj, trade)
            obj.strat_on_closing_price_update = False
            

    def _on_mkt_data_change_placed_order_admin(self, obj, trade, active_base_price, active_order_price):
        obj.on_mkt_data_change_trade = trade
        obj.active_base_price        = active_base_price  
        obj.active_order_price       = active_order_price

    
    def _placed_order_admin(self, obj, trade):
        if trade not in obj.active_trade_list:
            obj.active_trade_list.append(trade)

        self._update_trading_amounts(obj)

        if self.need_to_print_active_orders:
            self.print_orders("active",
                              trade.order.action, 
                              trade.order.totalQuantity, 
                              obj.my_fi_name, 
                              trade.order.lmtPrice, 
                              trade.order.orderId)


    def _finished_order_admin(self, obj, trade):
        if trade in obj.active_trade_list:
            obj.active_trade_list.remove(trade)

        if trade not in obj.finished_trade_list:
            obj.finished_trade_list.append(trade)

        self._update_trading_amounts(obj)

        if self.need_to_print_finished_orders:
            self.print_orders("finished",
                              trade.order.action, 
                              trade.orderStatus.filled, 
                              obj.my_fi_name, 
                              trade.orderStatus.avgFillPrice, 
                              trade.order.orderId)


    def _update_trading_amounts(self, obj):
        # print(obj.my_fi_name, obj.active_trade_list, obj.inactive_trade_list)

        obj.active_orders = sum(t.orderStatus.filled for t in obj.active_trade_list)
        obj.active_units  = obj.active_orders * obj.scalar_size_units_per_order

        obj.traded_orders = sum(t.orderStatus.filled for t in obj.finished_trade_list)
        obj.traded_units  = obj.traded_orders * obj.scalar_size_units_per_order
        
        obj.active_plus_traded_units = obj.active_units + obj.traded_units


    def _finish_routine(self):
        self._finalize_results()

        # if using event:
        if self.done_event is not None:
            self.done_event.set()


    def _finalize_results(self):
        print("\nTRADE PACKAGE FINISHED")
        print("----------------------")

        for obj in [self.obj1, self.obj2]:
            obj.total_orders_filled, obj.final_avg_FI_price    = self.calc_final_fills_and_avg_price(obj)
            obj.total_units_filled   = obj.total_orders_filled * obj.scalar_size_units_per_order
            obj.final_avg_unit_price = obj.final_avg_FI_price  * obj.scalar_size_FIs_per_unit

            print(
                obj.my_fi_name,
                obj.buy_sell,
                ", filled_orders:", obj.total_orders_filled,
                ", filled_units:", obj.total_units_filled,
                ", avg_FI_price:", obj.final_avg_FI_price,
                ", avg_unit_price:", obj.final_avg_unit_price
            )
        
        final_spread = (self.obj2.final_avg_unit_price * self.obj2.spread_ratio * self.obj2.filled_scalar + 
                        self.obj1.final_avg_unit_price * self.obj1.spread_ratio * self.obj1.filled_scalar)  
        
        net_units = self.obj1.total_units_filled - self.obj2.total_units_filled

        print('Final spread: ', final_spread, ', Net open units: ', net_units, '\n')

        
    def _calc_price_amount(self, unit_input_price, output_obj, epsilon_scalar=0):
        unit_fair_value   = output_obj.adj_spread - (unit_input_price * output_obj.spread_ratio)
        unit_output_price = unit_fair_value - (epsilon_scalar * self.epsilon)
        mkt_output_price  = unit_output_price * output_obj.scalar_size_units_per_FI
        mkt_output_price  = output_obj.round_price_to_tick(abs(mkt_output_price))    
        # print(unit_input_price, unit_fair_value, mkt_output_price)                                         
        return mkt_output_price
    

    def _calc_price_pct(self):
        pass

    