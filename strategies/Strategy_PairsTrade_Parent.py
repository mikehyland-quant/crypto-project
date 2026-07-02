
import asyncio

from strategies.Strategy_Parent import Strategy
from strategies.Strategy_PairsTrade_OnMktDataHotPath import PairsTrade_OnMktDataHotPath
from strategies.Strategy_PairsTrade_OnTradeExecHotPath import PairsTrade_OnTradeExecHotPath


class PairsTrade_Parent(PairsTrade_OnMktDataHotPath,
                        PairsTrade_OnTradeExecHotPath,
                        Strategy):
    def __init__(self, objs_list, df):
        super().__init__(objs_list=objs_list, df=df)
        
        # create self attributes
        self.no_partial_trades_yet = True

        self.trades_by_orderId_dict = {}

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
            obj.spread_ratio = obj.opp_obj.ratio_size / min_ratio_size
            obj.adj_spread   = self.target_spread     / obj.spread_ratio

            if obj.initial_order_size_units > 0:
                (obj.buy_sell, obj.input_price_attr, obj.filled_scalar) = buy_tuple 
            elif obj.initial_order_size_units < 0:
                (obj.buy_sell, obj.input_price_attr, obj.filled_scalar) = sell_tuple  

            obj.initial_order_size_units = abs(obj.initial_order_size_units)

            obj.primary_trade                    = None
            obj.primary_trade_base_price         = None
            obj.primary_trade_order_price        = None
            obj.primary_trade_initial_order_size = obj.round_size_to_increment(obj.initial_order_size_units *
                                                                               obj.scalar_size_orders_per_unit)
            
            
            obj.trades_by_orderId = {}
                                                                
            if obj.active_passive.lower() == 'passive':
                #was set to True in Strategy_Parent, so now set to False for passive leg
                setattr(obj.opp_obj, 'strat_on_mkt_data_change', False)   

        return self.obj1, self.obj2
                    

    def on_closing_price_update(self, obj):
        #creates a placeholder limit order to get trade opened and in system
        mkt_close = obj.price_screen_close

        buy_sell = obj.buy_sell
        if buy_sell == 'BUY':
            placeholder_price = mkt_close * 0.5
        elif buy_sell == 'SELL': 
            placeholder_price = mkt_close * 2.0
        else:
            raise ValueError(f"Invalid buy_sell value: {buy_sell}")
        placeholder_price = obj.round_price_to_tick(placeholder_price)

        size = obj.primary_trade_initial_order_size
        trade = self.update_limit_order(obj=obj, 
                                        buy_sell=buy_sell, 
                                        price=placeholder_price,
                                        size=size)

        if trade is not None:
            self._primary_trade_placed_order_admin(obj, trade, placeholder_price, placeholder_price)  # don't use market price as that may slow down hot path
            self._placed_order_admin(obj, trade, size, placeholder_price)

            obj.strat_on_closing_price_update = False
         

    def prep_and_launch_balancing_order(self, net_units):
        if net_units > 0:
            order_obj = self.obj2
        else:
            order_obj = self.obj1

        size = order_obj.round_size_to_increment(abs(net_units) * order_obj.scalar_size_orders_per_unit)

        trade = self.launch_balancing_order(order_obj, size)

    
    def _primary_trade_placed_order_admin(self, obj, trade, base_price, order_price):
        obj.primary_trade              = trade
        obj.primary_trade_base_price   = base_price  
        obj.primary_trade_order_price  = order_price

    
    def _placed_order_admin(self, obj, trade, size, price):
        trade_order = trade.order

        filled = trade.orderStatus.filled

        order_id = trade_order.orderId
        obj.trades_by_orderId[order_id] = {'active'        : True,
                                           'intended_size' : max(size, filled),
                                           "filled_size"   : filled}

        self._update_trading_amounts(obj)

        if self.need_to_print_active_orders:
            self.print_orders("active",
                              trade_order.action, 
                              size, 
                              obj.my_fi_name,
                              price, 
                              order_id)


    def _finished_order_admin(self, obj, trade):
        obj.finished_trade_dict[trade.order.orderId] = trade

        trade_order       = trade.order
        trade_orderStatus = trade.orderStatus

        order_id   = trade_order.orderId
        trade_size = trade_orderStatus.filled

        obj.trades_by_orderId[order_id] = {'active'        : False,
                                           'intended_size' : None,
                                           'filled_size'   : trade_size}

        self._update_trading_amounts(obj)

        if self.need_to_print_finished_orders:
            self.print_orders("finished",
                              trade_order.action, 
                              trade_size, 
                              obj.my_fi_name, 
                              trade_orderStatus.avgFillPrice, 
                              order_id)
            
        if not obj.strat_on_trade_exec and not obj.opp_obj.strat_on_trade_exec:
            self.finish_strategy()


    def _update_trading_amounts(self, obj):
        obj.active_orders = sum(
                rec["intended_size"] for rec in obj.trades_by_orderId.values() if rec["active"])

        obj.traded_orders = sum(
                rec["filled_size"] for rec in obj.trades_by_orderId.values() if not rec["active"])

        obj.active_plus_traded_units = (obj.active_orders + obj.traded_orders) * obj.scalar_size_units_per_order


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
                ", filled_units:", f'{obj.total_units_filled:.2f}',
                ", avg_FI_price:", f'{obj.final_avg_FI_price:.2f}',
                ", avg_unit_price:", f'{obj.final_avg_unit_price:.2f}'
            )
        
        final_spread = (self.obj2.final_avg_unit_price * self.obj2.spread_ratio * self.obj2.filled_scalar + 
                        self.obj1.final_avg_unit_price * self.obj1.spread_ratio * self.obj1.filled_scalar)  
        
        net_units = self.obj1.total_units_filled - self.obj2.total_units_filled

        print('Final spread: ', f'{final_spread:.2f}', ', Net open units: ', f'{net_units:.2f}', '\n')

        
    def _calc_price_amount(self, unit_input_price, output_obj, epsilon_scalar=0):
        unit_fair_value   = output_obj.adj_spread - (unit_input_price * output_obj.spread_ratio)
        unit_output_price = unit_fair_value - (epsilon_scalar * self.epsilon)
        mkt_output_price  = unit_output_price * output_obj.scalar_size_units_per_FI
        mkt_output_price  = output_obj.round_price_to_tick(abs(mkt_output_price))    
        # print(unit_input_price, unit_fair_value, mkt_output_price)                                         
        return mkt_output_price
    

    def _calc_price_pct(self):
        pass

    