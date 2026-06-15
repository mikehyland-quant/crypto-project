
from fin_insts.parents.Class_FI_MktData import MktData

# from itertools import combinations


class OptionCombo(MktData):
    """
    FutureSpread instrument class (NOT a child of FinancialInstrument
    """

    consensus_attr_list = [
        'my_pf_name',

        'comm_type',
        
        'scalar_price_raw_to_screen',
        'scalar_size_raw_to_screen',

        'scalar_self_per_unit', 
        'scalar_order_multiplier',

        'scalar_screens_per_unit',  
        'scalar_units_per_screen',         
            
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
        'date_expiry',
        'date_settle_expiry',

        'days_settle_comm',   
        'days_settle_trade',
        'days_settle_expiry',

        'last_trade_date_time_nyc'
                        ]

    def __init__(self, call_obj, put_obj):
        super().__init__() 
        
        self.call_obj  = call_obj
        self.put_obj   = put_obj
        self.objs_list = [call_obj, put_obj]
        
        self.my_prod_type = 'option_combo'
        self.my_fi_name = f"{self.call_obj.my_fi_name}/{self.put_obj.my_fi_name}"

        for attr in self.consensus_attr_list:
            setattr(self, attr, self._consensus_attr(attr))
            
        self.comm_maker_amount = self.call_obj.comm_maker_amount + self.put_obj.comm_maker_amount 
        self.comm_taker_amount = self.call_obj.comm_taker_amount + self.put_obj.comm_taker_amount 
        self.comm_misc_amount  = self.call_obj.comm_misc_amount  + self.put_obj.comm_misc_amount 

        # assigned later
        if self.my_pf_name == "IBKR":        
            self.ibkr_contract = None
            self.ibkr_details  = None 

    
    def _consensus_attr(self, attr_name):
        values = {getattr(obj, attr_name, None) for obj in self.objs_list}
        return values.pop() if len(values) == 1 else "multi"
    

    def make_ibkr_spread_contract(self, ibkr):
        self.ibkr_contract = ibkr.create_bag_contract(self.call_obj, "BUY", 1, self.put_obj, "SELL",

    
    @staticmethod
    def make_combos(instrument_list):
        call_dict = defaultdict(list)
        put_dict = defaultdict(list)

        for obj in instrument_list:
            if getattr(obj, "my_prod_type", None) != "option":
                continue

            key = (
                obj.underlying_symbol,
                obj.my_pf_name,
                obj.strike_price,
                obj.date_expiry,
            )

            if obj.right == "C":
                call_dict[key].append(obj)
            elif obj.right == "P":
                put_dict[key].append(obj)

        combos_list = []

        for key in call_dict.keys() & put_dict.keys():
            combo = OptionCombo(call_dict[key], put_dict[key])
            combos_list.append(combo)

        return combos_list



        