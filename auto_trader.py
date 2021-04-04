from dateutil.relativedelta import relativedelta
from datetime import date, datetime, timedelta
from requests_oauthlib import OAuth1Session
from dateutil.parser import parse
import config as cfg
import requests
import smtplib
import time
from email.message import EmailMessage
import threading
from queue import Queue

# initialize
ticker_list_condensed = []
early_gainers = []
exclude_gains = []
exclude_hilo = []
exclude_close_open = []
marketClockUrl = 'https://api.tradeking.com/v1/market/clock.json'
rate_lim = .01
price_max = 10
price_min = .001
bought = {}
bought_gainers = False
profit = 0.0
spent = 0.0

def fillCondensed():
    if len(ticker_list_condensed) == 0:
        url = 'https://api.tradeking.com/v1/market/ext/quotes.json?symbols='    
        ctr = 0
        req_lim = 400
        lim_increment = 400
        for ticker in ticker_list:
            if ctr == req_lim:
                try:
                    r = auth.get(url)
                    json_result = r.json()
                    time.sleep(1)
                    for quote in json_result['response']['quotes']['quote']:
                        ask_str = quote['ask']
                        sym = quote['symbol']
                        ask = float(ask_str) if ask_str != '' else 0
                        if ask <= price_max and ask != 0 and ask >= price_min:
                            ticker_list_condensed.append(sym)
                            print(sym)
                    url = 'https://api.tradeking.com/v1/market/ext/quotes.json?symbols='   
                    req_lim += lim_increment 
                except Exception as e:
                    print(e)
                ctr += 1
                continue
            if ctr == req_lim - lim_increment:
                url += ticker
            else:
                url += ',' + ticker
            ctr += 1
        try:
            r = auth.get(url)
            json_result = r.json()
            time.sleep(1)
            for quote in json_result['response']['quotes']['quote']:
                ask_str = quote['ask']
                sym = quote['symbol']
                ask = float(ask_str) if ask_str != '' else 0
                if ask <= price_max and ask != 0 and ask >= price_min:
                    ticker_list_condensed.append(sym)
                    print(sym)
        except Exception as e:
            print(e)
        f = open(cfg.file['master_file'], "w")
        for ticker in ticker_list_condensed:
            f.write(ticker + '\n')
        f.close()

def readFromMasIfEmpty():
    try:
        if len(ticker_list_condensed) == 0:
            mas_file = open(cfg.file['master_file'])
            for line in mas_file:
                ticker_list_condensed.append(line.strip())
    except Exception as error:
        print(error)

def checkToSell():
    message = '\n'
    url = 'https://api.tradeking.com/v1/market/ext/quotes.json?symbols='    
    ctr = 0
    sell_gain = .05
    sell_loss = -.01
    for key in bought:
        if ctr == 0:
            url += key
        else:
            url += ',' + key
        ctr += 1
    try:
        r = auth.get(url)
        json_result = r.json()
        time.sleep(1)
        for quote in json_result['response']['quotes']['quote']:
            if quote['bid'] != '':
                prof = float(quote['bid']) - float(bought[quote['symbol']])
                percent_change = prof / float(bought[quote['symbol']])
                sym = quote['symbol']
                if percent_change >= sell_gain:
                    message = '\n\n' + 'Sold ' + sym + ' for ' + str(quote['bid']) + ' (' \
                        + str(round(percent_change, 4) * 100) + '% from bought)'
                    sendEmail(message)
                    profit += prof
                    bought.pop(sym)
                if percent_change <= sell_loss:
                    message = '\n\n' + 'Sold ' + sym + ' for ' + str(quote['bid']) + ' (' \
                        + str(round(percent_change, 4) * 100) + '% from bought)'
                    sendEmail(message)
                    profit += prof
                    bought.pop(sym)    
    except Exception as e:
        print(e)

