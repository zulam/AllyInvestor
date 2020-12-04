from dateutil.relativedelta import relativedelta
from datetime import date, datetime, timedelta
from requests_oauthlib import OAuth1Session
from dateutil.parser import parse
import config as cfg
import requests
import smtplib
import time

# initialize
email_queue = []
email_sent = []
ticker_list_condensed = []
exclude_news = []
exclude_gains = []
exclude_hilo = []
marketClockUrl = 'https://api.tradeking.com/v1/market/clock.json'
rate_lim = .05
running = True
price_max = 5
price_min = .001

def fillCondensed():
    if len(ticker_list_condensed) == 0:
        url = 'https://api.tradeking.com/v1/market/ext/quotes.json?symbols='    
        ctr = 0
        req_lim = 100
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
                    req_lim += 100 
                except Exception as e:
                    print(e)
            if ctr == req_lim - 100:
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

def checkNews():
    newsUrl = 'https://api.tradeking.com/v1/market/news/search.json?symbols='
    ctr = 0
    req_lim = 100
    tod = datetime.now()
    d = timedelta(1)
    lim = tod - d
    for ticker in ticker_list_condensed:
        if ctr == req_lim:
            try:
                res = auth.get(newsUrl)
                json_news = res.json()
                time.sleep(1)
                articles = json_news['response']['articles']
                for article in articles['article']:
                    if parse(article['date']) >= lim:
                        if article['headline'] not in exclude_news:
                            message = '\n'
                            message += article['date'] + ': ' + article['headline'] 
                            sendEmail(message)
                            exclude_news.append(article['headline'])
                req_lim += 100 
                newsUrl = 'https://api.tradeking.com/v1/market/news/search.json?symbols='
            except Exception as e:
                print(e)
        if ctr == req_lim - 100:
            newsUrl += ticker
        else:
            newsUrl += ',' + ticker
        ctr += 1  
    try:
        res = auth.get(newsUrl)
        json_news = res.json()
        time.sleep(1)
        articles = json_news['response']['articles']
        for article in articles['article']:
            if parse(article['date']) >= lim:
                if article['headline'] not in exclude_news:
                    message = '\n'
                    message += article['date'] + ': ' + article['headline'] 
                    sendEmail(message)
                    exclude_news.append(article['headline'])
    except Exception as e:
        print(e)

def checkGains():
    url = 'https://api.tradeking.com/v1/market/ext/quotes.json?symbols='    
    ctr = 0
    req_lim = 100
    for ticker in ticker_list_condensed:
        if ctr == req_lim:
            try:
                r = auth.get(url)
                json_result = r.json()
                time.sleep(1)
                for quote in json_result['response']['quotes']['quote']:
                    #percent_change = float(quote['pchg'])
                    percent_change = (float(quote['ask']) - float(quote['cl']) / float(quote['cl']))
                    sym = quote['symbol']
                    if sym not in exclude_gains:
                        if percent_change >= .5 or percent_change <= -.5:
                            message = '\n' + 'Watch ' + sym + ' at ' + str(quote['ask']) + ' (' \
                                        + str(round(float(percent_change), 4) * 100) + '% gain since last close)'
                            sendEmail(message)
                            exclude_gains.append(sym)
                req_lim += 100 
                url = 'https://api.tradeking.com/v1/market/ext/quotes.json?symbols='   
            except Exception as e:
                print(e)

        if ctr == req_lim - 100:
            url += ticker
        else:
            url += ',' + ticker
        ctr += 1
    try:
        r = auth.get(url)
        json_result = r.json()
        time.sleep(1)
        for quote in json_result['response']['quotes']['quote']:
            percent_change = float(quote['pchg'])
            sym = quote['symbol']
            if sym not in exclude_gains:
                if percent_change >= 50:
                    message = '\n' + 'Watch ' + sym + ' at ' + str(quote['ask']) + ' (' \
                                + str(round(float(quote['pchg']), 4)) + '% gain since last close)'
                    sendEmail(message)
                    exclude_gains.append(sym)
    except Exception as e:
        print(e)

