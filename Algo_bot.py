"""
Created by Karl Lawson and Daniel Bunch
Liquidity Bot(REEK v1.0)

"""


from urllib.request import urlopen, Request
from urllib.parse import urlencode
import json
import math
import time
from datetime import datetime
import sys

import auth
token = auth.token
inputToken = "Token " + token

cancelURL = ""

def trailingStop(accountURL, instrumentURL, symbol, currPrice, quantity, inputToken, cancelURL):
    print("Creating new stop loss")

    if cancelURL != "":
        q = Request(cancelURL)
        q.add_header("Accept", "application/json")
        q.add_header("Authorization", inputToken)
        q.method = "POST"
        html = urlopen(q)

    stopPercentage = .05
    
    orderType = "market"
    timeInForce = "gtc"
    trigger = "stop"
    side = "sell"
    
    percentage = 1 - stopPercentage
    currPrice = float(currPrice)
    
    stopPrice = (currPrice * percentage)
    if(stopPrice > 1.0):
        stopPrice = round(stopPrice, 2)     #if the stock is greater than 1 then it can't go past 2 decimal places.
    else:
        stopPrice = round(stopPrice, 4)    #rounds the stop price to 4 decimal places because the api can only take up to 4 decimal places.

    #helpful for debugging ************
	#Uncomment if there are problems.
    #print()
    #print(accountURL)
    #print(instrumentURL)
    #print(quantity)
    #print(side)
    #print(symbol)
    #print(currPrice)
    #print(stopPrice)
    #print()
    #**********************************

    values = {'account': accountURL, 'instrument': instrumentURL, 'quantity': quantity, 'side': side, 'symbol': symbol, 'time_in_force': timeInForce, 'trigger': trigger, 'type': orderType, 'price' : currPrice, 'stop_price': stopPrice}
    data = urlencode(values).encode()
  
    q = Request("https://api.robinhood.com/orders/", data)

    q.add_header("Accept", "application/json")
    q.add_header("Authorization", inputToken)


    html = urlopen(q)
    response = (html.read())
    array = json.loads(response)
    cancel = array["cancel"]

    print("Created stop loss at price of " + str(stopPrice))

    return cancel


q = Request("https://api.robinhood.com/accounts/")
q.add_header("Authorization", inputToken)
html = urlopen(q)
response = (html.read())
array = json.loads(response)
accountURL = (array["results"][0]["url"])
accountID = array["results"][0]["account_number"]
availableCash = float(array["results"][0]["buying_power"])  #Will use all margin if the account is using it.

#********************************************
#Uncomment if wanting to set limit on money it can use.
#availableCash = 25      #sets the max money it will use to $25
#********************************************


#Find stock to buy****************************************

endTime = time.time() + (60*10) #10 minutes
margin = 1.25 #25% higher than normal average volume
symbol = ""
PercentageOverAvgVolume = 0.0


print()
print("Searching for a stock master...")
while time.time() < endTime:
    stockFile = open("stocks.txt")
    for line in stockFile:
        try:
            line = line.strip()     #gets rid of the extra spaces around the line

            html = urlopen("https://api.robinhood.com/fundamentals/" + line + "/")
            response = (html.read())        
            array = json.loads(response)

            if float(array["volume"]) > (float(array["average_volume"]) * margin) and float(array["volume"]) > 100000:  #margin is to make sure it is not just barely larger and to make sure that the volume is greater than 100,000

                #get the current price
                html = urlopen("https://api.robinhood.com/quotes/" + line + "/")   
                response = (html.read())        
                array = json.loads(response)
                currPrice = float(array["bid_price"])
                openPrice = float(array["adjusted_previous_close"])

                if openPrice < currPrice: 
                    symbol = line
                    break

            time.sleep(.2)
        except KeyboardInterrupt:
            print("Keyboard interrupt. Exiting early.")
            sys.exit(0)
        except:
            pass
        

    stockFile.close()

    if(symbol != ""):
        break

#*********************************************************
if symbol == "":
    print("I am sorry master, I have failed you.")
    sys.exit(0)
else:
    print("I have found a stock master it is called {}".format(symbol))
    print()



#Buy picked stock******************************************************
html = urlopen("https://api.robinhood.com/fundamentals/" + symbol + "/")   
response = (html.read())        
array = json.loads(response)
instrumentURL = (array["instrument"])

