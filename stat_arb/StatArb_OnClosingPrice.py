
# creates a placeholder limit order to get trade opened and in system
class StatArb_OnClosingPrice():

    def on_closing_price(self, obj):
        mkt_close = obj.price_screen_close

        orders_placed = 0

        if self.g_or_p == "group":
            buy_sell_list = ['BUY', 'SELL']
        else: # pairs
            buy_sell = obj.buy_or_sell
            buy_sell_list = [buy_sell.upper()]
            setattr(obj, f"{buy_sell.lower()}_size", obj.size)

        for buy_sell in buy_sell_list:
 
            if buy_sell == 'BUY':
                price = mkt_close * 0.5
                size = obj.buy_size
            else: # buy_sell == 'SELL'
                price = mkt_close * 2.0
                size = obj.sell_size

            price = obj.round_price_to_tick(price, buy_sell)

            trade = self.update_limit_order(obj=obj, 
                                            buy_sell=buy_sell, 
                                            price=price,
                                            size=size, 
                                            # all_or_none=True
                                            )

            if trade is not None:
                self._placed_order_admin(obj, trade, mkt_close)
                orders_placed += 1

        if orders_placed == len(buy_sell_list):
            obj.strat_on_closing_price = False


