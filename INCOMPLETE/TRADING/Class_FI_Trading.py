#!/usr/bin/env python
# coding: utf-8

# In[1]:


#imports
import math

#self-written shortcuts
from Methods_Core import *
from Methods_IBKR import *


# In[2]:


class Trading_Instrument():
    
    def __init__(self, tempDict, outsideRTH=True):
                               
        self.fin_inst_id                            = None
        
        self.outside_rth                            = tempDict['outside_rth']
        self.fade_ratio                             = float(tempDict['fade_ratio'])
        self.fade_mult                              = float(tempDict['fade_mult'])
        self.close_mult                             = float(tempDict['close_mult'])
        self.tick_inc                               = float(tempDict['tick_increment'])

     
        #size        
        self.my_trade_size                          = {}
        self.my_trade_size["noun"]                  = None 
        self.my_trade_size["shortable_amt"]         = None        
        self.my_trade_size["unit_size"]             = float(tempDict['trade_amt_in_BTC'])


        #buy/sell/bid/ask
        if self.my_trade_size['unit_size']   > 0:
            self.buy_sell                           = "BUY"
        elif self.my_trade_size['unit_size'] < 0:
            self.buy_sell                           = "SELL"
            self.my_trade_size["unit_size"]         = abs(self.my_trade_size["unit_size"])
        self.my_trade_size['mkt_size']              = int(round(self.my_trade_size["unit_size"] / self.unit_size['scalar'], 0))
 
        quickDict                                   = {"SELL" : "ask", "BUY" : "bid"}
        self.bid_ask                                = quickDict[self.buy_sell]
        
        self.buy_sell_opp                           = getOpp(self.buy_sell, "BUY", "SELL")      
        self.bid_ask_opp                            = getOpp(self.bid_ask, "bid", "ask")
 

        #prices
        self.my_trade_price                         = {}
        self.my_trade_price["off_mkt_bid"]          = None
        self.my_trade_price["off_mkt_ask"]          = None
        self.my_trade_price["show"]                 = None
        self.my_trade_price["fade"]                 = None 
        self.my_trade_price["fill"]                 = None 
        
        
        quickDict                                   = {'BUY' : 1, 'SELL' : -1}
        self.my_trade_price["stp_adj"]              = float(tempDict['stp_amt']) * quickDict[self.buy_sell]
        #self.convertToIncrement(quickDict[self.buy_sell] * float(self.limit) / float(self.scalar))         
        
        #orders
        self.order                                  = {"filled" : False, "fade_launched" : False, "lmt_id" : None, 
                                                                         "stop_launched" : False, "stp_id" : None}
        
        if self.platform == "IBKR":
            for lmtStp in ["lmt", "stp"]:
                self.order[lmtStp]                  = ibkrOrderObject(self.buy_sell, self.my_trade_size['mkt_size'],
                                                                      self.my_trade_price["show"], lmtStp, self.outside_rth)  

            
    def calcOffMktPrices(self, offMktPct):
  
        offMktDiff                                  = self.mkt_price["close"] * offMktPct
        
        self.my_trade_price["off_mkt_bid"]          = self.convertToIncrement(self.mkt_price["close"] - offMktDiff, "BUY")
        self.my_trade_price["off_mkt_ask"]          = self.convertToIncrement(self.mkt_price["close"] + offMktDiff, "SELL")
        
        self.my_trade_price["show"]                 = self.my_trade_price['off_mkt_' + self.bid_ask]            
        self.my_trade_price["fade"]                 = self.my_trade_price['off_mkt_' + self.bid_ask_opp]
               
            
    def resetMktPrices(self):
        
        for attr in ['bid', 'ask']:
            self.my_trade_price['off_mkt_' + attr]  = round(self.price['off_mkt_' + attr], 2)
            self.mkt_price[attr]                    = self.my_trade_price['off_mkt_' + attr]
            self.mkt_size [attr]                    = 0

            
    def calcFadePrice(self): 
    
        tempDict = {'BUY' : -1, "SELL" :1}
        addOrSubtract = tempDict[self.buy_sell_opp]
        
        fadeAmt = 0
        if self.mkt_size[self.bid_ask_opp] < (self.my_trade_size['mkt_amt'] * self.fade_ratio):
            fadeAmt = self.fade_mult * (self.mkt_price["ask"] - self.mkt_price["bid"])
        
        fadedPrice = self.mkt_price[self.bid_ask_opp] + (fadeAmt * addOrSubtract)    
        fadedPrice = self.convertToIncrement(fadedPrice, self.buy_sell_opp)       
        
        return fadedPrice    

    
    def testShowPrice(self, showPrice):
    
        testWidth         = self.close_mult * (self.mkt_price["ask"] - self.mkt_price["bid"])
    
        if self.bid_ask   ==  "bid":
            testBound     = self.mkt_price['bid'] - testWidth 
            closeToMarket = (testBound <= showPrice)
        elif self.bid_ask == "ask":
            testBound     = self.mkt_price['ask']  + testWidth 
            closeToMarket = (showPrice <= testBound)
        else:
            print("testShowPrice not Bid or Ask")
            
        if (not closeToMarket):
            showPrice     = self.my_trade_price['off_mkt_' + self.bid_ask]
        
        return showPrice
    
    
    def convertToIncrement(self, rawPrice, howIncrement=None):
        
        if howIncrement == None:
            howIncrement = self.buy_sell
        outside = convertToIncrement(rawPrice, self.price["tick_inc"], howIncrement)
        return outside
    
    def resetOrderIDs(self):
        
        for lmtStp in ["lmt_id", "stp_id"]:
            self.order[lmtStp] = None
 


# In[3]:


def convertToIncrement(rawPrice, tickInc, howIncrement):

    inside = rawPrice / tickInc

    if   howIncrement == "BUY":
        outside = round(math.floor(inside), 0) * tickInc
    elif howIncrement == "SELL":
        outside = round(math.ceil(inside), 0)  * tickInc
    elif howIncrement == "round":
        outside = round(inside, 0)   * tickInc
    else:
        outside = "error"

    return outside

