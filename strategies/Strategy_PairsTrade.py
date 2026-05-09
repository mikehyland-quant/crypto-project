#!/usr/bin/env python
# coding: utf-8

#import asyncio

from datetime import datetime
from strategies.Strategy_Parent import Strategy


class PairsTrade(Strategy):
    """
    Two-leg package strategy.

    """

    def __init__(self, objs_list, df):
        super().__init__(objs_list)  
        
        # create self attributes
        self.stage = 'ZERO FILLED'
        
        self.target_spread = df.loc['target_spread'].sum()
        self.epsilon       = df.loc['wiggle_on_2nd_fill'].sum()

        # make objs_dict
        #df = df.drop(columns=, 'TRUE/FALSE'])
        df = df.drop(index=['target_spread', 'wiggle_on_2nd_fill'])

        objs_dict = df.to_dict()

        # attach attributes to objs
        self.obj1, self.obj2 = self._attach_dict_attr(objs_list, objs_dict)
                                                 
        self.obj1.opp_obj = self.obj2
        self.obj2.opp_obj = self.obj1

        self.obj1, self.obj2 = self._attach_strat_attr([self.obj1, self.obj2])

                
    def _attach_dict_attr(self, objs_list, objs_dict):
        for obj_name, obj_dict in objs_dict.items():
    
            obj = next(
                (
                    o for o in objs_list
                    if o.my_fi_name == obj_dict['my_fi_name']
                    and o.my_pf_name == obj_dict['my_pf_name']
                ),
                None
            )
    
            if obj is None:
                raise ValueError(f"Could not find object for {obj_name}: {obj_dict}")
    
            # creates self.obj1, self.obj2, etc.
            setattr(self, obj_name.lower(), obj)
    
            # attaches strategy attrs to the object
            for attr_key, attr_val in obj_dict.items():
                setattr(obj, attr_key, attr_val)
    
        return self.obj1, self.obj2


    def _attach_strat_attr(self, objs_list):
        buy_sell_dict  = {'BUY': ('cf_unit_lift_ask', -1), 'SELL': ('cf_unit_hit_bid', 1)}
        min_ratio_size = min(self.obj1.ratio_size, self.obj2.ratio_size)
        
        for obj in objs_list:
            obj.active_base_price                   = None
            obj.active_order_price                  = None  

            obj.buy_sell                            = obj.buy_sell.upper()
            obj.order_size                          = abs(obj.order_size)
            obj.calc_price                          = self.calc_price   # assigns function below - might be able to lose this
            obj.spread_ratio                        = obj.opp_obj.ratio_size / min_ratio_size
#            obj.spread_ratio_inv                    = 1 / obj.spread_ratio
            obj.adj_spread                          = self.target_spread / obj.spread_ratio
            

            obj.input_price_attr, obj.filled_scalar = buy_sell_dict[obj.buy_sell]

            setattr(obj.opp_obj, 'strat_on_trade_exec', True)   
            
            if obj.active_passive.lower() == 'active':
                setattr(obj.opp_obj, 'strat_on_mkt_data', True)
            elif obj.active_passive.lower() == 'passive':
                setattr(obj.opp_obj, 'strat_on_mkt_data', False)

        return self.obj1, self.obj2
                    
        
    def on_mkt_data(self, input_obj):
        if self.stage != "ZERO FILLED":
            return  # no need to update price 

        output_obj  = input_obj.opp_obj
        input_price = getattr(input_obj, input_obj.input_price_attr)
        
        if output_obj.active_base_price is not None and abs(input_price - output_obj.active_base_price) < 1e-9:
            return

        output_price = output_obj.calc_price(input_price, output_obj, 0)  # goes to either _calc_obj1_price or _calc_obj2_price
        
        if output_obj.active_order_price is not None and abs(output_price - output_obj.active_order_price) < 1e-9:
            return
            
        order_id = self.place_order(output_obj, output_price, input_price)
        
        if order_id is not None:
            self._zero_admin(output_obj, input_price, output_price, order_id)

          
    def on_trade_exec(self, filled_obj, filled_order):        
        filled_obj.trade_status    = filled_order.orderStatus.status
        filled_obj.filled          = filled_order.orderStatus.filled
        filled_obj.remaining       = filled_order.orderStatus.remaining
        filled_obj.avg_fill_price  = filled_order.orderStatus.avgFillPrice
        filled_obj.last_fill_price = filled_order.orderStatus.lastFillPrice

        if self.stage == "ZERO FILLED":
            if filled_obj.remaining > 0:
                return
                
            self.stage   = "ONE FILLED"        
            input_price  = filled_obj.avg_fill_price * filled_obj.filled_scalar
            unfilled_obj = filled_obj.opp_obj
            
            output_price = unfilled_obj.calc_price(input_price, unfilled_obj, 1)  
            order_id     = self.place_order(unfilled_obj, output_price, input_price)
            
            if order_id is not None:
                self._one_admin(filled_obj, unfilled_obj, input_price, output_price, order_id)
                               
        elif self.stage == "ONE FILLED":
            if filled_obj.remaining > 0:
                return   
                
            self.stage = "TWO FILLED"
            
            self._two_admin(filled_obj)     


    def _zero_admin(self, obj, input_price, output_price, order_id):        
        obj.active_base_price  = input_price
        obj.active_order_price = output_price        
        obj.order_id           = order_id  

    
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

        print('Final spread: ', final_spread, '\n')

        # if using event:
        if self.done_event is not None:
            self.done_event.set()

        
    def calc_price(self, input_price, output_obj, epsilon_scalar):     
#        print(input_price, output_obj.my_fi_name, output_obj.adj_spread, output_obj.spread_ratio)
        fair_value   = output_obj.adj_spread - (input_price * output_obj.spread_ratio)
        output_price = fair_value - (epsilon_scalar * self.epsilon)
        output_price = output_obj.round_price_to_tick(abs(output_price))                                             
        return output_price

    
    def calc_final_spread(self, obj1, obj2):    
        final_spread = (obj2.avg_fill_price * obj2.spread_ratio * obj2.filled_scalar + 
                        obj1.avg_fill_price * obj1.spread_ratio * obj1.filled_scalar)  
        return final_spread


            
            