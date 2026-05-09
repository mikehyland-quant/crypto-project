#!/usr/bin/env python
# coding: utf-8

# In[1]:


#imports
import math
import pandas as pd
import threading
import time

#self-written shortcuts
import Class_FI_Trading as tc
import Methods_Core     as hc
import Methods_IBKR     as ibM
from   Methods_Printing import *


# In[2]:


#called from ibkrPriceSizeTrader

def checkMktData(self, inputIndex, field): 

    inputObj  = self.finInstDictID[inputIndex]
    outputObj = self.finInstDictID[1 - inputIndex] 

    #does the market data make sense?     
    cond1 = (0 <  inputObj.price["mkt_bid"] <  inputObj.price["mkt_ask"]) 
    cond2 = (0 < outputObj.price["mkt_bid"] < outputObj.price["mkt_ask"]) 

    if cond1 and cond2:
        #where the bid can be hit for the sellIndex
        cond3 = ((inputObj.buy_sell == "SELL") and (    field < 2))
        #where the ask can be lifted for the buyIndex
        cond4 = ((inputObj.buy_sell == "BUY")  and (1 < field < 4))

        if cond3 or cond4:
            organizeTradingData(self, inputObj, outputObj)
            
                                
#other tests                
#    cond5 = (self.finInstDictID[inputIndex] .size["to_trade"] < 
  #           self.finInstDictID[outputIndex].size["to_trade"])

   # if ((self.tradingStyle == "ShowBoth" )               or 
    #    (self.tradingStyle == "ShowSmall" and     cond5) or    
     #   (self.tradingStyle == "ShowBig"   and not cond5)):

#    elif (self.tradingStyle == "HitLift" ): 
 #       hitLift(self, inputIndex)
    


# In[ ]:


def organizeTradingData(self, inputObj, outputObj):
    
    #for cash flow directions
    buySellDict   = {'BUY' : -1, "SELL" : 1}     

    
    #calc faded amounts
    fadedInputPrice       = inputObj.calcFadePrice()
    fadedPkgPrice         = inputObj.price['scalar_pkg'] * fadedInputPrice
    fadedPkgFlow          = fadedPkgPrice * buySellDict[inputObj.buy_sell]


#in future this needs to be calced
    if inputObj.comm['type'] == 'flat':
        fadedComm         = inputObj.size ['scalar_pkg'] * inputObj.comm["mkt_" + inputObj.bid_ask_opp] 
    else:
        pass
    

    #make dataframe
    df                    = pd.DataFrame(index = [0, 1])
#    df['I/O']             = 0
    df[0]                 = 0
    df[self.daysList[0]]  = 0
    df[self.daysList[1]]  = 0

    
    #put input flows in dataframe
    inputIndex                                           = inputObj.fin_inst_id
    df.loc[inputIndex, inputObj.whole_days_to_expiry_cf] = fadedPkgFlow
    df.loc[inputIndex, inputObj.whole_days_to_comm]      = fadedComm + df.loc[inputIndex, inputObj.whole_days_to_comm]
    
    
    self.pricingEngine(inputObj, outputObj, df, fadedInputPrice)
    


# def pricingEngine is in main program

# In[3]:


#called from pricingEngine

def initialOrders(self, inputObj, outputObj, fadePrice, showPrice): 

    showPrice = outputObj.convertToIncrement(showPrice)
    showPrice = outputObj.testShowPrice(showPrice)

    if (showPrice != outputObj.price['show']):
        inputObj .price['fade'] = fadePrice
        outputObj.price['show'] = showPrice
       
        outputObj.order["lmt"].lmtPrice = outputObj.price["show"]    
        ibM.ibkrLaunchOrder(self, outputObj, 'lmt')
        initialOrdersCounter = threading.Timer(0.1, initialOrdersAdminAndPrint, 
                                                [self, inputObj, outputObj]).start()

###############
    
def initialOrdersAdminAndPrint(self, inputObj, outputObj):

    buySellDict           = {'BUY' : -1, "SELL" : 1}
    
    fadeFlow      = inputObj.price['fade']  * inputObj.price['scalar_pkg']  * buySellDict[inputObj.buy_sell]
    showFlow      = outputObj.price['show'] * outputObj.price['scalar_pkg'] * buySellDict[outputObj.buy_sell]
        
    fadeComm      = inputObj.comm['mkt_' + inputObj.bid_ask_opp] * inputObj.size['scalar_pkg']
    if inputObj.whole_days_to_comm == 0:
        fadeComm  = fadeComm * self.commScalar
     
    showComm      = outputObj.comm['mkt_' + outputObj.bid_ask] * outputObj.size['scalar_pkg']
    if outputObj.whole_days_to_comm == 0:
        showComm  = showComm * self.commScalar

    profitAmt = self.calcPricingEngine(fadeFlow, fadeComm, showFlow, showComm, inputObj)  
    printSummaryInfo("order", inputObj, outputObj, profitAmt)


# In[4]:


#called from IBKR.orderStatus():

