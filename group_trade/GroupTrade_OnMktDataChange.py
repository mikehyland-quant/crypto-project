
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
# two "XXX" 
    async def _update_trade(self, x):
        bo_obj = self.bo_obj

        # if not bo_obj.is_mkt_data_valid():
          #  return
        
        bo_obj_strat_bid = bo_obj.strat_bid
        bo_obj_strat_ask = bo_obj.strat_ask

        for obj in self.objs_list:
            profit_tgt = self.calc_profit_tgt(obj, bo_obj_strat_bid, bo_obj_strat_ask)
            self.create_trade(obj, "BUY", profit_tgt, bo_obj_strat_bid)
            self.create_trade(obj, "SELL", profit_tgt, bo_obj_strat_ask)


    def calc_profit_tgt(self, obj, bid, ask):
        if obj.tgt_profit_units == 'amt':
            return obj.tgt_profit_constant
        elif obj.tgt_profit_units == 'pct':
            bo_obj_avg_price = (abs(bid) + abs(ask)) / 2
            return bo_obj_avg_price * obj.tgt_profit_constant


    def create_trade(self, obj, buy_sell, profit_tgt, bo_obj_price):
        if buy_sell == 'BUY':
            prev_trade = obj.buy_trade
            prev_input_price = obj.XXXXX
        elif buy_sell == 'SELL':
            prev_trade = obj.sell_trade
            prev_input_price = obj.XXXXX

        if bo_obj_price != prev_input_price:
            new_unit_price = profit_tgt - bo_obj_price
            new_fi_price = obj.decompose_unit_cf(new_unit_price, 'taker')
            new_fi_price = obj.round_price_to_tick(abs(new_fi_price[0]), buy_sell)


            trade = None
            '''
            trade = self.update_limit_order(obj=obj, 
                                            trade=obj.buy_trade, 
                                            price=new_fi_price)
            '''



            
            if trade is not None:
                self._placed_order_admin(obj, trade, bo_obj_price)




            

        