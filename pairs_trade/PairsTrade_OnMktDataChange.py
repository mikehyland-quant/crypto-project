
import asyncio

# handles the on market data change event and updates the trades accordingly
class PairsTrade_OnMktDataChange:

# ============================================================
# THIS CODE ALLOWS FOR ONLY THE MOST RECENT UPDATES TO BE PROCESSED
# ============================================================

    def prepare_on_mkt_data_change(self):
        self.pending_mkt_data_objs = set()
 
        self.need_to_update        = False
        self.is_update_in_progress = False

        self.update_task           = None


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

# ============================================================
# THIS CODE ACTUALLY UPDATES THE OUTPUT PRICES BASED ON THE NEW INPUT PRICES
# ============================================================

    async def _update_trade(self, input_obj):

        output_obj  = input_obj.opp_obj
        if not input_obj.is_mkt_data_valid() or not output_obj.is_mkt_data_valid():
            return

        input_cf = getattr(input_obj, input_obj.input_price_attr)
        active_base_price = output_obj.primary_trade_base_price
        if active_base_price is not None and abs(input_price - active_base_price) < 1e-9:
            return

output_cf = margin - input_cf 
output_price = obj.decompose_unit_cf(output_cf_cf, 'taker')
output_price = obj.round_price_to_tick(abs(output_price[0]), buy_sell)

      #  output_price = self._calc_price(input_price, output_obj)
        active_order_price = output_obj.primary_trade_order_price
        if active_order_price is not None and abs(output_price - active_order_price) < 1e-9:
            return     
        
        trade = self.update_limit_order(obj=output_obj, 
                                        trade=output_obj.primary_trade, 
                                        price=output_price)
 
        if trade is not None:
            self._primary_trade_placed_order_admin(output_obj, trade, input_price, output_price)
            self._placed_order_admin(output_obj, trade, output_obj.primary_trade_initial_order_size, output_price)



    