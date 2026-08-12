
# creates a placeholder limit order to get trade opened and in system
class GroupTrade_OnClosingPrice:

    def on_closing_price(self, obj):
        mkt_close = obj.price_screen_close

        orders_placed = 0

        for action in ['BUY', 'SELL']:
 
            if action == 'BUY':
                price = mkt_close * 0.5
                size = obj.buy_size
            else: # action == 'SELL'
                price = mkt_close * 2.0
                size = obj.sell_size

            price = obj.round_price_to_tick(price, action)

            trade = self.update_limit_order(obj=obj, 
                                            buy_sell=action, 
                                            price=price,
                                            size=size, 
                                            all_or_none=True)

            if trade is not None:
                self._placed_order_admin(obj, trade, mkt_close)
                orders_placed += 1

        if orders_placed == 2:
            obj.strat_on_closing_price = False