def checkGains():
    message = '\n'
    url = 'https://api.tradeking.com/v1/market/ext/quotes.json?symbols='    
    ctr = 0
    req_lim = 400
    lim_increment = 400
    gain_check = .5
    for ticker in ticker_list_condensed:
        if ctr == req_lim:
            try:
                r = auth.get(url)
                json_result = r.json()
                time.sleep(1)
                for quote in json_result['response']['quotes']['quote']:
                    if quote['ask'] != '' and quote['cl'] != '':
                        percent_change = (float(quote['ask']) - float(quote['cl'])) / float(quote['cl'])
                        sym = quote['symbol']
                        if sym not in exclude_close_open:
                            if percent_change >= gain_check:
                                if clockJson == 'pre':
                                    early_gainers.append(sym)
                                    exclude_close_open.append(sym)
                                else:
                                    perc_change = (float(quote['ask']) - float(quote['cl'])) / float(quote['cl'])
                                    message = '\n\n' + 'Bought ' + str(quote['symbol']) + ' for ' + str(quote['ask']) + ' (' \
                                            + str(round(perc_change, 4) * 100) + '% from previous day close)'
                                    spent += float(quote['ask'])
                                    sendEmail(message)
                                    bought[sym] = float(quote['ask'])
                                    exclude_close_open.append(sym)
                req_lim += lim_increment 
                url = 'https://api.tradeking.com/v1/market/ext/quotes.json?symbols='   
            except Exception as e:
                print(e)
        if ctr == req_lim - lim_increment:
            url += ticker
        else:
            url += ',' + ticker
        ctr += 1
    try:
        r = auth.get(url)
        json_result = r.json()
        time.sleep(1)
        for quote in json_result['response']['quotes']['quote']:
            if quote['ask'] != '' and quote['cl'] != '':
                percent_change = (float(quote['ask']) - float(quote['cl'])) / float(quote['cl'])
                sym = quote['symbol']
                if sym not in exclude_close_open:
                    if percent_change >= gain_check:
                        if clockJson == 'pre':
                            early_gainers.append(sym)
                            exclude_close_open.append(sym)
                        else:
                            perc_change = (float(quote['ask']) - float(quote['cl'])) / float(quote['cl'])
                            message = '\n\n' + 'Bought ' + str(quote['symbol']) + ' for ' + str(quote['ask']) + ' (' \
                                    + str(round(perc_change, 4) * 100) + '% from previous day close)'
                            spent += float(quote['ask'])
                            sendEmail(message)
                            bought[sym] = float(quote['ask'])
                            exclude_close_open.append(sym)
    except Exception as e:
        print(e)

def buy_all_gainers():
    message = '\n'
    url = 'https://api.tradeking.com/v1/market/ext/quotes.json?symbols='    
    ctr = 0
    for key in early_gainers:
        if ctr == 0:
            url += key
        else:
            url += ',' + key
        ctr += 1
    try:
        r = auth.get(url)
        json_result = r.json()
        time.sleep(1)
        for quote in json_result['response']['quotes']['quote']:
            if quote['ask'] != '':
                perc_change = (float(quote['ask']) - float(quote['cl'])) / float(quote['cl'])
                message = '\n\n' + 'Bought ' + str(quote['symbol']) + ' for ' + str(quote['ask']) + ' (' \
                        + str(round(perc_change, 4) * 100) + '% from previous day close)'
                sendEmail(message)
                spent += float(quote['ask'])
                bought[quote['symbol']] = float(quote['ask'])
    except Exception as e:
        print(e)
    
