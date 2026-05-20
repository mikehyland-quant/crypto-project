
import asyncio

#from datetime import datetime
#from unittest import result
from strategies.Strategy_Parent import Strategy

class BestOfStrat(Strategy):

    def __init__(self, bo_obj, unit_size=1, safety_margin=0.01):
        super().__init__(bo_obj.objs_list)  
           
        self.bo_obj = bo_obj
        
        # attach attributes to objs in bo_obj 
        for obj in bo_obj.objs_list:
            self._attach_attr(obj, unit_size, safety_margin)
                
  
    def _attach_attr(self, obj, unit_size, safety_margin):
        obj.cf_unit_bid_net = None
        obj.cf_unit_ask_net = None
        obj.order_id_buy    = None  
        obj.order_id_sell   = None

        obj.min_profit      = obj.scalar_size_mkt_to_unit * safety_margin
        obj.order_size      = obj.round_size_to_increment(abs(obj.scalar_size_mkt_to_unit) * unit_size)
        print(obj.order_size)
        
        
    def on_close_data(self, obj):
        # from MktData.on_close_data()
        mkt_close = obj.price_mkt_close

        price = obj.round_price_to_tick(0.5 *mkt_close)
        buy_order_id = self.update_limit_order(obj=obj, 
                                               buy_sell="BUY", 
                                               price=price, 
                                               size=obj.order_size, 
                                               order_id=None)
        
        if buy_order_id is not None:
            obj.order_id_buy  = buy_order_id
            if self.print_orders:
                self.print_order_message("BUY", 
                                         obj.order_size, 
                                         obj.my_fi_name, 
                                         price, 
                                         buy_order_id)   
        
        price = obj.round_price_to_tick(2.0 *mkt_close)
        sell_order_id = self.update_limit_order(obj=obj, 
                                                buy_sell="SELL", 
                                                price=price, 
                                                size=obj.order_size, 
                                                order_id=None)  
        
        if sell_order_id is not None:
            obj.order_id_sell = sell_order_id
            if self.print_orders:
                self.print_order_message("SELL", 
                                         obj.order_size, 
                                         obj.my_fi_name, 
                                         2.0 * mkt_close, 
                                         sell_order_id)   
                         
        if buy_order_id is not None and sell_order_id is not None:
            obj.strat_on_close_data = False 
            
            
    def on_mkt_data(self, x):
        # from MktData.on_mkt_data()
        
        buy_obj  = self.bo_obj.cf_unit_lift_ask_net_obj
        sell_obj = self.bo_obj.cf_unit_hit_bid_net_obj
        
        net_amt    = self.bo_obj.cf_unit_lift_ask_net + self.bo_obj.cf_unit_hit_bid_net
        min_profit = buy_obj.min_profit + sell_obj.min_profit

        if net_amt < min_profit:
            return
        
        buy_order_id = buy_obj.platform_obj.modify_limit_order(obj=buy_obj,
                                                               size=buy_obj.order_size,
                                                               buy_sell="BUY",
                                                               order_id=buy_obj.order_id_buy,
                                                               price=buy_obj.price_mkt_lift_ask)
        
        sell_order_id = sell_obj.platform_obj.modify_limit_order(obj=sell_obj,
                                                                size=sell_obj.order_size,
                                                                buy_sell="SELL",
                                                                order_id=sell_obj.order_id_sell,
                                                                price=sell_obj.price_mkt_hit_bid)       

        buy_obj.order_id_buy   = buy_order_id
        sell_obj.order_id_sell = sell_order_id

        self.active_orders = [buy_order_id, sell_order_id]

        for obj in self.bo_obj.objs_list:
            obj.strat_on_mkt_data = False
            if obj.buy_order_id != buy_order_id:
                #cancel buy buy_order_id
                pass
            if obj.sell_order_id != sell_order_id:
                #cancel sell sell_order_id
                pass
            
    
        def on_trade_exec(self, filled_obj, filled_order):
            if filled_obj.order_id_buy in self.active_orders:
                self.active_orders.pop(filled_order.orderId)
                filled_obj.strat_on_trade_exec = False
                
                if not self.active_orders:
                    self.on_trade_exec

            filled_obj.trade_status    = filled_order.orderStatus.status
            filled_obj.filled          = filled_order.orderStatus.filled
            filled_obj.remaining       = filled_order.orderStatus.remaining
            filled_obj.avg_fill_price  = filled_order.orderStatus.avgFillPrice
            filled_obj.last_fill_price = filled_order.orderStatus.lastFillPrice

            #print fills

            #print final result













    
    '''

    def place_limit_order(self, obj, output_price, input_price):  # very literal to improve speed
        if obj.is_mkt_data_valid():
            buy_sell         = obj.buy_sell
            size         = abs(obj.order_size)
            order_id     = obj.order_id
            output_price = abs(output_price)
            
            order_id = self.update_limit_order(obj=obj,                                      
                                               price=output_price, 
                                               buy_sell=buy_sell, 
                                               size=size, 
                                               order_id=order_id)   
            if self.print_orders:
                self.print_order_message(buy_sell, size, obj.my_fi_name, output_price, input_price, order_id)

            return order_id
        
    
    


    
        
    

          
    async def on_trade_exec(self, filled_obj, filled_order):        
        filled_obj.trade_status    = filled_order.orderStatus.status
        filled_obj.filled          = filled_order.orderStatus.filled
        filled_obj.remaining       = filled_order.orderStatus.remaining
        filled_obj.avg_fill_price  = filled_order.orderStatus.avgFillPrice
        filled_obj.last_fill_price = filled_order.orderStatus.lastFillPrice

        print fills

        print final result



            self.play_fill_sound()  
            
            if order_id is not None:
                self._one_admin(filled_obj, unfilled_obj, input_price, output_price, order_id)

            await asyncio.sleep(1000)  # wait a second before launching market order 

            order_id = self.place_market_order(unfilled_obj)
                               
        elif self.stage == "ONE FILLED":
            if filled_obj.remaining > 0:
                return   
                
            self.stage = "TWO FILLED"
            
            self._two_admin(filled_obj)   


    
    def _one_admin(self, filled_obj, unfilled_obj, input_price, output_price, order_id):             
        self._zero_admin(unfilled_obj, input_price, output_price, order_id)
        
        unfilled_obj.strat_on_mkt_data  = False
            
        filled_obj.strat_on_mkt_data    = False
        filled_obj.strat_on_trade_exec  = False     

        filled_obj.active_order_price = None
        filled_obj.active_input_price = None

    
    def _two_admin(self, filled_obj):
        filled_obj.strat_on_trade_exec = False
        
        filled_obj.active_price        = None
        filled_obj.active_input_price  = None

        final_spread = self.calc_final_spread(self.obj1, self.obj2)

        print("\nTRADE PACKAGE FINISHED")
        print("----------------------")
    
        for obj in [self.obj1, self.obj2]:
            print(
                obj.my_fi_name,
                obj.buy_sell,
                ", order_id:", obj.order_id,
                ", status:", obj.trade_status,
                ", filled:", obj.filled,
                ", avg_price:", obj.avg_fill_price,
                ", last_price:", obj.last_fill_price,
            )

        print('Final spread: ', final_spr
    def calc_final_spread(self, obj1, obj2):    
        final_spread = (obj2.avg_fill_price * obj2.spread_ratio * obj2.filled_scalar + 
                        obj1.avg_fill_price * obj1.spread_ratio * obj1.filled_scalar)  
        return final_spread


            
    '''