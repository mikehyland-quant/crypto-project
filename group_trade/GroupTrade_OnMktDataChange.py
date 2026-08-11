
import asyncio

# handles the on market data change event and updates the trades accordingly
class GroupTrade_OnMktDataChange:

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
# THIS CODE AACTUALLY UPDATES THE OUTPUT PRICES BASED ON THE NEW INPUT PRICES
# ============================================================

    async def _update_trade(self, input_obj):
        bo_obj = self.bo_obj

        if not bo_obj.is_mkt_data_valid():
            return
        
        bo_obj_best_bid_cf = bo_obj.XXX
        bo_obj_best_ask_cf = bo_obj.XXX
        bo_obj_avg_price = (abs(bo_obj_best_bid_cf) + abs(bo_obj_best_ask_cf)) / 2

        for obj in self.objs_list:

            obj.bid_ask_spread = obj.price_screen_ask - obj.price_screen_bid

            if obj.tgt_profit_units == 'amt':
                profit_tgt = obj.tgt_profit_constant
            elif obj.tgt_profit_units == 'pct':
                profit_tgt = bo_obj_avg_price * obj.tgt_profit_constant

            if bo_obj_best_bid_cf != XXX:
                new_unit_bid = profit_tgt - bo_obj_best_bid_cf
                new_fi_bid = obj.decompose_unit_cf(new_unit_bid, 'taker')
                new_fi_bid = obj.round_price_to_tick(abs(new_fi_bid[0]), 'BUY')

                buy_trade = self.update_limit_order(obj=obj, 
                                                    trade=obj.buy_trade, 
                                                    price=new_fi_bid)

                if buy_trade is not None:
                    setattr(obj, 'buy_trade', buy_trade)
                    self._primary_trade_placed_order_admin(obj, buy_trade, new_fi_bid, bo_obj_best_bid_cf)  # don't use market price as that may slow down hot path
                    self._placed_order_admin(obj, trade, size, price)

            if bo_obj_best_ask_cf != XXX:
                new_unit_ask = profit_tgt - bo_obj_best_ask_cf
                new_fi_ask = obj.obj.decompose_unit_cf(new_unit_ask, 'taker')
                new_fi_ask = obj.round_price_to_tick(abs(new_fi_ask[0]), 'SELL')

                sell_trade = self.update_limit_order(obj=obj, 
                                                    trade=obj.sell_trade, 
                                                    price=new_fi_ask)

                if sell_trade is not None:
                    setattr(obj, 'sell_trade', trade)
                    self._primary_trade_placed_order_admin(obj, sell_trade, new_fi_ask, bo_obj_best_ask_cf)  # don't use market price as that may slow down hot path
                    self._placed_order_admin(obj, trade, size, price)
            

        