def checkHiLo():
    url = 'https://api.tradeking.com/v1/market/ext/quotes.json?symbols='    
    ctr = 0
    req_lim = 400
    lim_increment = 400
    message = '\n'
    for ticker in ticker_list_condensed:
        if ctr == req_lim:
            try:
                r = auth.get(url)
                json_result = r.json()
                time.sleep(1)
                for quote in json_result['response']['quotes']['quote']:
                    if quote['wk52lo'] != '' and quote['wk52hi'] != '':
                        low = 0.0
                        high = 0.0
                        reward = 0.0
                        sym = quote['symbol']
                        if sym not in exclude_hilo:
                            ask = float(quote['ask'])
                            if ask >= .01:
                                low = round(float(quote['wk52lo']), 4)
                                high = round(float(quote['wk52hi']), 4)
                                if low != 0 and high != 0:
                                    reward = ((high - low) / low) * 100
                            if low == 0:
                                low = .001
                            rate_from_low = (ask - low) / low
                            rate_from_high = (high - ask) / high
                            approach_low = (rate_from_low < rate_lim and low != 0 and rate_from_low != -1)
                            approach_high = (rate_from_high < rate_lim and high != 0 and rate_from_high != -1)
                            if approach_low:
                                message = '\n\n' + 'Bought ' + sym + ' at ' + str(ask) + '\n' \
                                        + str(round(rate_from_low, 4) * 100) + '% from 52 week low\nReward: ' + str(reward) + '%'
                                sendEmail(message)
                                spent += float(quote['ask'])
                                exclude_hilo.append(sym)
                                bought[ticker] = ask
                            if approach_high:
                                message = '\n\n' + 'Bought ' + sym + ' at ' + str(ask) + '\n' \
                                        + str(round(rate_from_high, 4) * 100) + '% from 52 week high\n'
                                sendEmail(message)
                                spent += float(quote['ask'])
                                exclude_hilo.append(sym)
                                bought[ticker] = ask
                req_lim += lim_increment 
                url = 'https://api.tradeking.com/v1/market/ext/quotes.json?symbols='
            except Exception as e:
                print(e)
            ctr += 1
            continue
        if ctr == req_lim - lim_increment:
            url += ticker
        else:
            url += ',' + ticker
        ctr += 1
    try: 
        r = auth.get(url)
        json_result = r.json()
        time.sleep(1)
        for quote in json_result['response']['quotes']['quote']:
            if quote['wk52lo'] != '' and quote['wk52hi'] != '':
                low = 0.0
                high = 0.0
                reward = 0.0
                sym = quote['symbol']
                if sym not in exclude_hilo:
                    ask = float(quote['ask'])
                    if ask >= .01:
                        low = round(float(quote['wk52lo']), 4)
                        high = round(float(quote['wk52hi']), 4)
                        if low != 0 and high != 0:
                            reward = ((high - low) / low) * 100
                    if low == 0:
                        low = .001
                    rate_from_low = (ask - low) / low
                    rate_from_high = (high - ask) / high
                    approach_low = (rate_from_low < rate_lim and low != 0 and rate_from_low != -1)
                    approach_high = (rate_from_high < rate_lim and high != 0 and rate_from_high != -1)
                    if approach_low:
                        message = '\n\n' + 'Buy ' + sym + ' at ' + str(ask) + '\n' \
                                + str(round(rate_from_low, 4) * 100) + '% from 52 week low\nReward: ' + str(reward) + '%'
                        spent += float(quote['ask'])
                        exclude_hilo.append(sym)
                        bought[ticker] = ask
                    if approach_high:
                        message = '\n\n' + 'Buy ' + sym + ' at ' + str(ask) + '\n' \
                                + str(round(rate_from_high, 4) * 100) + '% from 52 week high\n'
                        spent += float(quote['ask'])
                        exclude_hilo.append(sym)
                        bought[ticker] = ask
    except Exception as e:
        print(e)

def sendEmail(message):
    if len(message) > 10:
        try:
            msg = EmailMessage()
            msg['Subject'] = 'Ally Investor'
            msg['From'] = cfg.email['sender']
            msg['To'] = ', '.join(cfg.email['receiver'])
            msg.set_content(message)
            smtp_server = "smtp.gmail.com"
            port = 587
            sender = cfg.email['sender']
            password = cfg.email['password']
            server = smtplib.SMTP(smtp_server, port)
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        except Exception as e:
            print(e)

running = False
while not running:
    try:
        auth = OAuth1Session(
            cfg.key['consumer_key'],
            cfg.key['consumer_secret'],
            cfg.key['oauth_token'],
            cfg.key['oauth_token_secret'])
        running = True
    except Exception as e:
        print(e)
while running:
    # begin cycle
    time.sleep(1)
    try:
        auth = OAuth1Session(
            cfg.key['consumer_key'],
            cfg.key['consumer_secret'],
            cfg.key['oauth_token'],
            cfg.key['oauth_token_secret'])
        res = auth.get(marketClockUrl)
        time.sleep(1)
        clockJson = res.json()['response']['status']['current']
    except Exception as e:
        print(e)
    try:
        ticker_list = []
        company_list = open(cfg.file['company_list']) 
        for line in company_list:
            if line == 'Symbol,Name,Last Sale,Net Change,% Change,Market Cap,Country,IPO Year,Volume,Sector,Industry':
                continue
            ticker = line.split(',')[0]
            if len(ticker) <= 4:
                ticker_list.append(ticker)
    except Exception as e:
        print(e)
    
    if clockJson == 'close' and datetime.now().hour >= 17:
        running = False
        print('close cycle done')

    if clockJson == 'pre':
        try:
            readFromMasIfEmpty()
            checkGains()
        except Exception as e:
            print(e)
        print('pre cycle done')

    if clockJson == 'open':
        try: 
            if not bought_gainers:
                buy_all_gainers()
                bought_gainers = True
            fillCondensed()
            readFromMasIfEmpty()
            checkToSell()
            gainers_thread = threading.Thread(target=checkGains)
            hi_lo_thread = threading.Thread(target=checkHiLo)
            gainers_thread.start()
            hi_lo_thread.start()
            gainers_thread.join()
            hi_lo_thread.join()
        except Exception as e:
            print(e)
        print('open cycle done')

# finished running for the day      
sendEmail('Program has finished running for the day. \n Profit: ' + str(profit) + '\nSpent: ' + str(spent) + '\nProfit Percentage: ' + str(float(profit) / float(spent)))
print("complete") 