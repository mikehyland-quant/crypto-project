#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from itertools import combinations
from fin_insts.parents.Class_FI_MktData import MktData
from ibkr.Class_IBKR_IB import IBKR_IB


# In[ ]:


class FutureSpread(MktData):
    """
    FutureSpread instrument class (NOT a child of FinancialInstrument
    """

    consensus_attr_list = [
        'my_pf_name',

        'comm_type',
        
        'scalar_price_raw_to_order',
        'scalar_price_order_to_mkt',
        'scalar_price_mkt_to_unit',        
        'scalar_size_raw_to_order',
        'scalar_size_order_to_mkt',
        'scalar_size_mkt_to_unit',
        'scalar_order_size',
            
        'pf_symbol',
        'pf_number',
        'pf_prod_type',
        
        'numerator_currency',
        'denominator_currency',       
        'quote_currency',
        'settlement_currency',
    
        'date_trade',        
        'date_settle_comm',   
        'date_settle_trade',  
        
        'days_settle_comm',   
        'days_settle_trade', 
        
                        ]

    def __init__(self, obj1, obj2):
        super().__init__() 
        
        self.near_obj, self.far_obj = self.determine_near_far(obj1, obj2)
        self.objs_list = [self.near_obj, self.far_obj]
        
        self.my_prod_type = 'future_spread'
        self.my_fi_name = f"{self.near_obj.my_fi_name}/{self.far_obj.my_fi_name}"

        for attr in self.consensus_attr_list:
            setattr(self, attr, self._consensus_attr(attr))
            
        self.comm_maker_amount = self.near_obj.comm_maker_amount + self.far_obj.comm_maker_amount 
        self.comm_taker_amount = self.near_obj.comm_taker_amount + self.far_obj.comm_taker_amount 
        self.comm_misc_amount  = self.near_obj.comm_misc_amount  + self.far_obj.comm_misc_amount 
                       
        self.date_expiry_near              = self.near_obj.date_expiry
        self.date_settle_expiry_near       = self.near_obj.date_settle_expiry
        self.days_settle_expiry_near       = self.near_obj.days_settle_expiry
        self.last_trade_date_time_nyc_near = self.near_obj.last_trade_date_time_nyc

        self.date_expiry_far               = self.far_obj.date_expiry
        self.date_settle_expiry_far        = self.far_obj.date_settle_expiry
        self.days_settle_expiry_far        = self.far_obj.days_settle_expiry
        self.last_trade_date_time_nyc_far  = self.far_obj.last_trade_date_time_nyc

        # assigned later
        if self.my_pf_name == "IBKR":        
            self.ibkr_contract = None
            self.ibkr_details  = None 

    
    def determine_near_far(self, obj1, obj2):
        if obj1.date_expiry < obj2.date_expiry:
            return obj1, obj2
        else:
            return obj2, obj1   

    
    def _consensus_attr(self, attr_name):
        values = {getattr(obj, attr_name, None) for obj in self.objs_list}
        return values.pop() if len(values) == 1 else "multi"

    
    @staticmethod
    def make_spreads(list_):
        futures_list = [obj for obj in list_ if obj.my_prod_type == 'future']
        fut_spd_pairs_list = list(combinations(futures_list, 2))
        fut_spd_obj_list = [FutureSpread(pair[0], pair[1]) for pair in fut_spd_pairs_list]

        return fut_spd_obj_list

