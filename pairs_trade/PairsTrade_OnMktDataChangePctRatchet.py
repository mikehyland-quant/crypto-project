
import asyncio


# handles the on market data change event and updates the trades accordingly
class PairsTrade_OnMktDataChangePctRatchet:


    def prepare_on_mkt_data_change(self):
        self.pending_mkt_data_objs = set()
 
        self.need_to_update        = False
        self.is_update_in_progress = False

        self.update_task           = None


    def prepare_on_mkt_data_change_objs(self, objs_list):

        for obj in objs_list:
            if obj.buy_sell == "BUY":
                obj.price_calc_scalar = 1 + self.target_spread
            elif obj.buy_sell == "SELL":
                obj.price_calc_scalar = 1 / (1 + self.target_spread)

            if obj.active_passive.lower() == 'active':
                obj.actively_updating_mkt_data = True
                obj.need_to_save_closing_price = False
                obj.strat_on_closing_price     = False

                order = obj.platform_obj.LimitOrder(action=obj.buy_sell, 
                                           totalQuantity=obj.primary_trade_initial_order_size, 
                                           lmtPrice=price)
        
                obj.primary_trade = order


    def on_mkt_data_change(self, obj):
        self.pending_mkt_data_objs.add(obj)
        self.need_to_update = True

        if self.is_update_in_progress:
            return

        self.is_update_in_progress = True
        
        self.update_task = asyncio.create_task(self._update_trade_worker())


    async def _update_trade_worker(self):
        try:
            while True:
                self.need_to_update = False

                pending_objs = list(self.pending_mkt_data_objs)
                self.pending_mkt_data_objs.clear()

                for obj in pending_objs:
                    await self._update_trade(obj)

                if not self.need_to_update:  
                    break
        finally:
            self.is_update_in_progress = False


    async def _update_trade(self, input_obj):

        output_obj  = input_obj.opp_obj
        if not input_obj.is_mkt_data_valid() or not output_obj.is_mkt_data_valid():
            return

        input_price = getattr(input_obj, input_obj.input_price_attr)
        if input_price is None:
            return
        
        active_base_price = output_obj.primary_trade_base_price
        buy_sell = output_obj.buy_sell

        if active_base_price is not None and buy_sell == "SELL" and (input_price <= active_base_price):
            return
        if active_base_price is not None and buy_sell == "BUY"  and (input_price >= active_base_price):
            return

        output_price = self._calc_price(input_price, output_obj)
        if output_price is None:
            return
        
        active_order_price = output_obj.primary_trade_order_price

        if active_order_price is not None and buy_sell == "SELL" and (output_price <= active_order_price):
            return
        if active_order_price is not None and buy_sell == "BUY"  and (output_price >= active_order_price):
            return
        
        trade = self.update_limit_order(obj=output_obj, 
                                        trade=output_obj.primary_trade, 
                                        price=output_price)
 
        if trade is not None:
            self._primary_trade_placed_order_admin(output_obj, trade, input_price, output_price)
            self._placed_order_admin(output_obj, trade, output_obj.primary_trade_initial_order_size, output_price)



    def _calc_price(self, unit_input_price, output_obj, epsilon_scalar=0):
        # unit_fair_value   = output_obj.adj_spread - (unit_input_price * (1 + output_obj.spread_ratio))
        unit_output_price = unit_input_price * output_obj.price_calc_scalar
        mkt_output_price  = unit_output_price * output_obj.scalar_size_units_per_FI
        mkt_output_price  = output_obj.round_price_to_tick(abs(mkt_output_price))    
        # print(unit_input_price, unit_fair_value, mkt_output_price)                                         
        return mkt_output_price

    