
import asyncio


class PairsTrade_OnMktDataHotPath:

    def on_mkt_data_update(self, input_obj):
        self.pending_mkt_data_objs.add(input_obj)
        self.need_to_update_on_mkt_data_trade = True

        if self.update_on_mkt_data_trade_in_progress:
            return

        self.update_on_mkt_data_trade_in_progress = True
        
        self.update_on_mkt_data_trade_task = asyncio.create_task(self._update_on_mkt_data_trade_worker())


    async def _update_on_mkt_data_trade_worker(self):
        try:
            while True:
                self.need_to_update_on_mkt_data_trade = False

                pending_objs = list(self.pending_mkt_data_objs)
                self.pending_mkt_data_objs.clear()

                for input_obj in pending_objs:
                    await self._update_on_mkt_data_trade(input_obj)

                if not self.need_to_update_on_mkt_data_trade:
                    break

        finally:
            self.update_on_mkt_data_trade_in_progress = False


    async def _update_on_mkt_data_trade(self, input_obj):

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
        
        trade = self.update_limit_order(obj=output_obj, 
                                        trade=output_obj.initial_trade, 
                                        price=output_price)
        
        if trade is not None:
            output_obj.initial_trade = trade
            output_obj.active_base_price = input_price
            self._placed_order_admin(output_obj, trade)
       