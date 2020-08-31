import time
from datetime import datetime
import smtplib
import config as cfg
import requests

# getting tickers
ticker_list = []
# ticker_list_condensed = ['AAPL']
company_file = open(cfg.file['company_list'])
ctr = 0
for line in company_file:
    # debugging
    # if len(ticker_list) >= 10:
    #     break
    ticker_list.append(line.split('|')[0])

yearlyProfit = 0.00
totalProfit = 0.00
totalSpent = 0.00

#variables
year = 2015
yearMax = 2019
sellTop = 1.0
sellBottom = -.05
lowLim = 1
line = .05
with open(str(year) + '-' + str(yearMax) + '_lessThan1_'  + str(sellTop*100) + ':' + str(sellBottom*100) + '.csv', 'w') as file:
    while year <= yearMax:
        prioryear = year - 1
        startdateprior = str(prioryear) + '-01-01'
        enddateprior = str(prioryear) + '-12-31'
        startdate = str(year) + '-01-01'
        enddate = str(year) + '-12-31'
        yearSpent = 0.0
        #get 52 week low
        for ticker in ticker_list:
            low = 100000.00
            vol = 0
            urlPast = 'https://api.tiingo.com/tiingo/daily/' + ticker + '/prices?token=' + cfg.file['token'] + '&startDate=' + startdateprior + '&endDate=' + enddateprior + '&format=json&resampleFreq=daily'
            try:
                # uncomment this portion for debugging
                # if ctr == lim:
                #     break
                r = requests.get(urlPast)
                json_result = r.json()
                for item in json_result:
                    low = float(item['low']) if (float(item['low']) < low) else low
                    vol = float(item['volume'])
                    if (low > lowLim or vol == 0):
                        break
                    #print(low)
                    # ctr += 1
            except Exception as error:
                print(error)
            if (low > lowLim or low == 10000 or vol == 0):
                continue
            #run sim
            url = 'https://api.tiingo.com/tiingo/daily/' + ticker + '/prices?token=' + cfg.file['token'] + '&startDate=' + startdate+ '&endDate=' + enddate + '&format=json&resampleFreq=daily'
            dayHigh = 100000.00
            dayClose = 100000.00
            invested = False
            boughtAt = 0.0
            prof = 0.0
            try:
                r = requests.get(url)
                json_result = r.json()
                for item in json_result:
                    dayClose = float(item['close'])
                    dayOpen = float(item['open'])
                    if (dayClose >= 10000 or dayOpen >= 10000):
                        break
                    percFromLow = (dayClose - low) / low
                    if invested:
                        percFromBought = (dayClose - boughtAt) / boughtAt
                        if percFromBought >= sellTop:
                            prof += (dayClose - boughtAt)
                            invested = False
                            boughtAt = 0.0
                            if (prof > 5000): 
                                print('')
                                break
                            break
                        elif percFromBought <= sellBottom:
                            prof += (dayClose - boughtAt)
                            invested = False
                            boughtAt = 0.0
                            break
                    elif not invested:        
                        if percFromLow < line:
                            boughtAt = dayClose
                            totalSpent += dayClose
                            yearSpent += dayClose
                            invested = True
            except Exception as error:
                print(error)

            if (dayClose >= 10000 or dayOpen >= 10000):
                continue
            if boughtAt != 0 :
                if prof == 0:
                    prof += (dayClose - boughtAt)

            #print total gains from year
            if prof != 0:
                if (prof > 5000): 
                    continue
                file.write(str(year) + ': ' + ticker + ': ' + str(round(prof, 2)))
                file.write('\n')
                print(str(year) + ': ' + ticker + ': ' + str(round(prof, 2)))
                yearlyProfit += prof
                totalProfit += prof
                # if (totalProfit >= 10000):
                #     print('profit too high')
            else:
                file.write(str(year) + ': ' + ticker + ': ' + 'No Purchases')
                file.write('\n')
                print(str(year) + ': ' + ticker + ': ' + 'No Purchases')

        yearProfPerc = yearlyProfit / yearSpent
        print('\n' + '\n' + 'YEAR SPENT FOR ' + str(year) + ': ' + str(yearSpent) + '\n') 
        print('YEAR PROFIT FOR ' + str(year) + ': ' + str(yearlyProfit) + '\n')
        print('PROFIT PERCENT FOR ' + str(year) + ': ' + str(yearProfPerc) + '\n' + '\n') 
        file.write('\n' + '\n' + 'YEAR SPENT FOR ' + str(year) + ': ' + str(yearSpent) + '\n')
        file.write('YEAR PROFIT FOR ' + str(year) + ': ' + str(yearlyProfit) + '\n')
        file.write('PROFIT PERCENT FOR ' + str(year) + ': ' + str(yearProfPerc) + '\n' + '\n')
        year += 1
        yearlyProfit = 0.00
        yearSpent = 0.00
        yearProfPerc = 0.00

    totalProfPerc = totalProfit / totalSpent
    print('\n' + '\n' + 'TOTAL SPENT: ' + str(totalSpent))
    print('\n' + 'TOTAL PROFIT: ' + str(totalProfit))
    print('\n' + 'TOTAL PROFIT PERCENT: ' + str(totalProfPerc))
    file.write('\n' + '\n' + 'TOTAL SPENT: ' + str(totalSpent))
    file.write('\n' + 'TOTAL PROFIT: ' + str(totalProfit))
    file.write('\n' + 'TOTAL PROFIT PERCENT: ' + str(totalProfPerc))