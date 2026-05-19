
import asyncio

from strategies.Strategy_Parent import Strategy

class PairsTrade_Parent(Strategy):
    """
    Two-leg package strategy.

    This is for shared code between different pairs trade strategies. Try to keep this to non-hot path code, and put any hot path code in the child class.
    """

    def __init__(self, objs_list, df):
        super().__init__(objs_list)  
        
        # create self attributes
        self.stage = 'ZERO FILLED'
        
        self.target_spread = df.loc['target_spread'].sum()
        self.epsilon       = df.loc['epsilon'].sum()
        
        df = df.drop(index=['target_spread'])
        df = df.drop(index=['epsilon'])

        objs_dict = df.to_dict()

        # attach attributes to objs
        self.obj1, self.obj2 = self._attach_input_attr(objs_list, objs_dict)
                                                 
        self.obj1.opp_obj = self.obj2
        self.obj2.opp_obj = self.obj1

        self.obj1, self.obj2 = self._attach_strat_attr([self.obj1, self.obj2])

                
    def _attach_input_attr(self, objs_list, objs_dict):
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
            obj.active_base_price  = None
            obj.active_order_price = None  

            obj.order_id           = None
            obj.trade_status       = None
            obj.filled             = 0
            obj.remaining          = None
            obj.avg_fill_price     = None
            obj.last_fill_price    = None
            
            obj.buy_sell           = obj.buy_sell.upper()
            obj.order_size         = abs(obj.order_size)
            obj.calc_price         = self._calc_price   # assigns function below 
            obj.spread_ratio       = obj.opp_obj.ratio_size / min_ratio_size
            obj.adj_spread         = self.target_spread / obj.spread_ratio
            
            obj.input_price_attr, obj.filled_scalar = buy_sell_dict[obj.buy_sell]  
            
            if obj.active_passive.lower() == 'passive':
                #was set to True in Strategy_Parent, so now set to False for passive leg
                setattr(obj.opp_obj, 'strat_on_mkt_data', False)   

        return self.obj1, self.obj2
                    

     def _placed_order_admin(self, obj, order_id, order_price, base_price):   
        obj.order_id            = order_id
        obj.active_base_price   = base_price
        obj.active_order_price  = order_price       
    

    def _filled_order_admin(self, filled_obj, filled_order):      
        filled_obj.trade_status        = filled_order.orderStatus.status
        filled_obj.filled              = filled_order.orderStatus.filled
        filled_obj.remaining           = filled_order.orderStatus.remaining
        filled_obj.avg_fill_price      = filled_order.orderStatus.avgFillPrice
        filled_obj.last_fill_price     = filled_order.orderStatus.lastFillPrice
        
        filled_obj.strat_on_trade_exec = False     
        
        filled_obj.active_order_price  = None
        filled_obj.active_base_price   = None


    def _finalize_results(self):
        final_spread = (self.obj2.avg_fill_price * self.obj2.spread_ratio * self.obj2.filled_scalar + 
                        self.obj1.avg_fill_price * self.obj1.spread_ratio * self.obj1.filled_scalar)  

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

        
    def _calc_price(self, input_price, output_obj, epsilon_scalar=0):     
        fair_value   = output_obj.adj_spread - (input_price * output_obj.spread_ratio)
        output_price = fair_value - (epsilon_scalar * self.epsilon)
        output_price = output_obj.round_price_to_tick(abs(output_price))                                             
        return output_price

    