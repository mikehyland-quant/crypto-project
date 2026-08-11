
from strategies.Strategy_Parent             import Strategy_Parent
from group_trade.GroupTrade_OnClosingPrice  import GroupTrade_OnClosingPrice
from group_trade.GroupTrade_OnMktDataChange import GroupTrade_OnMktDataChange
from group_trade.GroupTrade_OnTradeExec     import GroupTrade_OnTradeExec


class GroupTrade_Parent(GroupTrade_OnClosingPrice,
                        GroupTrade_OnMktDataChange,
                        GroupTrade_OnTradeExec,
                        Strategy_Parent):
    
    def __init__(self, bo_objs):
        super().__init__(bo_objs.objs_list)  # this calls Strategy_Parent.__init__() 
        
        # create self attributes
        self.prepare_on_mkt_data_change()

        anchor_fi = next(obj for obj in objs_list if getattr(obj, "anchor_t/f"))
        anchor_size = anchor_fi.tgt_anchor_units * anchor_fi.scalar_size_FIs_per_unit

        # attach attributes to objs
        for obj in self.objs_list:
            obj.base_size = anchor_size * obj.scalar_size_FIs_per_unit

            obj.buy_size = obj.base_size + obj.extra_shs
            obj.sell_size = obj.base_size - obj.extra_shs

            obj.buy_size = obj.round_size_to_increment(obj.buy_size)
            obj.sell_size = obj.round_size_to_increment(obj.sell_size)

            obj.buy_trade = None
            obj.sell_trade = None

            obj.buy_trade_input_price = None
            obj_sell_trade_input_price = None

            obj.buy_trade_order_price = None
            obj.sell_trade_order_price = None

    
    def _placed_order_admin(self, obj, trade, base_price, order_price):
        obj.primary_trade              = trade
        obj.primary_trade_base_price   = base_price  
        obj.primary_trade_order_price  = order_price

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
                ", filled_orders:",     obj.total_orders_filled,
                ", filled_units:",   f'{obj.total_units_filled:.2f}',
                ", avg_FI_price:",   f'{obj.final_avg_FI_price:.2f}',
                ", avg_unit_price:", f'{obj.final_avg_unit_price:.2f}'
            )
        
        final_spread = (self.obj2.final_avg_unit_price * self.obj2.spread_ratio * self.obj2.fimal_spread_scalar + 
                        self.obj1.final_avg_unit_price * self.obj1.spread_ratio * self.obj1.final_spread_scalar)  
        
        net_units = self.obj1.total_units_filled - self.obj2.total_units_filled

        print('Final spread: ', f'{final_spread:.2f}', ', Net open units: ', f'{net_units:.2f}', '\n')

        
