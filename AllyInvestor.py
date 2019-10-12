import time
from datetime import datetime
from requests_oauthlib import OAuth1Session
import smtplib
import config as cfg

# getting tickers
ticker_list = []
ticker_list_condensed = []
company_file = open(cfg.file['company_list'])
for line in company_file:
    ticker_list.append(line.split('|')[0])

# initialize
url = 'https://api.tradeking.com/v1/market/ext/quotes.json?symbols='
ctr = 0
lim = 100
price_max = 1.0
var = .05
auth = OAuth1Session(
    cfg.key['consumer_key'],
    cfg.key['consumer_secret'],
    cfg.key['oauth_token'],
    cfg.key['oauth_token_secret'])

# filter out expensive stocks
for ticker in ticker_list:
    temp_url = url + ticker
    try:
        # uncomment this portion for debugging
        # if ctr == lim:
        #     break
        time.sleep(1)
        r = auth.get(temp_url)
        json_result = r.json()
        ask = float(json_result['response']['quotes']['quote']['ask'])
        if ask <= price_max and ask != 0:
            ticker_list_condensed.append(ticker)
            print(ticker)
            # ctr += 1
    except Exception as error:
        print(error)

# empty loop until market opens
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
            if rate_from_low < var:
                # send email to buy stock
                smtp_server = "smtp.gmail.com"
                port = 587
                sender = cfg.email['sender']
                receiver = cfg.email['receiver']
                password = cfg.email['sender_password']
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

# complete
print('complete')
