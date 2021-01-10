import datetime

import numpy as np
import pandas as pd
import statsmodels.api as sm

from strategy import Strategy
from event import SignalEvent
from backtest import Backtest
from data import HistoricMinDataHandler
from execution import SimulatedExecutionHandler
from portfolio import Portfolio

class MovingAverageCrossStrategy(Strategy):
    """
    Carries out basic moving average strategy with a short/long simple weighted moving average.
    Default short/long window are 100/400 periods respectively.
    """
    def __init__(self, bars, events, short_window=100, long_window=400):
        """
        Initialses the Moving Avg. Cross Strategy.
        :param bars: The DataHandler object that provides bar information
        :param events: The Event Queue object
        :param short_window: The short moving average lookback
        :param long_window: The long moving average lookback
        """
        self.bars = bars
        self.symbol_list = self.bars.symbol_list
        self.events = events
        self.short_window = short_window
        self.long_window = long_window
        self.bought = self._calculate_initial_bought()

    def _calculate_initial_bought(self):
        """
        Adds keys to the bought dict for all symbols and sets them to 'OUT'
        bought dict의 초기값 지정해줌. ('OUT' or 'LONG' or 'SHORT')
        :return:
        """
        bought = {}
        for s in self.symbol_list:
            bought[s] = 'OUT'
        return bought

    def calc_signals(self, event):
        """
        Generates a new set of signal based on MAC SMA with the short window crossing
        the long window meaning a long entry and vice versa for short entry
        :param event: A MarketEvent Object
        :return:
        """
        if event.type == 'MARKET':
            for s in self.symbol_list:
                bars = self.bars.get_latest_n_bars_value(s, 'close', N=self.long_window)
                bar_date = self.bars.get_latest_bar_datetime(s)
                if (bars is not None) and (bars.size > 0):
                    short_sma = np.mean(bars[-self.short_window:])
                    long_sma = np.mean(bars[-self.long_window:])

                    symbol = s
                    dt = datetime.datetime.utcnow()
                    sig_dir = ""

                    if short_sma > long_sma and self.bought[s]=="OUT":
                        print("LONG: %s" % bar_date)
                        sig_dir = "LONG"
                        cur_price = self.bars.get_latest_bar_value(s, 'close')
                        signal = SignalEvent(1, symbol, dt, sig_dir, 1.0, cur_price)
                        self.events.put(signal)
                        self.bought[s] = 'LONG'
                    elif short_sma < long_sma and self.bought[s]=="LONG":
                        print("SHORT: %s" % bar_date)
                        sig_dir = "EXIT"
                        cur_price = self.bars.get_latest_bar_value(s, 'close')
                        signal = SignalEvent(1, symbol, dt, sig_dir, 1.0, cur_price)
                        self.events.put(signal)
                        self.bought[s] = 'OUT'



if __name__ == "__main__":
    csv_dir = 'G:/공유 드라이브/Project_TBD/Stock_Data/Minute/'
    symbol_list = ["005930"]
    initial_cap = 1000000.0
    heartbeat = 0.0
    start_date = datetime.datetime(2019, 11, 1, 9, 0, 0)

    backtest = Backtest(
        csv_dir, symbol_list, initial_cap, heartbeat, start_date,
        HistoricMinDataHandler, SimulatedExecutionHandler, Portfolio,
        MovingAverageCrossStrategy
    )
    backtest.simulate_trading()