
from fin_insts.tradable.Class_FI_Future import Future

import pandas as pd


class Option(Future):  
    """
    Option instrument class (child of FinancialInstrument).
    """
    def __init__(self, row):
        super().__init__(row)

    def complete_obj(self):
        super().complete_obj()   

        '''
        self.opt_values = {'mkt_intrinsic' : None,
                           'mkt_bid_tv'    : None, 
                           'mkt_ask_tv'    : None,
                           'unit_intrinsic': None,
                           'unit_bid_tv'   : None,
                           'unit_ask_tv'   : None}
        
        self.opt_vols   = {'mkt_bid'       : None, 
                            'mkt_ask'       : None}
        '''

        # overwrite previous entries and reattach scalars
        self.scalar_size_FIs_per_unit    = self.get_scalar()
        self.scalar_size_units_per_FI    = 1 / self.scalar_size_FIs_per_unit
        
        self.scalar_size_orders_per_unit = self.scalar_size_FIs_per_unit / self.scalar_size_FIs_per_order
        self.scalar_size_units_per_order = self.scalar_size_FIs_per_order / self.scalar_size_FIs_per_unit

        self.unit_strike_price = self.strike_price * self.scalar_size_FIs_per_unit

    def get_scalar(self):
        from input_output.Class_InputOutput import InputOutput
        io = InputOutput()

        wb, ws = io.set_xw_book_and_sheet('2026 BTC ETF Ratios.xlsx', 'BTC RATIOS')
        df = io.get_xw_df(ws, 'btc_ratios', table=True)
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        exp_date = self.date_settle_trade
        scalar = self._safe_float(df.loc[df['Date'] == exp_date, self.ibkr_contract.symbol].to_list()[0])
        return scalar

    '''         
    def calc_iv_tv (self, underlyingPrice):
        tempValue = underlyingPrice - self.contract['strike']
        if   self.contract['right'].upper() == 'C':
            self.opt_values["intrinsic"]  = max[0,  tempValue]
        elif self.contract['right'].upper() == 'P':
            self.opt_values["intrinsic"]  = max[0, -tempValue]
        else:
            raise ValueError("Invalid option type. Use 'C' or 'P'.")
            
        self.opt_values["mkt_bid_tv"] = self.mkt_data['bid_price'] - self.opt_values["intrinsic"]
        self.opt_values['mkt_ask_tv'] = self.mkt_data['ask_price'] - self.opt_values["intrinsic"]
        
    
    def calc_imp_vol(self, bidAsk, underlyingPrice, intRate):
        bidAskList = getBidAskList(bidAsk)
        for action in bidAskList: 
            if self.contract['secType'] in ['OPT']:
                self.opt_vols['mkt_' + action] = calculate_implied_volatility(self.contract['right'], 
                                                                              self.mkt_data[action + '_price'], 
                                                                              underlyingPrice, 
                                                                              self.contract['strike'], 
                                                                              self.expiration['years_to_expiry'], 
                                                                              intRate)
            elif self.contract['secType'] in ['FOP']:
                self.opt_vols['mkt_' + action] = calculate_implied_volatility_forward(self.contract['right'], 
                                                                                      self.mkt_data[action + '_price'], 
                                                                                      underlyingPrice, 
                                                                                      self.contract['strike'], 
                                                                                      self.expiration['years_to_expiry'], 
                                                                                      intRate)
            else:
                raise ValueError("Invalid secType.")

    '''
    