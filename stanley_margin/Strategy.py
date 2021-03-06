import poloniexAPI
import time
import sys


# region ### Methods
def calc_margin_alt(price, symbol):
    current_balance = poloniexAPI.polo.returnTradableBalances()  # make it more flexible...
    coin =  symbol.replace("BTC_", "")
    coin_balance = float(current_balance[symbol][coin])
    relative_balance = coin_balance*0.95  # 95% of current balance for buffer
    print("My malt margin balance = %s at price %f" % (relative_balance, price))

    amount = relative_balance
    return amount


# region ### Methods
def calc_margin_btc(price, symbol):
    balance = poloniexAPI.polo.returnTradableBalances()
    coin_balance = float(balance[symbol]["BTC"])
    relative_balance = coin_balance*0.95  # 2= 50% of current balance
    print("My mbtc margin balance = %f at price %f" % (relative_balance, price))

    amount = relative_balance / price
    return amount



def buy_margin(ask, symbol):
    amount = calc_margin_btc(ask, symbol)
    value = float(amount) * ask
    factor = 0.20  # percentage of total margin avaliable to use on this trade
    print("Buy %s amount = %s at price %f, value %f" % (symbol, amount, ask, value))

    if value > 0.02:  # enough margin to place a trade
        if value * factor > 0.02:  # trade a fraction of available funds
            amount = amount * factor
            res = poloniexAPI.polo.marginBuy(symbol, ask, amount, lendingRate=0.02)  # if you want margin trade
            print("Res %s at price %f" % (res, ask))
            ret = 'success'
        else:  # trade with remaining margin available > 0.02 btc
            res = poloniexAPI.polo.marginBuy(symbol, ask, amount, lendingRate=0.02)  # if you want margin trade
            print("Res %s at price %f" % (res, ask))
            ret = 'success'
    elif value < 0.02:
        print("Res %s not enough margin: %f" % (symbol, value))
        ret = 'no_margin'

    #if res != 'success':
    #    raise BaseException('### Trade Buy error')
    return ret


def sell_margin(bid, symbol):

    amount = calc_margin_alt(bid, symbol)
    value = float(amount) * bid
    factor = 0.2
    print("Sell %s amount = %s at price %f, value %f" % (symbol, amount, bid, value))

    if value > 0.02:
        if value * factor > 0.02:
            amount = amount * factor
            res = poloniexAPI.polo.marginSell(symbol, bid, amount, lendingRate=0.02)  # if you want margin trade
            print("Res %s at price %f" % (res, bid))
            ret = 'success'
        else:
            res = poloniexAPI.polo.marginSell(symbol, bid, amount, lendingRate=0.02)  # if you want margin trade
            print("Res %s at price %f" % (res, bid))
            ret = 'success'
    elif value < 0.02:
        print("Res %s not enough margin: %f" % (symbol, value))
        ret = 'no_margin'
     # fix it when uncomment!
    #if res != 'success':
    #    raise BaseException('### Trade Sell error')
    return ret

def exit_buy_margin(ask, symbol):
    res = poloniexAPI.polo.closeMarginPosition(currencyPair=symbol)  # close margin trade

    print("Res %s at price %f" % (res, ask))
    return res

def exit_sell_margin(bid, symbol):
    res = poloniexAPI.polo.closeMarginPosition(currencyPair=symbol)  # close margin trade
    print("Res %s at price %f" % (res, bid))

    return res


