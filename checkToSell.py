#check to sell (commented out - needs some work)
                    # owned_url = 'https://api.tradeking.com/v1/accounts.json'
                    # holdings = {}
                    # request = auth.get(owned_url)
                    # profile = request.json()
                    # info = profile['response']['accounts']['accountsummary']
                    # stocks_owned = []
                    # for item in info:
                    #     if item['account'] == cfg.key['account']:
                    #         stocks_owned.append(item['accountholdings']['holding'])
                    #         for holding in stocks_owned:
                    #             for item in holding: 
                    #                 if item['displaydata']['symbol'] not in sym_ign:
                    #                     holdings[item['displaydata']['symbol']] = (item['displaydata']['marketvalue'], item['displaydata']['costbasis'])
                    # for key, value in holdings.items():
                    #     rate = (value[0] - value[1]) / value[0]
                    #     if (rate >= sellTop or rate <= sellBottom):
                    #         #send email to sell stock
                    #         #stocks_bought.pop(key)
                    #         smtp_server = "smtp.gmail.com"
                    #         port = 587
                    #         sender = cfg.email['receiver']
                    #         receiver = cfg.email['receiver']
                    #         password = cfg.email['password']
                    #         message = 'Sell ' + key + ' at ' + str(value[0]) + ' (' \
                    #                 + str(round(rate, 4) * 100) + '% from bought)'
                    #         server = smtplib.SMTP(smtp_server, port)
                    #         server.starttls()
                    #         server.login(sender, password)
                    #         server.sendmail(sender, receiver, message)
                    #         ticker_list_condensed.append(key)
                    #         break