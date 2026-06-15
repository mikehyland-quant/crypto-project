
from fin_insts.parents.Class_FI import FinancialInstrument

 
class Spot(FinancialInstrument):
    """
    Spot instrument class (child of FinancialInstrument).
    """
    def __init__(self, row):
        super().__init__(row)

        self.biz_days_to_comm_pmt  = 0
        self.biz_days_to_trade_pmt = 0

        
    def complete_obj(self):
        super().complete_obj()  


        