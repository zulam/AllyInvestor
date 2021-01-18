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
email_queue = []
email_sent = []
ticker_list_condensed = []
close_open_gainers = []
exclude_news = []
exclude_gains = []
exclude_hilo = []
exclude_sold = []
exclude_close_open = []
marketClockUrl = 'https://api.tradeking.com/v1/market/clock.json'
rate_lim = .05
price_max = 10
price_min = .001
sellTop = .25
sellBottom = -.05
sym_ign = ['FNCL', 'GLD', 'IEFA', 'ILTB' , 'PICK', 'SCHD', 'SCHH', 'VGT', 'VIG', 'VOOV', 'XBI']
early_gainers_watchlist = 'GAINERS'
low_watchlist = 'LOW'
acct_val = 1000
#max_invest = acct_val / 20

def begin() :
    owned_url = 'https://api.tradeking.com/v1/accounts/' + cfg.account + '/balances.json'
    try:
        request = auth.get(owned_url)
        profile = request.json()
        info = profile['response']
    except Exception as e:
        print(e)
    try:
        cash_avail = round(float(info['accountbalance']['money']['cashavailable']) - float(info['accountbalance']['money']['unsettledfunds']), 2)
        message = '\nProgram has begun.\nFunds available for trading: $' + str(cash_avail)
        message_public = '\nProgram has begun.'
        sendEmail(message, False)
        sendEmail(message_public, True)
    except Exception as e:
        print(e)

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

def createWatchlists():
    try:
        url = 'https://api.tradeking.com/v1/watchlists.json'
        body = {'id': low_watchlist}
        auth.post(url, body)
        time.sleep(1)
    except Exception as e:
        print(e)
    try:
        url = 'https://api.tradeking.com/v1/watchlists.json'
        body = {'id': early_gainers_watchlist}
        auth.post(url, body)
        time.sleep(1)
    except Exception as e:
        print(e)

def addToWatchlist(watchlistId, ticker):
    try:
        url = 'https://api.tradeking.com/v1/watchlists/' + watchlistId + '/symbols.json'
        body = {'symbols': ticker}
        auth.post(url, body)
        time.sleep(1)
    except Exception as e:
        print(e)

def deleteWatchlists():
    try:
        url = 'https://api.tradeking.com/v1/watchlists/' + low_watchlist + '.json'
        auth.delete(url)
        time.sleep(1)
    except Exception as e:
        print(e)
    try:
        url = 'https://api.tradeking.com/v1/watchlists/' + early_gainers_watchlist + '.json'
        auth.delete(url)
        time.sleep(1)
    except Exception as e:
        print(e)

def buy(ticker, quant, lim):
    try:
        message = '\n'
        url = 'https://api.tradeking.com/v1/accounts/' + cfg.account + '/orders.xml'
        body = '<FIXML xmlns=\"http://www.fixprotocol.org/FIXML-5-0-SP2\"><Order TmInForce="0" Typ="2" Side="1" Px=' + '\"' + str(lim) + '\"' + ' Acct=' + '\"' + cfg.account + '\"' \
        + '><Instrmt SecTyp="CS" Sym=' + '\"' + ticker + '\"' + '/><OrdQty Qty=' + '\"' + str(quant) + '\"' + '/></Order></FIXML>'
        resp = auth.post(url, body)
        if resp.status_code == 200:
            message += 'Buy order placed for ' + ticker + ' at ' + str(lim) 
        else:
            message += 'BUY ORDER FAILED FOR ' + ticker + ' at ' + str(lim)
        sendEmail(message, False)
        time.sleep(1)
    except Exception as e:
        print(e)

def checkToBuy():
    owned_url = 'https://api.tradeking.com/v1/accounts/' + cfg.account + '/balances.json'
    try:
        request = auth.get(owned_url)
        profile = request.json()
        info = profile['response']
    except Exception as e:
        print(e)
    try:
        unsettled = info['accountbalance']['money']['unsettledfunds']
        cash_avail = info['accountbalance']['money']['cashavailable']
        if float(unsettled) < (acct_val / 3) and float(cash_avail) >= (acct_val * .66):
            return True
        else: 
            return False
    except Exception as e:
        print(e)
        return False

