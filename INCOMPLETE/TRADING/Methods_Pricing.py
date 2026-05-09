#!/usr/bin/env python
# coding: utf-8

# In[7]:


#imports
import pandas as pd


# In[ ]:


def buySellDollarSpread(self, inputObj, outputObj, df): 
       
    outputIndex           = outputObj.fin_inst_id

    
    if outputObj.comm['type'] == 'flat':
        outputComm        = outputObj.size ['scalar_pkg'] * outputObj.comm["mkt_" + outputObj.bid_ask]
        outputCommDays    = outputObj.whole_days_to_comm
        df.loc[outputIndex, outputCommDays] = df.loc[outputIndex, outputCommDays] + outputComm
 
        zeroFlow          = df[0].sum()
        nearFlow          = zeroFlow * self.commScalar
        
        nearFlow          = df[self.daysList[0]].sum() + nearFlow
        farFlow           = df[self.daysList[1]].sum()
 
        showFlow          = self.profit['target'] - nearFlow
        if self.daysList[0] != self.daysList[1]:
            showFlow      = showFlow - farFlow 
            
            
    showPrice             = abs(showFlow / outputObj.price['scalar_pkg'])


    return showPrice

    
###############    
    
    
def calcBuySellDollarSpread(self, fadeFlow, fadeComm, showFlow, showComm): 

    profitAmt = fadeFlow + fadeComm + showFlow + showComm
        
    return profitAmt
    


# In[8]:


def buyNowSellLater(self, inputObj, outputObj, df): 
              
    outputIndex           = outputObj.fin_inst_id
      
        
    if outputObj.comm['type'] == 'flat':
        outputComm        = outputObj.size ['scalar_pkg'] * outputObj.comm["mkt_" + outputObj.bid_ask]
        outputCommDays    = outputObj.whole_days_to_comm
        df.loc[outputIndex, outputCommDays] = df.loc[outputIndex, outputCommDays] + outputComm
        
        zeroFlow = df[0].sum()
        nearFlow = zeroFlow * self.commScalar
        
        nearFlow = df[self.daysList[0]].sum() + nearFlow
        farFlow  = df[self.daysList[1]].sum()
       
        if inputObj.whole_days_to_expiry_cf == self.daysList[0]:
            farFlowTotal  = nearFlow * -self.profitScalar 
            showFlow      = farFlowTotal - farFlow
            
        elif inputObj.whole_days_to_expiry_cf == self.daysList[1]:
            nearFlowTotal = farFlow / -self.profitScalar
            showFlow      = nearFlowTotal - nearFlow
            
        else:
            print("problem", "buyNowSellFwd")

    
    showPrice             = abs(showFlow) / outputObj.price['scalar_pkg']
         
    return showPrice



###############
    
    
def calcBuyNowSellLater(self, fadeFlow, fadeComm, showFlow, showComm, inputObj): 
          
    if inputObj.whole_days_to_expiry_cf == self.daysList[0]:
        nearCF    = fadeFlow  + fadeComm + showComm
        farCF     = showFlow 

    elif inputObj.whole_days_to_expiry_cf == self.daysList[1]:
        nearCF    = showFlow + fadeComm + showComm
        farCF     = fadeFlow 

    else:
        print('problem', 'calcBuyNowSellFwd')
    
    profitAmt = ((-farCF / nearCF) - 1) * (1 / self.yearFracIntRate)
        
    return profitAmt
    

