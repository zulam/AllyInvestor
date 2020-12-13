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
exclude_sold = []
marketClockUrl = 'https://api.tradeking.com/v1/market/clock.json'
rate_lim = .05
price_max = 5
price_min = .001
sellTop = .25
sellBottom = -.05
sym_ign = ['FNCL', 'GLD', 'IEFA', 'ILTB' , 'PICK', 'SCHD', 'SCHH', 'VGT', 'VIG', 'VOOV', 'XBI']
watchlist_id = 'WATCHLIST'
acct_val = 1000
max_invest = acct_val / 20

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
        sendEmail(message)
    except Exception as e:
        print(e)

def createWatchlist():
    try:
        url = 'https://api.tradeking.com/v1/watchlists.json'
        body = {'id': watchlist_id}
        auth.post(url, body)
        time.sleep(1)
    except Exception as e:
        print(e)

def addToWatchlist(ticker):
    try:
        url = 'https://api.tradeking.com/v1/watchlists/' + watchlist_id + '/symbols.json'
        body = {'symbols': ticker}
        auth.post(url, body)
        time.sleep(1)
    except Exception as e:
        print(e)

def deleteWatchlist():
    try:
        url = 'https://api.tradeking.com/v1/watchlists/' + watchlist_id + '.json'
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
        sendEmail(message)
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
        sendEmail(message)
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
                if (rate >= sellTop or rate <= sellBottom):
                    message += '\n\n' + 'Sell ' + key + ' for ' + str(value[0]) + ' (' \
                            + str(round(rate, 4) * 100) + '% from bought)'
                    sell(key, qty[key], round(float(last_price[key].replace('$','').replace(',','')) * .95, 2))
                    exclude_sold.append(key)
        sendEmail(message)
    except Exception as e:
        print(e)
    
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
                ctr += 1
                continue
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
                    message += '\n\n' + article['date'] + ': ' + article['headline'] 
                    exclude_news.append(article['headline'])
        sendEmail(message)
    except Exception as e:
        print(e)

def checkEarlyGainers():
    message = '\n'
    url = 'https://api.tradeking.com/v1/market/ext/quotes.json?symbols='    
    ctr = 0
    req_lim = 100
    gain_check = .04
    for ticker in ticker_list_condensed:
        if ctr == req_lim:
            try:
                r = auth.get(url)
                json_result = r.json()
                time.sleep(1)
                for quote in json_result['response']['quotes']['quote']:
                    percent_change = (float(quote['ask']) - float(quote['opn']) / float(quote['opn']))
                    sym = quote['symbol']
                    if sym not in exclude_gains:
                        if percent_change >= gain_check:
                            message += '\n\n' + 'Watch ' + sym + ' at ' + str(quote['ask']) + '\n' \
                                        + str(round(float(percent_change), 4) * 100) + '% gain since open'
                            addToWatchlist(sym)
                            exclude_gains.append(sym)
                req_lim += 100 
                url = 'https://api.tradeking.com/v1/market/ext/quotes.json?symbols='   
            except Exception as e:
                print(e)
            ctr += 1
            continue   
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
            percent_change = (float(quote['ask']) - float(quote['opn']) / float(quote['opn']))
            sym = quote['symbol']
            if sym not in exclude_gains:
                if percent_change >= gain_check:
                    message += '\n\n' + 'Watch ' + sym + ' at ' + str(quote['ask']) + '\n' \
                                + str(round(float(percent_change), 4) * 100) + '% gain since open'
                    addToWatchlist(sym)
                    exclude_gains.append(sym)
        sendEmail(message)            
    except Exception as e:
        print(e)

