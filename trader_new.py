from datetime import datetime
from datetime import date
from dateutil.relativedelta import relativedelta
from requests_oauthlib import OAuth1Session
import time
import smtplib
import config as cfg
import requests
import Stock
from datetime import datetime, timedelta
from dateutil.parser import parse

def checkNews(ticker):
    tod = datetime.now()
    d = timedelta(2)
    lim = tod - d
    newsCount = 0
    newsTarget = 2
    newsUrl = 'https://api.tradeking.com/v1/market/news/search.json?symbols='
    temp_news = newsUrl + ticker + '&maxhits=10'
    try:
        res = auth.get(temp_news)
        json_news = res.json()
        articles = json_news['response']['articles']
        for article in articles['article']:
            if parse(article['date']) >= lim:
                newsCount += 1
        if newsCount >= newsTarget:
            return True
        else: 
            return False
    except Exception as e:
        print(e) 

def sendEmail(message):
    if datetime.now().hour >= 8 and datetime.now().hour <= 20:
        try:
            smtp_server = "smtp.gmail.com"
            port = 587
            sender = cfg.email['sender']
            receiver = ", ".join(cfg.email['receivers'])
            password = cfg.email['password']
            server = smtplib.SMTP(smtp_server, port)
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, receiver, message)
        except Exception as e:
            print(e)

ticker_list_condensed = []
marketClockUrl = 'https://api.tradeking.com/v1/market/clock.json'
rate_lim = .05
while True:
    #clock
    time.sleep(1)
    auth = OAuth1Session(
        cfg.key['consumer_key'],
        cfg.key['consumer_secret'],
        cfg.key['oauth_token'],
        cfg.key['oauth_token_secret'])
    res = auth.get(marketClockUrl)
    clockJson = res.json()['response']['status']['current']
    # getting tickers
    if clockJson != 'pre':
        ticker_list = []
        stocks_bought = {}
        sym_ign = ['D', 'FNCL', 'GLD', 'IEFA', 'ILTB' , 'OKE', 'PICK', 'SCHD', 'SCHH', 'VGT', 'VIG', 'VOOV', 'XBI']
        tickerCtr = 0
        company_list = open(cfg.file['company_list']) 
        for line in company_list:
            if line == '"Symbol","Name","LastSale","MarketCap","IPOyear","Sector","industry","Summary Quote",\n':
                continue
            ticker_list.append(line.split(',')[0].replace('"', ''))
            tickerCtr += 1

    # initialize
    url = 'https://api.tradeking.com/v1/market/ext/quotes.json?symbols='
    ctr = 0
    price_max = 1
    price_min = .001
    try:
        auth = OAuth1Session(
            cfg.key['consumer_key'],
            cfg.key['consumer_secret'],
            cfg.key['oauth_token'],
            cfg.key['oauth_token_secret'])
    except Exception as error:
        print(error)
    
    # filter out expensive stocks only when market is closed
    if clockJson == 'close' and datetime.now().hour <= 5:
        ticker_list_condensed.clear()
        # penny_file = open(cfg.file['penny_list'])
        # for line in penny_file:
        #     ticker = line.strip()
        #     temp_url = url + ticker
        #     try:
        #         time.sleep(1)
        #         r = auth.get(temp_url)
        #         json_result = r.json()
        #         ask_str = json_result['response']['quotes']['quote']['adp_100']
        #         ask = float(ask_str) if ask_str != '' else 0
        #         if ask <= price_max and ask != 0 and ask >= price_min:
        #             ticker_list_condensed.append(line.strip())
        #             print(ticker)
        #             ctr += 1
        #     except Exception as error:
        #         print(error)
        for ticker in ticker_list:
            temp_url = url + ticker
            try:
                time.sleep(1)
                r = auth.get(temp_url)
                json_result = r.json()
                ask_str = json_result['response']['quotes']['quote']['adp_100']
                ask = float(ask_str) if ask_str != '' else 0
                if ask <= price_max and ask != 0 and ask >= price_min:
                    ticker_list_condensed.append(ticker)
                    print(ticker)
                    ctr += 1
            except Exception as error:
                print(error)
        f = open("tickers_" + str(datetime.now().month) + "-" + str(datetime.now().day) + "-" + str(datetime.now().year) + ".txt", "w")
        for ticker in ticker_list_condensed:
            f.write(ticker + '\n')
        f.close()
        
    # market has opened
    if clockJson == 'open':
        master_list = []
        try:
            auth = OAuth1Session(
                cfg.key['consumer_key'],
                cfg.key['consumer_secret'],
                cfg.key['oauth_token'],
                cfg.key['oauth_token_secret'])
            res = auth.get(marketClockUrl)
            mas_file = open(cfg.file['master_file'])
            for line in mas_file:
                master_list.append(line.strip())
            for ticker in master_list: #ticker_list_condensed:
                # select stocks to suggest
                low = 0.0
                hi = 0.0
                temp_url = url + ticker
                time.sleep(1)
                r = auth.get(temp_url)
                json_result = r.json()
                ask = float(json_result['response']['quotes']['quote']['ask'])
                if ask >= .01:
                    low = float(json_result['response']['quotes']['quote']['wk52lo'])
                    hi = float(json_result['response']['quotes']['quote']['wk52hi'])
                if low == 0:
                    low = .001
                rate_from_low = (ask - low) / low
                if rate_from_low < rate_lim and low != 0 and rate_from_low != -1:
                    # send email to buy stock
                    message = 'Buy ' + ticker + ' at ' + str(ask) + ' (' \
                            + str(round(rate_from_low, 4) * 100) + '% from 52 week low)'
                    stocks_bought[ticker] = ask
                    sendEmail(message)
                    master_list.remove(ticker)
                    continue
                if hi == 0:
                    continue
                rate_from_high = (hi - ask) / hi
                if rate_from_high < rate_lim and hi != 0 and rate_from_high != -1:
                    # send email to buy stock
                    message = 'Short ' + ticker + ' at ' + str(ask) + ' (' \
                            + str(round(rate_from_high, 4) * 100) + '% from 52 week high)'
                    stocks_bought[ticker] = ask
                    sendEmail(message)
                    master_list.remove(ticker)
        except Exception as error:
            print('ERROR: ', error)
    print('complete')