def sell(ticker, quant, lim):
    try:
        message = '\n'
        url = 'https://api.tradeking.com/v1/accounts/' + cfg.account + '/orders.xml'
        body = '<FIXML xmlns=\"http://www.fixprotocol.org/FIXML-5-0-SP2\"><Order TmInForce="0" Typ="2" Side="2" Px=' + '\"' + str(lim) + '\"' + ' Acct=' + '\"' + cfg.account + '\"' \
        + '><Instrmt SecTyp="CS" Sym=' + '\"' + ticker + '\"' + '/><OrdQty Qty=' + '\"' + str(quant) + '\"' + '/></Order></FIXML>'
        resp = auth.post(url, body)
        if resp.status_code == 200:
            message += 'Sell order placed for ' + ticker + ' at ' + str(lim) 
        else:
            message += 'SELL ORDER FAILED FOR ' + ticker + ' at ' + str(lim)
        sendEmail(message, False)
        time.sleep(1)
    except Exception as e:
        print(e)

def checkToSell():
    message = '\n'
    owned_url = 'https://api.tradeking.com/v1/accounts.json'
    holdings = {}
    last_price = {}
    qty = {}
    stocks_owned = []
    try:
        request = auth.get(owned_url)
        profile = request.json()
        info = profile['response']['accounts']['accountsummary']
    except Exception as e:
        print(e)
    try:
        for item in info:
            if item['account'] == cfg.account:
                stocks_owned.append(item['accountholdings']['holding'])
                for holding in stocks_owned:
                    for item in holding: 
                        if item['displaydata']['symbol'] not in sym_ign:
                            holdings[item['displaydata']['symbol']] = (item['displaydata']['marketvalue'], item['displaydata']['costbasis'])
                            last_price[item['displaydata']['symbol']] = item['displaydata']['lastprice']
                            qty[item['displaydata']['symbol']] = item['displaydata']['qty']
    except Exception as e:
        print(e)
    try:   
        for key, value in holdings.items():
            if key not in exclude_sold:
                orig = float(value[1].replace('$','').replace(',',''))
                curr = float(value[0].replace('$','').replace(',',''))
                rate = (curr - orig) / orig
                if rate <= sellBottom:
                    message += '\n\n' + 'Sell ' + key + ' for ' + str(value[0]) + ' (' \
                            + str(round(rate, 4) * 100) + '% from bought)'
                    #sell(key, qty[key], round(float(last_price[key].replace('$','').replace(',','')) * .95, 2))
                    exclude_sold.append(key)
                if rate >= sellTop:
                    message += '\n\n' + 'Sell ' + key + ' for ' + str(value[0]) + ' (' \
                            + str(round(rate, 4) * 100) + '% from bought)'
                    exclude_sold.append(key)
        sendEmail(message, False)
    except Exception as e:
        print(e)

def checkNews():
    newsUrl = 'https://api.tradeking.com/v1/market/news/search.json?symbols='
    ctr = 0
    req_lim = 400
    lim_increment = 400
    tod = datetime.now()
    d = timedelta(hours = 8)
    lim = tod - d
    message = '\n'
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
                            message += '\n\n' + article['date'] + ': ' + article['headline'] 
                            #sendEmail(message, True)
                            exclude_news.append(article['headline'])
                req_lim += lim_increment 
                newsUrl = 'https://api.tradeking.com/v1/market/news/search.json?symbols='
            except Exception as e:
                print(e)
        if ctr == req_lim - lim_increment:
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
                    message += '\n\n' + article['date'] + ': ' + article['headline'] 
                    #sendEmail(message, True)
                    exclude_news.append(article['headline'])
        sendEmail(message, True)
    except Exception as e:
        print(e)