def secondaryOrders(self, orderNum, shsRemaining, shsFilled, fillPrice):         
    
    quickDict       = {self.finInstDictID[0].order["lmt_id"]: [0, "lmt"],
                       self.finInstDictID[0].order["stp_id"]: [0, "stp"],
                       self.finInstDictID[1].order["lmt_id"]: [1, "lmt"],
                       self.finInstDictID[1].order["stp_id"]: [1, "stp"]}
    fillInfo        = quickDict[orderNum]
    
    filledIndex     = fillInfo[0]
    filledOrderType = fillInfo[1]
        
    filledObj       = self.finInstDictID[filledIndex]
    unfilledObj     = self.finInstDictID[1 - filledIndex]
    
    if self.ordersFilled == 0:
        zeroFilled(self, orderNum, shsRemaining, shsFilled, filledObj, unfilledObj, fillPrice)

    if self.ordersFilled == 1:
        oneFilled (self, orderNum, shsRemaining, filledObj, unfilledObj, filledOrderType, fillPrice)


# In[5]:


#called from secondaryOrders

def zeroFilled(self, orderNum, shsRemaining, shsFilled, filledObj, unfilledObj, fillPrice):

    if ((shsRemaining < shsFilled) and (not unfilledObj.order["fade_launched"])):
        unfilledObj.order["lmt"].lmtPrice = unfilledObj.price['fade']        
        ibM.ibkrLaunchOrder(self, unfilledObj, 'lmt')
        unfilledObj.order["fade_launched"] = True   
        
        
    if shsRemaining == 0:

#maybe make better fadedPrice somewhere around here?
#unfilledObj.order["lmt"].lmtPrice = unfilledObj.price['fade']        
#ibM.ibkrLaunchOrder(self, unfilledObj, 'lmt')
       
        self.ordersFilled = 1 
        
        filledObj.price["fill"]            = fillPrice
        filledObj.order['filled']          = True        
        filledObj.order["fade_launched"]   = 'XXX'
        filledObj.order["stop_launched"]   = 'XXX'
        filledObj.order["stp_id"]          = filledObj.order["lmt_id"] #prevent stop from being launched

        zeroFilledCounter = threading.Timer(0.1, zeroFilledAdminAndPrint, 
                                            [self, orderNum, filledObj, unfilledObj, fillPrice]).start()

###############
        
def zeroFilledAdminAndPrint(self, orderNum, filledObj, unfilledObj, fillPrice):
    
    printOneLiner('orderNumberFilled', str(orderNum), str(self.ordersFilled)) 

#    unfilledObj.order["fade_launched"] = True                
    printOneLiner('orderLaunched', "Fade", str(unfilledObj.order["lmt_id"]), 
                                           str(unfilledObj.price['fade']))

    self.cancelMktData(  filledObj.ibkr_ticker_id)
    self.cancelMktData(unfilledObj.ibkr_ticker_id)
    printOneLiner('mktDataCanc')


# In[6]:


#called from secondaryOrders

def oneFilled(self, orderNum, shsRemaining, filledObj, unfilledObj, filledOrderType, fillPrice):
    
    if (not unfilledObj.order["stop_launched"]):
        stopOrder(self, unfilledObj)
        shsRemaining = -1  #prevents from next if statement
        
    if shsRemaining == 0:
        cancelAndCalculate(self, orderNum, filledObj, unfilledObj, filledOrderType, fillPrice)
        


# In[7]:


# called from oneFilled

def stopOrder(self, obj):

#launchStopOrder           
    stopPrice = obj.price['fade'] + obj.price["stp_adj"]
    stopPrice = tc.convertToIncrement(stopPrice, obj.price["tick_inc"], "round") 

    obj.order["stp"].auxPrice = stopPrice               
    ibM.ibkrLaunchOrder(self, obj, "stp")

    stopOrderCounter = threading.Timer(0.1, stopOrderAdminAndPrint, 
                                       [obj, stopPrice]).start()

############

def stopOrderAdminAndPrint(obj, stopPrice):
    obj.order["stop_launched"] = True
    printOneLiner("orderLaunched", "Stop", str(obj.order["stp_id"]), str(stopPrice))


# In[8]:


#called from oneFilled

def cancelAndCalculate(self, orderNum, filledObj, unfilledObj, filledOrderType, fillPrice):
           
    unfilledOrderType = hc.getOpp(filledOrderType.upper(), "LMT", "STP").lower()
    self.cancelOrder(filledObj.order[unfilledOrderType + '_id'], "") 

    time.sleep(1)
    self.disconnect()
    time.sleep(1) 

    self.ordersFilled = 2
    filledObj.order['filled'] = True        
    filledObj.price["fill"] = fillPrice

    printOneLiner('orderNumberFilled', str(orderNum), str(self.ordersFilled))
    
    if filledObj.whole_days_to_expiry_cf == self.daysList[0]:
        firstObj = filledObj
        lastObj  = unfilledObj
    else:
        firstObj = unfilledObj
        lastObj  = filledObj        
    
    self.profit["final"] = self.calcPricingEngine(-firstObj.price['scalar_pkg'] * firstObj.price["fill"],
                                                   firstObj.size ['scalar_pkg'] * firstObj.comm ["mkt_" + firstObj.bid_ask], 
                                                    lastObj.price['scalar_pkg'] *  lastObj.price["fill"], 
                                                    lastObj.size ['scalar_pkg'] *  lastObj.comm ["mkt_" +  lastObj.bid_ask], 
                                                   firstObj)
             
    printSummaryInfo("final", firstObj, lastObj, self.profit["final"])
    

