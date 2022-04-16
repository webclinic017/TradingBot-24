import alpaca_trade_api as tradeapi
import numpy as np
import time
from flask import Flask, render_template, jsonify
from flask_apscheduler import APScheduler
from datetime import datetime, timedelta
import pytz
import pandas as df
'''
    This is using Alpaca paper trading with fake money.
'''


SEC_KEY = 'rPG3gW1B6vimk2c1I0uHjP9c2HitnhrRHENSTo5W'
PUB_KEY = 'PKISWKG08XNPGJMT730Q'
BASE_URL = 'https://paper-api.alpaca.markets'
api = tradeapi.REST(key_id= PUB_KEY, secret_key=SEC_KEY, base_url=BASE_URL)

class Config:
    SCHEDULER_API_ENABLED = True

app = Flask(__name__)
app.config.from_object(Config())
app.config['JSON_SORT_KEYS'] = False
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

UTC = pytz.timezone('UTC')
def get_data():
    # Returns a an numpy array of the closing prices of the past 5 minutes
    time_now = datetime.now(tz=UTC)
    time_5_mins = time_now - timedelta(minutes=6)
    bar_iter = api.get_bars_iter(symb, tradeapi.TimeFrame.Minute, time_5_mins.isoformat(), time_now.isoformat(),limit = 5)
    close_list = []
    for bar in bar_iter:
        close_list.append(bar.c)
    
    close_list = np.array(close_list, dtype=np.float64)

    return close_list

def buy(q, s): # Returns nothing, makes call to buy stock
    api.submit_order(
        symbol=s,
        qty=q,
        side='buy',
        type='market',
        time_in_force='gtc'
    )
def sell(q, s): # Returns nothing, makes call to sell stock
    api.submit_order(
        symbol=s,
        qty=q,
        side='sell',
        type='market',
        time_in_force='gtc'
    )

symb = "TSLA" # Ticker of stock you want to trade
pos_held = False
count = 0
 # buy(1, symb)
@scheduler.task('interval', id='trading', seconds=60)
def trading():
    global pos_held, symb, count
    print("")
    t = time.localtime()
    count = count + 1
    current_time = time.strftime("%H:%M:%S", t)
    print("Checking Price at " + current_time + "count @ " + str(count))
    
    close_list = get_data()

    ma = np.mean(close_list)
    ma8 = np.SMA(close_list, 8) # moving average 8
    ma20 = np.SMA(close_list, 20) # moving average 20
    
    ma8b4 = np.SMA(close_list, 8) [-1] # moving average 8 one bar before
    ma20b4 = np.SMA(close_list, 20) [-1] # moving average 20 one bar before
    # print(len(close_list))
    last_price = close_list[-1]

    print("Moving Average: " + str(ma))
    print("Last Price: " + str(last_price))

    # Make buy/sell decision
    # This algorithm buys or sells when the moving average crosses the most recent closing price 
'''
    if ma + 0.2 < last_price and not pos_held: # Buy when moving average is ten cents below the last price
        print("Buy")
        buy(1, symb)
        pos_held = True
    
    elif ma - 0.2 > last_price and pos_held: # Sell when moving average is ten cents above the last price
        print("Sell")
        sell(1, symb)
        pos_held = False
'''    
    if ma8 > ma20 and ma8b4 < ma20b4: #if ma8 crossed ma20 and is now above = buy
        print("Buy")
        buy(1, symb)
        pos_held = True
    elif ma8 < ma20 and ma8b4 > ma20b4: #if ma8 crosses again but now is below = sell
        print("Sell")
        sell(1, symb)
        pos_held = False

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/buying_power')
def buyingpower():
    account = api.get_account()
    return account.buying_power

@app.route('/api/current_balance')
def currentbalance():
    account = api.get_account()
    return account.portfolio_value

@app.route('/api/gain')
def calculateGain():
    account = api.get_account()
    balance_change = float(account.equity) - float(account.last_equity)
    # print(f'{account.equity} {account.last_equity}')
    balance_change = balance_change / float(account.equity) * 100
    return "%" +str(round(balance_change,3))

@app.route('/api/cash')
def cash():
    account = api.get_account()
    return account.cash

@app.route('/api/portfolio')
def portfolio():
    portfolio = api.list_positions()
    json = {}
    cash = api.get_account()
    json['cash'] = float(cash.cash)
    for position in portfolio:
        json[position.symbol] = float(position.current_price) * float(position.qty)
    return json

@app.route('/api/history')
def porthistory():
    history = api.get_portfolio_history()
    json = {}
    count = 0
    for time in history.timestamp:
        date = datetime.fromtimestamp(time).strftime("%B %d, %Y %I:%M:%S")
        json[date] = history.equity[count]
        count += 1
    return json

@app.route('/api/orders')
def orders():
    acts = api.get_activities(page_size=10)
    activities = []
    for transaction in acts:
        order = []
        order.append(transaction.symbol)
        order.append(transaction.side)
        order.append(transaction.qty)
        order.append(transaction.price)
        order.append(transaction.transaction_time)
        order.append(transaction.order_status)
        activities.append(order)
    return jsonify(activities)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080,use_reloader=False)