def checkEarlyGainers():
    message = '\n'
    url = 'https://api.tradeking.com/v1/market/ext/quotes.json?symbols='    
    ctr = 0
    req_lim = 400
    lim_increment = 400
    gain_check = .04
    for ticker in close_open_gainers:
        if ctr == req_lim:
            try:
                r = auth.get(url)
                json_result = r.json()
                time.sleep(1)
                for quote in json_result['response']['quotes']['quote']:
                    if quote['ask'] != '' and quote['opn'] != '':
                        if float(quote['opn']) != 0:
                            percent_change = (float(quote['ask']) - float(quote['opn'])) / float(quote['opn'])
                            sym = quote['symbol']
                            if sym not in exclude_close_open:
                                if percent_change >= gain_check:
                                    message = '\n\n' + 'BUY ' + sym + ' at ' + str(quote['ask']) + '\n' \
                                                + str(round(float(percent_change), 4) * 100) + '% gain since open after 9:30 spike'
                                    sendEmail(message, True) 
                                    addToWatchlist(early_gainers_watchlist, sym)
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
            if quote['ask'] != '' and quote['opn'] != '':
                if float(quote['opn']) != 0:
                    percent_change = (float(quote['ask']) - float(quote['opn'])) / float(quote['opn'])
                    sym = quote['symbol']
                    if sym not in exclude_close_open:
                        if percent_change >= gain_check:
                            message = '\n\n' + 'BUY ' + sym + ' at ' + str(quote['ask']) + '\n' \
                                        + str(round(float(percent_change), 4) * 100) + '% gain since open after 9:30 spike'
                            sendEmail(message, True) 
                            addToWatchlist(early_gainers_watchlist, sym)
                            exclude_close_open.append(sym)
        #sendEmail(message, True)            
    except Exception as e:
        print(e)

def checkGains():
    #message = '\n'
    url = 'https://api.tradeking.com/v1/market/ext/quotes.json?symbols='    
    ctr = 0
    req_lim = 400
    lim_increment = 400
    gain_check = .25
    #vol_check = 1
    for ticker in ticker_list_condensed:
        if ctr == req_lim:
            try:
                r = auth.get(url)
                json_result = r.json()
                time.sleep(1)
                for quote in json_result['response']['quotes']['quote']:
                    if quote['ask'] != '' and quote['cl'] != '':
                        percent_change = (float(quote['ask']) - float(quote['cl'])) / float(quote['cl'])
                        # vol = float(quote['vl'])
                        # avg_vol = float(quote['adv_30'])
                        #vol_chg = (vol - avg_vol) / avg_vol
                        sym = quote['symbol']
                        if sym not in exclude_gains:
                            if percent_change >= gain_check:
                                # message += '\n\n' + 'Watch ' + sym + ' at ' + str(quote['ask']) + '\n' \
                                #             + str(round(float(percent_change), 4) * 100) + '% gain since close \nVolume up ' \
                                #             + str(round(float(vol_chg), 4) * 100) + '% from 30 day avg'
                                # addToWatchlist(sym)
                                exclude_gains.append(sym)
                                close_open_gainers.append(sym)
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
                # vol = float(quote['vl'])
                # avg_vol = float(quote['adv_30'])
                #vol_chg = (vol - avg_vol) / avg_vol
                sym = quote['symbol']
                if sym not in exclude_gains:
                    if percent_change >= gain_check:
                        # message += '\n\n' + 'Watch ' + sym + ' at ' + str(quote['ask']) + '\n' \
                        #             + str(round(float(percent_change), 4) * 100) + '% gain since close \nVolume up ' \
                        #             + str(round(float(vol_chg), 4) * 100) + '% from 30 day avg'
                        # addToWatchlist(sym)
                        exclude_gains.append(sym)
                        close_open_gainers.append(sym)
        #sendEmail(message)            
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
                            approach_low = (rate_from_low < rate_lim and low != 0 and rate_from_low != -1)
                            if approach_low:
                                # send email to buy stock
                                message = '\n\n' + 'Buy ' + sym + ' at ' + str(ask) + '\n' \
                                        + str(round(rate_from_low, 4) * 100) + '% from 52 week low\nReward: ' + str(reward) + '%'
                                sendEmail(message, True)
                                # if checkToBuy():
                                #     shares_to_buy = round(max_invest / ask)
                                #     buy(sym, shares_to_buy, ask)
                                addToWatchlist(low_watchlist, sym)
                                exclude_hilo.append(sym)
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
                        low = float(quote['wk52lo'])
                        high = round(float(quote['wk52hi']), 4)
                        if low != 0 and high != 0:
                            reward = ((high - low) / low) * 100
                    if low == 0:
                        low = .001
                    rate_from_low = (ask - low) / low
                    approach_low = (rate_from_low < rate_lim and low != 0 and rate_from_low != -1)
                    if approach_low:
                        # send email to buy stock
                        message = '\n\n' + 'Buy ' + sym + ' at ' + str(ask) + '\n' \
                                + str(round(rate_from_low, 4) * 100) + '% from 52 week low\nReward: ' + str(reward) + '%'
                        sendEmail(message, True)
                        # if checkToBuy():
                        #     shares_to_buy = round(max_invest / ask)
                        #     buy(sym, shares_to_buy, ask)
                        addToWatchlist(low_watchlist, sym)
                        exclude_hilo.append(sym)
        #sendEmail(message, True)            
    except Exception as e:
        print(e)

