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
    d = timedelta(14)
    lim = tod - d
    newsCount = 0
    newsTarget = 4
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
        smtp_server = "smtp.gmail.com"
        port = 587
        sender = cfg.email['sender']
        receiver = ", ".join(cfg.email['receivers'])
        password = cfg.email['password']
        server = smtplib.SMTP(smtp_server, port)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver, message)

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
    ticker_list = []
    penny_list = []
    
    stocks_bought = {}
    sym_ign = ['D', 'FNCL', 'GLD', 'IEFA', 'ILTB' , 'OKE', 'PICK', 'SCHD', 'SCHH', 'VGT', 'VIG', 'VOOV', 'XBI']
    company_file = open(cfg.file['company_list']) 
    penny_file = open(cfg.file['penny_list'])
    tickerCtr = 0
    for line in company_file:
        if line == '"Symbol","Name","LastSale","MarketCap","IPOyear","Sector","industry","Summary Quote",\n':
            continue
        # if tickerCtr == 100:
        #   break
        ticker_list.append(line.split(',')[0].replace('"', ''))
        tickerCtr += 1
    for line in penny_file:
        penny_list.append(line.strip())

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
    if clockJson == 'pre' or clockJson == 'close': # or clockJson == 'open':
        ticker_list_condensed.clear()
        for ticker in ticker_list:
            if ticker not in sym_ign:
                temp_url = url + ticker
                try:
                    time.sleep(1)
                    r = auth.get(temp_url)
                    json_result = r.json()
                    ask_str = json_result['response']['quotes']['quote']['ask']
                    ask = float(ask_str) if ask_str != '' else 0
                    if ask <= price_max and ask != 0 and ask >= price_min:
                        ticker_list_condensed.append(ticker)
                        print(ticker)
                        ctr += 1
                except Exception as error:
                    print(error)
    # pumps
    # newsCtr = 0
    # pumps = []
    # for ticker in penny_list: #ticker_list_condensed:
    #     newsBool = checkNews(ticker)
    #     if (newsBool):
    #         pumps.append(ticker)
    #         newsCtr += 1
    #         print('Potential pump and dumps: ' + str(newsCtr))
    #     time.sleep(1)
    # try:
    #     print('Potential pump and dumps: ' + str(newsCtr))
    #     message = ''
    #     for item in pumps:
    #         message += item + ' \n'
    #     sendEmail(message)
    # except Exception as e:
    #     print(e)

    # market has opened
    if clockJson == 'open':
        try:
            auth = OAuth1Session(
                cfg.key['consumer_key'],
                cfg.key['consumer_secret'],
                cfg.key['oauth_token'],
                cfg.key['oauth_token_secret'])
            res = auth.get(marketClockUrl)
            clockJson = res.json()
            for ticker in penny_list: #ticker_list_condensed:
                # select stocks to suggest
                temp_url = url + ticker
                try:
                    # checkNews(ticker)
                    time.sleep(1)
                    r = auth.get(temp_url)
                    json_result = r.json()
                    ask = float(json_result['response']['quotes']['quote']['ask'])
                    low = float(json_result['response']['quotes']['quote']['wk52lo'])
                    if low == 0:
                        low = .001
                    rate_from_low = (ask - low) / low
                    if rate_from_low < rate_lim and low != 0 and rate_from_low != -1:
                        # send email to buy stock
                        message = 'Buy ' + ticker + ' at ' + str(ask) + ' (' \
                                + str(round(rate_from_low, 4) * 100) + '% from 52 week low)'
                        stocks_bought[ticker] = ask
                        sendEmail(message)
                        #ticker_list_condensed.remove(ticker)
                        penny_list.remove(ticker)
                except Exception as error:
                    print('ERROR: ', error)
        except Exception as error:
            print('ERROR: ', error)
        print('complete')