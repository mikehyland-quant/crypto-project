
import asyncio

from strategies.Strategy_Parent import Strategy

class BestOfStrat(Strategy):

    def __init__(self, bo_obj, unit_size=0.1, safety_margin=0.01):
        super().__init__(bo_obj.objs_list)  
           
        self.bo_obj = bo_obj
        
        # attach attributes to objs in bo_obj 
        for obj in bo_obj.objs_list:
            self._attach_attr(obj, unit_size, safety_margin)
                
  
    def _attach_attr(self, obj, unit_size, safety_margin):
        obj.trade_buy  = None  
        obj.trade_sell = None

        obj.min_profit = obj.scalar_size_mkt_to_unit * safety_margin
        obj.order_size = obj.round_size_to_increment(abs(obj.scalar_size_mkt_to_unit) * unit_size)
        
        
    def on_close_data(self, obj):
        # from MktData.on_close_data()
        mkt_close = obj.price_mkt_close

        price = obj.round_price_to_tick(0.5 * mkt_close, "BUY")
        buy_trade = obj.platform_obj.place_limit_order(obj=obj, 
                                                       buy_sell="BUY", 
                                                       price=price, 
                                                       size=obj.order_size)
                    
        if buy_trade is not None:
            obj.trade_buy = buy_trade
            if self.print_orders:
                self.print_order_message("BUY", 
                                         obj.order_size, 
                                         obj.my_fi_name, 
                                         price, 
                                         buy_trade.order.orderId)   
        
        price = obj.round_price_to_tick(2.0 * mkt_close, "SELL")
        sell_trade = obj.platform_obj.place_limit_order(obj=obj, 
                                                        buy_sell="SELL", 
                                                        price=price, 
                                                        size=obj.order_size)  
        
        if sell_trade is not None:
            obj.trade_sell = sell_trade
            if self.print_orders:
                self.print_order_message("SELL", 
                                         obj.order_size, 
                                         obj.my_fi_name, 
                                         price, 
                                         sell_trade.order.orderId)   
                         
        if buy_trade is not None and sell_trade is not None:
            obj.strat_on_close_data = False 
            
            
    def on_mkt_data(self, x):
        # from MktData.on_mkt_data()
        
        buy_obj  = self.bo_obj.cf_unit_lift_ask_net_obj
        sell_obj = self.bo_obj.cf_unit_hit_bid_net_obj
        
        net_amt    = self.bo_obj.cf_unit_lift_ask_net + self.bo_obj.cf_unit_hit_bid_net
        min_profit = buy_obj.min_profit + sell_obj.min_profit

        print(net_amt, min_profit)

        if net_amt < min_profit:
            return
        
        buy_trade = buy_obj.platform_obj.modify_limit_order(obj=buy_obj,
                                                            size=buy_obj.order_size,
                                                            buy_sell="BUY",
                                                            trade=buy_obj.trade_buy,
                                                            price=buy_obj.price_mkt_ask)
        
        sell_trade = sell_obj.platform_obj.modify_limit_order(obj=sell_obj,
                                                              size=sell_obj.order_size,
                                                              buy_sell="SELL",
                                                              trade=sell_obj.trade_sell,
                                                              price=sell_obj.price_mkt_bid)   

        print(buy_obj.price_mkt_ask, sell_obj.price_mkt_bid)    

        buy_obj.trade_buy   = buy_trade
        sell_obj.trade_sell = sell_trade

        self.active_trades = [buy_trade, sell_trade]

        for obj in self.bo_obj.objs_list:
            obj.strat_on_mkt_data = False
            if obj.trade_buy != buy_trade:
                obj.platform_obj.cancel_trade(obj.trade_buy)
            if obj.trade_sell != sell_trade:
                obj.platform_obj.cancel_trade(obj.trade_sell)
            
    
    async def on_trade_exec(self, filled_obj, filled_trade):
        if filled_trade in self.active_orders:
            self.active_orders.pop(filled_trade)
            filled_obj.strat_on_trade_exec = False
            
            if not self.active_orders:
                pass