def sendEmail(message, public):
    if len(message) > 10:
        if datetime.now().hour >= 6 and datetime.now().hour <= 22:
            try:
                msg = EmailMessage()
                msg['Subject'] = 'Ally Investor'
                msg['From'] = cfg.email['sender']
                if public:
                    msg['To'] = ', '.join(cfg.email['receivers'])
                else:
                    msg['To'] = cfg.email['receiver']
                msg.set_content(message)
                smtp_server = "smtp.gmail.com"
                port = 587
                sender = cfg.email['sender']
                password = cfg.email['password']
                server = smtplib.SMTP(smtp_server, port)
                server.starttls()
                server.login(sender, password)
                #server.sendmail(sender, receiver, message)
                server.send_message(msg)
            except Exception as e:
                print(e)
        else:
            email_queue.append(message)

running = False
while not running:
    try:
        auth = OAuth1Session(
            cfg.key['consumer_key'],
            cfg.key['consumer_secret'],
            cfg.key['oauth_token'],
            cfg.key['oauth_token_secret'])
        begin()
        createWatchlists()
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

    # getting tickers
    try:
        if clockJson != 'pre':
            ticker_list = []
            company_list = open(cfg.file['company_list']) 
            for line in company_list:
                if line == '"Symbol","Name","LastSale","MarketCap","IPOyear","Sector","industry","Summary Quote",\n':
                    continue
                ticker = line.split(',')[0].replace('"', '')
                if len(ticker) <= 4:
                    ticker_list.append(line.split(',')[0].replace('"', ''))
    except Exception as e:
        print(e)

    # early morning close, ready to send emails
    if clockJson == 'close' and datetime.now().hour > 5 and datetime.now().hour < 17:
        try:
            fillCondensed()
            readFromMasIfEmpty()
            checkNews()
        except Exception as e:
            print(e)
        print('close cycle done')
    
    elif clockJson == 'close' and datetime.now().hour >= 17:
        running = False
        deleteWatchlists()
        print('close cycle done')

    # pre market or after hours
    if clockJson == 'pre' or clockJson == 'after':
        try:
            readFromMasIfEmpty()
            checkNews()
        except Exception as e:
            print(e)
        print('pre cycle done')

    # open 
    if clockJson == 'open':
        try: 
            readFromMasIfEmpty()
            gainers_thread = threading.Thread(target=checkGains)
            news_thread = threading.Thread(target=checkNews)
            gainers_thread.start()
            news_thread.start()
            gainers_thread.join()
            checkEarlyGainers()
            news_thread.join()
        except Exception as e:
            print(e)
        print('open cycle done')

# finished running for the day      
sendEmail('Program has finished running for the day.', True)  
print("complete") 