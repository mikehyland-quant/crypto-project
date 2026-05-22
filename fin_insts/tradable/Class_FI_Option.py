#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from fin_insts.parents.Class_FI import Future

# In[ ]:


class Option(Future):
    """
    Option instrument class (child of FinancialInstrument).
    """
    def __init__(self, row):
        super().__init__(row)
        
        self.biz_days_to_comm_pmt  = None
        self.biz_days_to_trade_pmt = None
        self.biz_days_to_expiry_pmt  = None

    def complete_obj(self):
        super().complete_obj()   

        self.underlying_asset = self.contract_dict['symbol']
        
        self.p_or_c = self.contract_dict['right']
        
        self.mkt_data_dict['strike']               = self.contract_dict['strike']
        self.unit_data_dict['unit_strike']         = self.contract_dict['strike'] * self.unit_scalar_dict['price']

        self.opt_values                            = {'mkt_intrinsic' : None,
                                                      'mkt_bid_tv'    : None, 
                                                      'mkt_ask_tv'    : None,
                                                      'unit_intrinsic': None,
                                                      'unit_bid_tv'   : None,
                                                      'unit_ask_tv'   : None}
        
        self.opt_vols                              = {'mkt_bid'       : None,
                                                      'mkt_ask'       : None}

    def complete_obj(self):
        super().complete_obj() 
        
        self.mkt_to_unit_scalar_dict['price'] = self.get_scalar()
        self.mkt_to_unit_scalar_dict['size']  = self.mkt_to_unit_scalar_dict['price'] 

    def get_scalar(self):
        df = xlw.get_df('2026 Crypto ETF Ratios.xlsx', 
                        'BTC RATIOS', 
                        'btc_ratios', table=True)
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        exp_date = pd.to_datetime(self.settlement_dates_dict['trade']).date()
        scalar = self._safe_float(df.loc[df['Date'] == exp_date, self.my_fi_name].to_list()[0])
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


    



        