
# creates a placeholder limit order to get trade opened and in system
class PairsTrade_OnClosingPrice:
    

    def on_closing_price(self, obj):

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

            obj.strat_on_closing_price = False
         