import requests

url = '/v1/market/ext/quotes.xml?symbols=aapl'
params = {'symbols':'AAPL'}

r = requests.get(url = url, params=params)
