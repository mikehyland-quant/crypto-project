
from fin_insts.parents.Class_FI import Future

# In[ ]:


class Option(Future):  
    """
    Option instrument class (child of FinancialInstrument).
    """
    def __init__(self, row):
        super().__init__(row)

    def complete_obj(self):
        super().complete_obj()   

        self.opt_values = {'mkt_intrinsic' : None,
                            'mkt_bid_tv'    : None, 
                            'mkt_ask_tv'    : None,
                            'unit_intrinsic': None,
                            'unit_bid_tv'   : None,
                            'unit_ask_tv'   : None}
        
        self.opt_vols   = {'mkt_bid'       : None, 
                            'mkt_ask'       : None}

        # overwrite previous entries and reattach scalars
        self.mkt_to_unit_price_scalar = self.get_scalar()
        
        self.attach_scalars(self.raw_to_screen_price_scalar, 
                            self.screen_to_mkt_price_scalar, 
                            self.mkt_to_unit_price_scalar,

                            self.raw_to_screen_size_scalar,
                            self.screen_to_mkt_size_scalar,
                            self.mkt_to_unit_size_scalar)

        self.unit_strike_price = self.strike_price * self.scalar_size_mkt_to_unit

    def get_scalar(self):

        wb, ws = io.set_xw_book_and_sheet('2026 BTC ETF Ratios.xlsx', 'BTC RATIOS')
        df = io.get_xw_df(ws, 'btc_ratios', table=True)
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        exp_date = self.date_settle_trade
        scalar = self._safe_float(df.loc[df['Date'] == exp_date, self.ibkr_contract.symbol].to_list()[0])
        return scalar
             
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
        
    '''
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
    



        