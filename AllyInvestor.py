import requests

ticker_list = []
company_file = open('nasdaqlisted.txt')
for line in company_file:
    ticker_list.append(line.strip('\n'))
    
print("ay")
# url = '/v1/market/ext/quotes.xml?symbols=aapl'
# params = {'symbols':'AAPL'}
# r = requests.get(url = url, params=params)
# print('success')