class Strategy:
    is_buy_open = False
    is_sell_open = False
    SYMBOL = None
    ticket = -1
    confirm = 4
    initiate = 0

    def __init__(self, symbol):
        self.SYMBOL = symbol
        self.ticket = 0
        self.confirm = 4
        self.initiate = 0
    def crossover_strategy(self, time_period, fast_period, mid_period, slow_period):
        try:
            fast_ma = poloniexAPI.get_ma(self.SYMBOL, timeframe=time_period, period=fast_period)
            time.sleep(0.2)  # safe
            slow_ma = poloniexAPI.get_ma(self.SYMBOL, timeframe=time_period, period=slow_period)
            time.sleep(0.2)  # safe
            mid_ma = poloniexAPI.get_ma(self.SYMBOL, timeframe=time_period, period=mid_period)
            time.sleep(0.2)  # safe

            current_btc = poloniexAPI.get_btc_balance(self.SYMBOL)
            time.sleep(0.2)  # safe
            current_alt = poloniexAPI.get_margin_balance(self.SYMBOL)
            time.sleep(0.2)  # safe
            last_price = poloniexAPI.get_orderbook(self.SYMBOL)
            alt_converted = float(current_alt)  * float(last_price['bids'][0][0])
            ask = float(last_price['asks'][0][0])*1.005
            bid = float(last_price['bids'][0][0])*0.995
            current_margin = poloniexAPI.get_current_margin()

            margin_type = poloniexAPI.get_margin_type(self.SYMBOL)
            time.sleep(0.2)  # safe
            if margin_type == "short":
                self.is_buy_open = False
                self.is_sell_open = True
            elif margin_type == "long":
                self.is_buy_open = True
                self.is_sell_open = False
            elif margin_type == "none":
                self.is_buy_open = False
                self.is_sell_open = False

            print("%s alt_converted %f at current_btc %f" % (self.SYMBOL, alt_converted, current_btc))
            print("%s ask %f at bid %f" % (self.SYMBOL, ask, bid))
            print("%s confirm %.0f at ticket %.0f" % (self.SYMBOL, self.confirm, self.ticket))
            print("%s sell open %.0f buy open %.0f" % (self.SYMBOL, self.is_sell_open, self.is_buy_open))
            print("%s slow_ma %f mid_ma %f fast_ma %f" % (self.SYMBOL, slow_ma, mid_ma,fast_ma ))


            if self.is_buy_open:
                if current_margin > 0.44:
                    if  fast_ma > slow_ma:
                        if fast_ma > mid_ma:
                            if self.ticket < self.confirm:
                                self.ticket = self.ticket + 1
                            else:
                                if buy_margin(ask, self.SYMBOL) == "success":
                                    self.ticket = 0
                        else:
                            self.ticket = 0
                    elif  fast_ma < mid_ma:
                        exit_buy_margin(ask, self.SYMBOL)
                        self.ticket = 0
                    elif  fast_ma < slow_ma:
                        exit_buy_margin(ask, self.SYMBOL)
                        self.ticket = 0
                else:
                    if  fast_ma < mid_ma:
                        exit_buy_margin(ask, self.SYMBOL)
                        self.ticket = 0

            elif self.is_sell_open:
                if current_margin > 0.44:
                    if  fast_ma < slow_ma:
                        if fast_ma < mid_ma:
                            if self.ticket < self.confirm:
                                self.ticket = self.ticket + 1
                            else:
                                if sell_margin(bid, self.SYMBOL) == "success":
                                    self.ticket = 0
                        else:
                            self.ticket = 0
                    elif  fast_ma > mid_ma:
                        try:
                            exit_sell_margin(bid, self.SYMBOL)
                            self.ticket = 0
                        except:
                            self.ticket = 0
                    elif  fast_ma > slow_ma:
                        exit_sell_margin(bid, self.SYMBOL)
                        self.ticket = 0
                else:
                    if  fast_ma > mid_ma:
                        exit_sell_margin(bid, self.SYMBOL)
                        self.ticket = 0


            elif self.is_sell_open is False and self.is_buy_open is False :
                if current_margin > 0.42:
                    if  fast_ma < slow_ma:
                        if self.ticket < self.confirm:
                            self.ticket = self.ticket + 2
                        else:
                            if sell_margin(bid, self.SYMBOL) == "success":
                                self.ticket = 0
                    if  fast_ma > slow_ma:
                        if self.ticket < self.confirm:
                            self.ticket = self.ticket + 2
                        else:
                            if buy_margin(ask, self.SYMBOL) == "success":
                                self.ticket = 0

        except:
            self.ticket = 0

        #    def supertrend_strategy(self, fast_period, slow_period):
