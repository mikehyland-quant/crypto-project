#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#imports
from datetime import datetime, timezone, timedelta, date
from dateutil import parser
import time

#from IBKR
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract, ComboLeg
from ibapi.tag_value import TagValue
from ibapi.order import *

#self-written shortcuts
import Methods_Trading as trading


# In[ ]:


class IBKRLightOW(EWrapper, EClient):     
       
    
    def __init__(self):
        EClient.__init__(self, self)

        
    def nextValidId(self, orderNum):
        super().nextValidId(orderNum)
        print("\n")
        print("Successful API client connection confirmed -> Next OrderId = ", orderNum) 
        self.orderID = orderNum

        
    def tickPrice(self, tickerId, field, price, attribs):
        super().tickPrice(tickerId, field, price, attribs)
        if field in [1, 2, 9]:
            ibkrPriceSizeGrabber(self, tickerId, field, price)
        
        
    def tickSize(self, tickerId, field, size):
        super().tickSize(tickerId, field, size)
        if field in [0, 3, 8, 21]:
            ibkrPriceSizeGrabber(self, tickerId, field, size)
            
            
    def position(self, account, contract, position, avgCost):
        super().position(account, contract, position, avgCost)

        objList = [obj for key, obj in self.ibkrDictID.items() if obj.ibkr_contractID == contract.conId]
        if len(objList) == 1:
            obj = objList[0]
            obj.current_position = position
            
                       
#    def securityDefinitionOptionParameter(self, reqId: int, exchange: str, 
#                                          underlyingConId: int, tradingClass: str, multiplier: str, 
#                                          expirations: SetOfString, strikes: SetOfFloat):
#        super().securityDefinitionOptionParameter(self, reqId, exchange, underlyingConId, 
#                                                  tradingClass, multiplier, expirations, strikes)
#        print(reqId, exchange, underlyingConId, tradingClass, multiplier, expirations, strikes)
                        


# In[ ]:


class IBKRLightOWTrader(IBKRLightOW):     
       
    
    def __init__(self):
        IBKRLightOW.__init__(self)
        
    
    def orderStatus(self, orderNum, status, filled, remaining, avgFillPrice, 
                    permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        super().orderStatus(orderNum, status, filled, remaining, avgFillPrice, 
                    permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice)      
        print("Order Number:", orderNum, status, 
              "(f/u = ", filled, "/", remaining, ")", "\n")            
        trading.secondaryOrders(self, orderNum, remaining, filled, avgFillPrice)           
             
                  
    def tickPrice(self, tickerId, field, price, attribs):
        super().tickPrice(tickerId, field, price, attribs)
        if field in [1, 2, 9]:
            ibkrPriceSizeTrader(self, tickerId, field, price)
        
        
    def tickSize(self, tickerId, field, size):
        super().tickSize(tickerId, field, size)
        if field in [0, 3, 8, 21]:
            ibkrPriceSizeTrader(self, tickerId, field, size)
            
            
    def getIBKROrderID(self):
        oID = self.orderID
        self.orderID = self.orderID + 1      
        return oID
            


# In[ ]:


# get client number for IBKR connection
def getIBKRClientNumber():
    
    current = str(datetime.now().time())
    clientNumber = float(current[0:2] + current[3:5] + current [6:8]) 
    print('IBKR client number is ', int(clientNumber))
    
    return int(clientNumber)


# In[ ]:


def ibkrFinInstObject(symbol, primaryExchange, ttype = "STK", expiry = "X", strike = 'X', putCall = 'X'):
    
    contractObj = Contract()
    contractObj.currency = "USD" 
    contractObj.exchange = "SMART"
    
    contractObj.symbol = symbol
    contractObj.secType = ttype
    contractObj.primaryExchange = primaryExchange  
    
    if ttype == "CRYPTO":
        contractObj.exchange = primaryExchange
    elif ttype == "FUT":
        contractObj.exchange = primaryExchange
        contractObj.lastTradeDateOrContractMonth = expiry
    
    return contractObj


# In[ ]:


def ibkrFutSpreadObject(spreadObject):
    
    contractObj          = Contract()
    contractObj.currency = "USD" 
    contractObj.exchange = "SMART"
    contractObj.secType  = spreadObject.ibkr_type
    
    contractObj.symbol   = spreadObject.symbol
        
    leg1                 = ComboLeg()
    leg1.conId           = int(spreadObject.leg1["ibkr_contractID"])
    leg1.ratio           = spreadObject.leg1["ratio"]      
    leg1.action          = spreadObject.leg1["action"] 
    leg1.exchange        = spreadObject.leg1["exchange"]     

    leg2                 = ComboLeg()
    leg2.conId           = int(spreadObject.leg2["ibkr_contractID"])
    leg2.ratio           = spreadObject.leg2["ratio"]      
    leg2.action          = spreadObject.leg2["action"] 
    leg2.exchange        = spreadObject.leg2["exchange"]     

    contractObj.comboLegs = []
    contractObj.comboLegs.append(leg1)
    contractObj.comboLegs.append(leg2)
    
    return contractObj


# In[ ]:


#attributes: 165 is for avg volume, 225 is for auctions, 236 is for shortable
def startIBKR(self, objDict, variablesDict, attributes = "", createIBKRObj=False):
        
    self.connect("127.0.0.1", int(variablesDict["IBKR Port"]), variablesDict["Channel"])
    time.sleep(2) 

    for key, obj in objDict.items():
        
        if createIBKRObj:
            
          
            if obj.product_type == "option": 
                pass
            
            
            elif obj.product_type == "futures spread":  
                obj.ibkr_object = ibkrFutSpreadObject(obj)
                
            
            
            else:                                 
                obj.ibkr_object = ibkrFinInstObject(obj.symbol,    obj.exch_name, 
                                                    obj.ibkr_type, obj.ibkr_expiry)
                 

        self.reqMktData(int(obj.ibkr_ticker_id), obj.ibkr_object, attributes, False, False, [])
        time.sleep(1)              



# In[ ]:


#self.ibkrDictID is defined outside of this module

def ibkrPriceSizeGrabber(self, tickerId, field, amount):
 
    obj = self.ibkrDictID[tickerId]
    
    varNameDict = { 0 : "bid",
                    1 : "bid",
                    2 : "ask",
                    3 : "ask",
                    8 : 'volume',
                    9 : "close",
                   21 : "avg_volume"}
    
    action = varNameDict[field]
        
    if   field in [1, 2, 9]: 
        obj.calc_prices(amount, action)
        if field != 9:
            obj.calc_cashflows(action)
        
    elif field in [0, 3]:
        obj.calc_sizes (amount, action)
        
    elif field in [8, 21, 89]:
        obj.mkt_size[action] = float(amount)


# In[ ]:


#self.ibkrDictID is defined outside of this module

def ibkrPriceSizeTrader(self, tickerId, field, amount): 
            
    ibkrPriceSizeGrabber(self, tickerId, field, amount)
    
    if self.ordersFilled > -1:
        trading.checkMktData(self, tickerId, field)    
    
    #if shortable shares goes below order size while order is yet 
    #to be filled then IBKR will cancel the order automatically  


# In[ ]:


def ibkrOrderObject(buySell, quantity, price, oType, oRTH=True):
    
    objectName = Order()
    objectName.action = buySell
    objectName.totalQuantity = quantity
    objectName.orderType = oType
    objectName.outsideRth = oRTH 
    
    if oType == "LMT":
        objectName.lmtPrice = price
    elif oType == "STP":
        objectName.auxPrice = price
    
    return objectName 


# In[ ]:


def ibkrLaunchOrder(self, obj, lmtStp): 

    if (obj.order[lmtStp + "_id"] == None):
        obj.order[lmtStp + "_id"] = self.getIBKROrderID()  

    self.placeOrder(obj.order[lmtStp + "_id"], 
                    obj.ibkr_obj, 
                    obj.order[lmtStp])