html = urlopen("https://api.robinhood.com/quotes/" + symbol + "/")   
response = (html.read())        
array = json.loads(response)
price = float(array["bid_price"])

calcPrice = price * 1.10    #calculates price with a 10% premium
quantity = math.floor(availableCash / calcPrice)

#Helpful for debugging*****************
#Uncomment if there are problems
#print(availableCash)
#print(accountURL)
#print(instrumentURL)
#print(quantity)
#print(symbol)
#print(price)
#***************************************

#uses the price that is calculated because it is higher than the current causing the order to execute right away.
calcPrice = round(calcPrice, 2)
print (calcPrice)

values = {'account': accountURL, 'instrument': instrumentURL, 'quantity': quantity, 'side': "buy", 'symbol': symbol, 'time_in_force': 'gtc', 'trigger': "immediate", 'type': "market", 'price' : calcPrice}
data = urlencode(values).encode()
q = Request("https://api.robinhood.com/orders/", data)
q.add_header("Accept", "application/json")
q.add_header("Authorization", inputToken)

html = urlopen(q)
response = (html.read())
array = json.loads(response)

orderID = array["id"]
buyCancelURL = array["cancel"]


highestPrice = 0.0
time.sleep(.5)

count = 0

if array["state"] != "filled":
    print("Checking to make sure that the order has gone through.")
    print(orderID)
    while True:
        tempURL = "https://api.robinhood.com/orders/" + orderID
        q2 = Request(tempURL)
        q2.add_header("Accept", "application/json")
        q2.add_header("Authorization", inputToken)

        html2 = urlopen(q2)
        response2 = (html2.read())
        array2 = json.loads(response2)
        if array2["state"] == "filled":
            highestPrice = float(array2["average_price"])
            break
        
        if(count >= 1500):  #cancels buy if it takes more than 5 minutes to fill
            q2 = Request(buyCancelURL)
            q2.add_header("Accept", "application/json")
            q2.add_header("Authorization", inputToken)
            q2.method = "POST"
            html2 = urlopen(q2)
            sys.exit(0)
        count += 1

        time.sleep(.2)
else:
    highestPrice = float(array["average_price"])
    
print("The order has gone through. I am now setting an initial stop loss.")

#set stop loss
cancelURL = trailingStop(accountURL, instrumentURL, symbol, highestPrice, quantity, inputToken, cancelURL)

temp = instrumentURL.split("/")
instrumentID = temp[4]

print("Master, I have bought the stock for " + str(highestPrice))

closing = datetime(1970, 1, 1, 14, 45)  #15 minutes before the stock market closes
sold = False
while closing.time() > datetime.now().time():
    print ("Checking current price")
    
    url = "https://api.robinhood.com/positions/" + accountID + "/" + instrumentID + "/"
    q = Request(url)
    q.add_header("Accept", "application/json")
    q.add_header("Authorization", inputToken)
    html = urlopen(q)
    response = (html.read())
    array = json.loads(response)

    if float(array["quantity"]) == 0:   #If stock has been sold then exit the loop
        sold = True
        break


    html = urlopen("https://api.robinhood.com/quotes/" + symbol + "/")
    response = (html.read())        
    array = json.loads(response)
    currentPrice = float(array["bid_price"])

    if currentPrice > highestPrice:
        cancelURL = trailingStop(accountURL, instrumentURL, symbol, currentPrice, quantity, inputToken, cancelURL)
        highestPrice = currentPrice

    
    time.sleep(60)

if(not sold):
    #cancels the stop loss
    q = Request(cancelURL)
    q.add_header("Accept", "application/json")
    q.add_header("Authorization", inputToken)
    q.method = "POST"
    html = urlopen(q)

    html = urlopen("https://api.robinhood.com/quotes/" + symbol + "/")
    response = (html.read())        
    array = json.loads(response)
    currentPrice = array["bid_price"]


    values = {'account': accountURL, 'instrument': instrumentURL, 'quantity': quantity, 'side': "sell", 'symbol': symbol, 'time_in_force': 'gtc', 'trigger': "immediate", 'type': "market", 'price' : currentPrice}
    data = urlencode(values).encode()
    q = Request("https://api.robinhood.com/orders/", data)
    q.add_header("Accept", "application/json")
    q.add_header("Authorization", inputToken)

    html = urlopen(q)

    print("The stock has been sold master.")
    


