from datetime import datetime
from datetime import date
from dateutil.relativedelta import relativedelta
from requests_oauthlib import OAuth1Session
import time
import smtplib
import config as cfg
import requests
import Stock

# getting tickers
ticker_list = []
ticker_list_condensed = []
stocks_bought = {}
sym_ign = ['D', 'FNCL', 'GLD', 'IEFA', 'ILTB' , 'OKE', 'PICK', 'SCHD', 'SCHH', 'VGT', 'VIG', 'VOOV', 'XBI']
company_file = open(cfg.file['company_list'])
for line in company_file:
    ticker_list.append(line.split('|')[0])

#variables
sellTop = 1.0
sellBottom = -.05
line = .05

# initialize
url = 'https://api.tradeking.com/v1/market/ext/quotes.json?symbols='
# ctr = 0
# lim = 50
price_max = 1
price_min = .01
auth = OAuth1Session(
    cfg.key['consumer_key'],
    cfg.key['consumer_secret'],
    cfg.key['oauth_token'],
    cfg.key['oauth_token_secret'])

# filter out expensive stocks
for ticker in ticker_list:
    if ticker not in sym_ign:
        temp_url = url + ticker
        try:
            # uncomment this portion for debugging
            # if ctr == lim:
            #     break
            time.sleep(1)
            r = auth.get(temp_url)
            json_result = r.json()
            ask_str = json_result['response']['quotes']['quote']['ask']
            ask = float(ask_str) if ask_str != '' else 0
            if ask <= price_max and ask != 0 and ask >= price_min:
                ticker_list_condensed.append(ticker)
                print(ticker)
                # ctr += 1
        except Exception as error:
            print(error)

#empty loop until market opens
before_hours = True
while before_hours:
    cur_time = datetime.now()
    hour = cur_time.hour
    minute = cur_time.minute
    if (hour == 9 and minute > 30) or hour >= 10:
        before_hours = False

# market has opened
market_open = True
while market_open:
    for ticker in ticker_list_condensed:
        if not market_open:
            break
        # check if market still open
        cur_time = datetime.now()
        hour = cur_time.hour
        if hour >= 16:
            market_open = False
            break

        # select stocks to suggest
        temp_url = url + ticker
        try:
            time.sleep(1)
            r = auth.get(temp_url)
            json_result = r.json()
            ask = float(json_result['response']['quotes']['quote']['ask'])
            low = float(json_result['response']['quotes']['quote']['wk52lo'])
            rate_from_low = (ask - low) / low
            if rate_from_low < line:
                # send email to buy stock
                stocks_bought[ticker] = ask
                smtp_server = "smtp.gmail.com"
                port = 587
                sender = cfg.email['receiver']
                receiver = cfg.email['receiver']
                password = cfg.email['password']
                message = 'Buy ' + ticker + ' at ' + str(ask) + ' (' \
                        + str(round(rate_from_low, 4) * 100) + '% from 52 week low)'
                try:
                    server = smtplib.SMTP(smtp_server, port)
                    server.starttls()
                    server.login(sender, password)
                    server.sendmail(sender, receiver, message)
                    ticker_list_condensed.remove(ticker)
                except Exception as error:
                    print('ERROR: ', error)
        except Exception as error:
            print('ERROR: ', error)

        #check to sell
        owned_url = 'https://api.tradeking.com/v1/accounts.json'
        auth = OAuth1Session(
            cfg.key['consumer_key'],
            cfg.key['consumer_secret'],
            cfg.key['oauth_token'],
            cfg.key['oauth_token_secret'])
        
        try: 
            holdings = {}
            request = auth.get(owned_url)
            profile = request.json()
            info = profile['response']['accounts']['accountsummary']
            stocks_owned = []
            for item in info:
                if item['account'] == cfg.key['account']:
                    stocks_owned.append(item['accountholdings']['holding'])
                    for holding in stocks_owned:
                        for item in holding: 
                            if item['displaydata']['symbol'] not in sym_ign:
                                holdings[item['displaydata']['symbol']] = (item['displaydata']['marketvalue'], item['displaydata']['costbasis'])
            for key, value in holdings.items():
                rate = (value[0] - value[1]) / value[0]
                if (rate >= sellTop or rate <= sellBottom):
                    #send email to sell stock
                    #stocks_bought.pop(key)
                    smtp_server = "smtp.gmail.com"
                    port = 587
                    sender = cfg.email['receiver']
                    receiver = cfg.email['receiver']
                    password = cfg.email['password']
                    message = 'Sell ' + key + ' at ' + str(value[0]) + ' (' \
                            + str(round(rate, 4) * 100) + '% from bought)'
                    try:
                        server = smtplib.SMTP(smtp_server, port)
                        server.starttls()
                        server.login(sender, password)
                        server.sendmail(sender, receiver, message)
                        ticker_list_condensed.append(key)
                        break
                    except Exception as error:
                        print('ERROR: ', error)
        except Exception as error:
            print('ERROR: ', error)
print('complete')