def checkHiLo():
    url = 'https://api.tradeking.com/v1/market/ext/quotes.json?symbols='    
    ctr = 0
    req_lim = 100
    for ticker in ticker_list_condensed:
        if ctr == req_lim:
            try:
                r = auth.get(url)
                json_result = r.json()
                time.sleep(1)
                for quote in json_result['response']['quotes']['quote']:
                    low = 0.0
                    sym = quote['symbol']
                    if sym not in exclude_hilo:
                        ask = float(quote['ask'])
                        if ask >= .01:
                            low = float(quote['wk52lo'])
                        if low == 0:
                            low = .001
                        rate_from_low = (ask - low) / low
                        approach_low = (rate_from_low < rate_lim and low != 0 and rate_from_low != -1)
                        message = '\n'
                        if approach_low:
                            # send email to buy stock
                            message += '\n' + 'Buy ' + sym + ' at ' + str(ask) + ' (' \
                                + str(round(rate_from_low, 4) * 100) + '% from 52 week low)'
                            sendEmail(message)
                            exclude_hilo.append(sym)
                req_lim += 100 
                url = 'https://api.tradeking.com/v1/market/ext/quotes.json?symbols='
            except Exception as e:
                print(e)
        if ctr == req_lim - 100:
            url += ticker
        else:
            url += ',' + ticker
        ctr += 1
    try: 
        r = auth.get(url)
        json_result = r.json()
        time.sleep(1)
        for quote in json_result['response']['quotes']['quote']:
            low = 0.0
            sym = quote['symbol']
            if sym not in exclude_hilo:
                ask = float(quote['ask'])
                if ask >= .01:
                    low = float(quote['wk52lo'])
                if low == 0:
                    low = .001
                rate_from_low = (ask - low) / low
                approach_low = (rate_from_low < rate_lim and low != 0 and rate_from_low != -1)
                message = '\n'
                if approach_low:
                    # send email to buy stock
                    message += '\n' + 'Buy ' + sym + ' at ' + str(ask) + ' (' \
                        + str(round(rate_from_low, 4) * 100) + '% from 52 week low)'
                    sendEmail(message)
                    exclude_hilo.append(sym)
    except Exception as e:
        print(e)

def sendEmail(message):
    if datetime.now().hour >= 6 and datetime.now().hour <= 22:
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
    else:
        email_queue.append(message)

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

    # getting tickers
    try:
        if clockJson != 'pre':
            ticker_list = []
            sym_ign = ['D', 'FNCL', 'GLD', 'IEFA', 'ILTB' , 'OKE', 'PICK', 'SCHD', 'SCHH', 'VGT', 'VIG', 'VOOV', 'XBI']
            company_list = open(cfg.file['company_list']) 
            for line in company_list:
                if line == '"Symbol","Name","LastSale","MarketCap","IPOyear","Sector","industry","Summary Quote",\n':
                    continue
                ticker = line.split(',')[0].replace('"', '')
                if len(ticker) <= 4:
                    ticker_list.append(line.split(',')[0].replace('"', ''))
    except Exception as e:
        print(e)
    
    # late night close, filter out stocks and check news
    if clockJson == 'close' and datetime.now().hour <= 5:
        try:
            fillCondensed()
            checkNews()
        except Exception as e:
            print(e)
        print('close cycle done')

    # early morning close, ready to send emails
    elif clockJson == 'close' and datetime.now().hour > 5 and datetime.now().hour < 22:
        if len(email_queue) > 0:
            for email in email_queue:
                try:
                    sendEmail(email)
                    time.sleep(1)
                    email_queue.remove(email)
                except Exception as e:
                    print(e)
        try:
            fillCondensed()
            readFromMasIfEmpty()
            checkNews()
        except Exception as e:
            print(e)
        print('close cycle done')
    elif clockJson == 'close' and datetime.now().hour >= 22:
        running = False
        print('close cycle done')

    # pre market, open, or after, check all
    if clockJson == 'pre' or clockJson == 'open' or clockJson == 'after':
        try: 
            readFromMasIfEmpty()
            checkGains()
            checkHiLo()
            checkNews()
        except Exception as e:
            print(e)
        print('pre / open cycle done')

# finished running for the day        
print("complete") 