def checkGains():
    message = '\n'
    url = 'https://api.tradeking.com/v1/market/ext/quotes.json?symbols='    
    ctr = 0
    req_lim = 100
    gain_check = .5
    vol_check = 1
    for ticker in ticker_list_condensed:
        if ctr == req_lim:
            try:
                r = auth.get(url)
                json_result = r.json()
                time.sleep(1)
                for quote in json_result['response']['quotes']['quote']:
                    percent_change = (float(quote['ask']) - float(quote['cl']) / float(quote['cl']))
                    vol = float(quote['vl'])
                    avg_vol = float(quote['adv_30'])
                    vol_chg = (vol - avg_vol) / avg_vol
                    sym = quote['symbol']
                    if sym not in exclude_gains:
                        if (percent_change >= gain_check or percent_change <= -gain_check) and vol_chg >= vol_check:
                            message += '\n\n' + 'Watch ' + sym + ' at ' + str(quote['ask']) + '\n' \
                                        + str(round(float(percent_change), 4) * 100) + '% gain since close \nVolume up ' \
                                        + str(round(float(vol_chg), 4) * 100) + '% from 30 day avg'
                            addToWatchlist(sym)
                            exclude_gains.append(sym)
                req_lim += 100 
                url = 'https://api.tradeking.com/v1/market/ext/quotes.json?symbols='   
            except Exception as e:
                print(e)
            ctr += 1
            continue   
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
            percent_change = (float(quote['ask']) - float(quote['cl']) / float(quote['cl']))
            vol = float(quote['vl'])
            avg_vol = float(quote['adv_30'])
            vol_chg = (vol - avg_vol) / avg_vol
            sym = quote['symbol']
            if sym not in exclude_gains:
                if (percent_change >= gain_check or percent_change <= -gain_check) and vol_chg >= vol_check:
                    message += '\n\n' + 'Watch ' + sym + ' at ' + str(quote['ask']) + '\n' \
                                + str(round(float(percent_change), 4) * 100) + '% gain since close \nVolume up ' \
                                + str(round(float(vol_chg), 4) * 100) + '% from 30 day avg'
                    addToWatchlist(sym)
                    exclude_gains.append(sym)
        sendEmail(message)            
    except Exception as e:
        print(e)

def checkHiLo():
    url = 'https://api.tradeking.com/v1/market/ext/quotes.json?symbols='    
    ctr = 0
    req_lim = 100
    message = '\n'
    for ticker in ticker_list_condensed:
        if ctr == req_lim:
            try:
                r = auth.get(url)
                json_result = r.json()
                time.sleep(1)
                for quote in json_result['response']['quotes']['quote']:
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
                            message += '\n\n' + 'Buy ' + sym + ' at ' + str(ask) + '\n' \
                                    + str(round(rate_from_low, 4) * 100) + '% from 52 week low\nReward: ' + str(reward) + '%'
                            # if checkToBuy():
                            #     shares_to_buy = round(max_invest / ask)
                            #     buy(sym, shares_to_buy, ask)
                            addToWatchlist(sym)
                            exclude_hilo.append(sym)
                req_lim += 100 
                url = 'https://api.tradeking.com/v1/market/ext/quotes.json?symbols='
            except Exception as e:
                print(e)
            ctr += 1
            continue
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
                    message += '\n\n' + 'Buy ' + sym + ' at ' + str(ask) + '\n' \
                            + str(round(rate_from_low, 4) * 100) + '% from 52 week low\nReward: ' + str(reward) + '%'
                    # if checkToBuy():
                    #     shares_to_buy = round(max_invest / ask)
                    #     buy(sym, shares_to_buy, ask)
                    addToWatchlist(sym)
                    exclude_hilo.append(sym)
        sendEmail(message)            
    except Exception as e:
        print(e)

def sendEmail(message):
    if len(message) > 10:
        if datetime.now().hour >= 6 and datetime.now().hour <= 22:
            try:
                smtp_server = "smtp.gmail.com"
                port = 587
                sender = cfg.email['sender']
                receiver = cfg.email['receivers']
                password = cfg.email['password']
                server = smtplib.SMTP(smtp_server, port)
                server.starttls()
                server.login(sender, password)
                server.sendmail(sender, receiver, message)
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
        createWatchlist()
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
    if clockJson == 'close' and datetime.now().hour > 5 and datetime.now().hour < 18:
        try:
            fillCondensed()
            readFromMasIfEmpty()
            checkNews()
        except Exception as e:
            print(e)
        print('close cycle done')
    
    elif clockJson == 'close' and datetime.now().hour >= 18:
        running = False
        deleteWatchlist()
        print('close cycle done')

    # pre market, open, or after, check all
    if clockJson == 'pre' or clockJson == 'open' or clockJson == 'after':
        if clockJson == 'open' and datetime.now().hour == 9:
            try: 
                checkEarlyGainers()
            except Exception as e:
                print(e)
            print('early gainers cycle done')
        try: 
            checkToSell()
            readFromMasIfEmpty()
            checkGains()
            checkHiLo()
            checkNews()
        except Exception as e:
            print(e)
        print('pre / open cycle done')

# finished running for the day      
sendEmail('Program has finished running for the day.')  
print("complete") 