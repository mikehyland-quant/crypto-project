#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#imports
import threading

#self-written shortcuts
from   Class_FI_Equities  import *
from   Class_FI_Futures   import *
from   Class_FI_Spot      import *

from   Methods_Core       import *
from   Methods_DataCheck  import *
from   Methods_IBKR       import *
import Methods_Pricing    as pricing
from   Methods_Printing   import *
import Methods_Trading    as trading


# In[ ]:


def getData():
 
    workbookName      = getWorkbookName()                                                #above
    variablesDict     = getSpreadsheetVariables(workbookName, 'Initial Variables', 'B1') #core
    
    df                = getFinInstsDFTrade(variablesDict)

    finInstDict       = {}
    for row in df.index:
        tempDict      = df.loc[row].to_dict()

        if tempDict['platform'] == "WS" or tempDict['platform'] == "IBKR":
            
            if   tempDict['product_type'] == 'equity':
                obj   = EquityTrader(tempDict)
            
            elif tempDict['product_type'] == 'future':
                obj   = FutureTrader(tempDict)
                
            elif tempDict['product_type'] == 'spot':
                obj   = SpotTrader(tempDict)
                
            objName   = obj.object_name
            finInstDict[objName] = obj
                                 
  #      elif tempDict['platform'] == "LX":
   #         lxDict      = makeLXContractInfoDict(tempDict)
    #        finInstDict = {** finInstDict, **lxDict}
 
    return finInstDict, variablesDict


# In[ ]:


class noIBKRTrader():
    
    def __init__(self, finInstDict, variablesDict):
                                      
        #initialize dictionaries in main2  
        self.finInstDict              = {}
        self.finInstDictID            = {}
        
        self.ibkrDict                 = {}
        self.ibkrDictID               = {}        
        self.ibkrTrueFalse            = False
         
        #assign objects to dictionaries; one for products and one for platforms
        i = 0
        for name, obj in finInstDict.items():
            self.finInstDict[name]    = obj
            self.finInstDictID[i]     = obj
            obj.fin_inst_id           = i
                            
            if obj.platform          == "IBKR":
                self.ibkrDict[name]   = obj
                self.ibkrDictID[i]    = obj
                obj.ibkr_ticker_id    = i    
            i = i + 1
            
        self.ordersFilled             = -1

        self.variablesDict            = variablesDict 
        
        self.profit                   = {}
        self.profit['target']         = None
        self.profit['final']          = None
             
        tempList                      = [self.finInstDictID[0].whole_days_to_expiry_cf,
                                         self.finInstDictID[1].whole_days_to_expiry_cf]
        self.daysList                 = [min(tempList), max(tempList)]

        
        prepPricingEngine(self, variablesDict)

        
    def pricingEngine(self, inputObj, outputObj, df, fadePrice):
        pricingEngine(self, inputObj, outputObj, df, fadePrice)

    def calcPricingEngine(self, fadeFlow, fadeComm, showFlow, showComm, inputObj):
        profitAmt = calcPricingEngine(self, fadeFlow, fadeComm, showFlow, showComm, inputObj)
        return profitAmt

###############


class yesIBKRTrader(IBKRLightOWTrader, noIBKRTrader):
    
    def __init__(self, finInstDict, variablesDict):
        
        IBKRLightOWTrader.__init__(self)
        noIBKRTrader.__init__(self, finInstDict, variablesDict)
        
        self.variablesDict["Channel"] = getIBKRClientNumber()
        self.ibkrTrueFalse = True 
               


# In[ ]:


def prepPricingEngine(self, varsDict):
    
    self.profit['target']    = float(varsDict['profit%'])
        
    self.daysInDenom         = varsDict['daysInDenom']
 
    yearFracCommRate         = self.daysList[0]   / self.daysInDenom    
    self.commScalar          = 1 + (float(self.profit['target']) * yearFracCommRate)
    
    self.yearFracIntRate     = (self.daysList[1] - self.daysList[0])  / self.daysInDenom    
    self.profitScalar        = 1 + (float(self.profit['target']) * self.yearFracIntRate)
    
    
###############


def pricingEngine(self, inputObj, outputObj, df, fadePrice):
    
    showPrice = pricing.buyNowSellLater(self, inputObj, outputObj, df) 
    trading.initialOrders(self, inputObj, outputObj, fadePrice, showPrice)
    
    
###############


def calcPricingEngine(self, fadeFlow, fadeComm, showFlow, showComm, inputObj):    
    profitAmt = pricing.calcBuyNowSellLater(self, fadeFlow, fadeComm, showFlow, showComm, inputObj)
    return profitAmt
        


# In[ ]:


def main():
    
    finInstDict, variablesDict = getData()

    platformList = [obj.platform for key, obj in finInstDict.items()]
      
    if "IBKR" in platformList:       #connect to IBKR 
        main2 = yesIBKRTrader(finInstDict, variablesDict) 
        startIBKR(main2, main2.finInstDict, main2.variablesDict, createIBKRObj=True)
#        main2.reqPositions()
        timerRunIBKR = threading.Timer(1, main2.run, []).start()
  
        timerTOCounter = threading.Timer(3, timeoutCounter, [main2])
        timerTOCounter.start()
        timerTOCounter.join()        
    else:                            #don't connect to IBKR   
        main2 = noIBKRTrader(finInstDict, variablesDict)        

        
#    if "WS" in platformList:
#    if "LX" in platformList:
        
        
    if main2.mktDataOK:   #this variable is set in timeoutCounter above    
        printSummaryInfo("initial", main2.finInstDictID[0], main2.finInstDictID[1], 
                                    main2.profit['target'], main2.variablesDict["tradingUnits"])        
       
        permissionGranted = getPermission(main2.finInstDictID[0], main2.finInstDictID[1])  
        #permissionGranted could be FALSE depending on user response
        
                     
        if permissionGranted:
            
            for rounds in range(int(main2.variablesDict['tradingUnits'])):
                main2.ordersFilled = 0   #allows for initialTrades to be launch limit orders
                
                for key, obj in main2.finInstDict.items(): 
                    obj.calcOffMktPrices(main2.variablesDict["offMktPercentage"])
                    obj.resetMktPrices()
            
            
            
                startIBKR(main2, main2.finInstDict, main2.variablesDict)
                main2.reqOpenOrders()
                #main2.reqPositions()                
                main2.run()  
                #followUpOrder ends self.run() via self.disconnect() call 
                #after both orders filled and returns to here
        
                if rounds < main2.variablesDict['tradingUnits']:
                    for key, obj in main2.finInstDict.items():
                        obj.resetOrderIDs()
                    
                    
                    
    printOneLiner('programComplete')    
    exit()


# In[ ]:


main()

