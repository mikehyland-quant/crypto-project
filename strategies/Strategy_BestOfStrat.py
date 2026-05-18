
import asyncio
from datetime import datetime
from strategies.Strategy_Parent import Strategy


class BestOfStrat(Strategy):

    def __init__(self, bo_obj, unit_size=1, safety_margin=0.01):
        super().__init__(bo_obj.objs_list)  
           
        self.bo_obj = bo_obj
        
        # attach attributes to objs in bo_obj 
        for obj in bo_obj.objs_list:
            self._prep_obj_for_strat(obj, unit_size, safety_margin)
                
  
    def _prep_obj_for_strat(self, obj, unit_size, safety_margin):
        obj.cf_unit_bid_net = None
        obj.cf_unit_ask_net = None
        obj.order_id_buy    = None
        obj.order_id_sell   = None

        obj.min_profit      = bo_obj.scalar_size_mkt_to_unit * safety_margin
        obj.order_size      = obj.round_size_to_increment(abs(obj.scalar_size_mkt_to_unit) * unit_size)
        obj.update_mkt_data = self.update_mkt_data  # override the method in parent class so that it can be called by bo_obj at end of mkt_data_update() in subscriber.update_unit_data()


    def update_mkt_data(self, bid_price=None, ask_price=None, bid_size=None, ask_size=None):       
        changed = super().update_mkt_data(bid_price, ask_price, bid_size, ask_size)  
        if changed:
            self.cf_unit_bid_net = self.cf_unit_bid - self.comm_unit_hit_bid
            self.cf_unit_ask_net = self.cf_unit_ask - self.comm_unit_lift_ask

        return changed

        
    def on_close_data(self, obj):
        # from MktData.on_close_data()
        buy_order_id = self.update_limit_order(obj=obj, 
                                               side="BUY", 
                                               price=0.5 * obj.price_mkt_close, 
                                               size=obj.order_size, 
                                               order_id=None)
        
        sell_order_id = self.update_limit_order(obj=obj, 
                                                side="SELL", 
                                                price=2.0 * obj.price_mkt_close, 
                                                size=obj.order_size, 
                                                order_id=None)  
        
        obj.order_id_buy  = buy_order_id
        obj.order_id_sell = sell_order_id


    def on_mkt_data(self):
        # from MktData.on_mkt_data()
        buy_obj  = self.bo_obj.cf_unit_ask_net_obj
        sell_obj = self.bo_obj.cf_unit_bid_net_obj
        
        net_amt    = self.bo_obj.cf_unit_ask_net + self.bo_obj.cf_unit_bid_net
        min_profit = buy_obj.min_profit + sell_obj.min_profit

        if net_amt < min_profit:
            return

        buy_order_id = self.update_limit_order(obj=buy_obj,                  
                                               price=buy_obj.price_mkt_lift_ask,
                                               order_id=buy_obj.order_id_buy)
        
        sell_order_id = self.update_limit_order(obj=sell_obj,           
                                                price=sell_obj.price_mkt_hit_bid,       
                                                order_id=sell_obj.order_id_sell)
        
        #record order ids
        #turn off on mkt data updates until trade exec
        

        def on_trade_exec(filled_obj, filled_order):

            # from TradeExec.on_trade_exec()
            pass  # to be implemented
            #cancel all remaining orders














    
    '''

    def place_limit_order(self, obj, output_price, input_price):  # very literal to improve speed
        if obj.is_mkt_data_valid():
            side         = obj.buy_sell
            size         = abs(obj.order_size)
            order_id     = obj.order_id
            output_price = abs(output_price)
            
            order_id = self.update_limit_order(obj=obj,                                      
                                               price=output_price, 
                                               side=side, 
                                               size=size, 
                                               order_id=order_id)   
            if self.print_orders:
                self.print_order_message(side, size, obj.my_fi_name, output_price, input_price, order_id)

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