
# creates a placeholder limit order to get trade opened and in system
class GroupTrade_OnClosingPrice:

    def on_closing_price(self, obj):
        size = obj.order_size
        mkt_close = obj.price_screen_close

        orders_placed = 0

        for action in ['BUY', 'SELL']:

            if action == 'BUY':
                price = mkt_close * 0.5
            else: # action == 'SELL'
                price = mkt_close * 2.0

            price = obj.round_price_to_tick(price, action)

            trade = self.update_limit_order(obj=obj, 
                                            buy_sell=action, 
                                            price=price,
                                            size=size, 
                                            all_or_none=True)

            if trade is not None:
                setattr(obj, action.lower() + '_trade', trade)
                self._primary_trade_placed_order_admin(obj, trade, price, price)  # don't use market price as that may slow down hot path
                self._placed_order_admin(obj, trade, size, price)

                orders_placed += 1

        if orders_placed == 2:
            obj.strat_on_closing_price = False
