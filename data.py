from abc import abstractmethod, ABCMeta
import datetime
import os, os.path
import numpy as np
import pandas as pd
from event import MarketEvent

class DataHandler(object):
    """
    DataHandler is an Abstract Base Class(ABC) providing interface for all subsequent data handlers (both live and historic).

    cf) ABC(Abstract Base Class)
    ABC acts like mother class of its sub classes, gives them same foundation structures of sub classes.
    ABC by itself cannot be initiated. It only works as a foundation structure of sub classes

    The goal of a DataHandler object is to output a generated set of bars for each symbol requested.

    This will replicate how a live strategy would function as current market data would be sent "down the pipe".
    Thus a historical and live system will be treated identically by the rest of the backtesting suite.
    """

    __metaclass__ = ABCMeta

    # @classmethod #참조: https://docs.python.org/3/library/abc.html
    @abstractmethod
    def get_latest_bar(self, symbol):
        """
        returns latest bar updated
        """
        raise NotImplementedError("Should implement get_latest_bar()")

    @abstractmethod
    def get_latest_n_bars(self, symbol, N=1):
        """
        :param N: Number of wanted bars
        :return: the last N bars updated
        """
        raise NotImplementedError("Should implement get_latest_n_bars()")

    @abstractmethod
    def get_latest_bar_datetime(self, symbol):
        """
        :return: a Python datetime object for the last bar
        """
        raise NotImplementedError("Should implement get_latest_bar_datetime()")

    @abstractmethod
    def get_latest_bar_value(self, symbol, val_type):
        """
        :param val_type: one of OHLCV, Quotes, Open Interest(OI)
        :return: returns one of values designated by val_type
        """
        raise NotImplementedError("Should implement get_latest_bar_value()")

    @abstractmethod
    def get_latest_n_bars_value(self, symbol, val_type, N=1):
        """
        :param symbol:
        :param val_type: one of OHLCV, Quotes, Open Interest(OI)
        :param N: Number of bars considered
        :return: returns one of N-bars values designated by val_type
        """
        raise NotImplementedError("Should implement get_latest_n_bars_value()")

    @abstractmethod
    def update_bars(self):
        """
        Pushes the latest bars to the bars_queue for each symbol in a tuple OHLCV format:
        (datetime, open, high, low, close, volume, open interest)
        """
        raise NotImplementedError("Should implement update_bars()")

class HistoricMinDataHandler(DataHandler):
    """
    HistoricMinDataHandler is design to read CSV files for each requested symbol from G-Drive
    and provide the "latest" bar in manner identical to a live trading interface
    """

    def __init__(self, events, csv_dir, symbol_list):
        """
        Initialises the historic minute data handler by requesting the CSV files and a list of symbols.
        It will be assumed that all files are of the form 'symbol.csv', where symbol is a string in the list.
        :param events: The event queue
        :param csv_dir: Absolute directory path to CSV files.
        :param symbol_list: A list of symbol strings.
        """

        self.events = events
        self.csv_dir = csv_dir
        self.symbol_list = symbol_list

        self.symbol_data = {}
        self.latest_symbol_data = {}
        self.continue_backtest = True

        self._open_convert_csv_files()

    def _open_convert_csv_files(self):
        """
        Opens the CSV files from the data directory, converting them into pandas DataFrames within a symbol dictionary.
        For this handler it will be assumed that the data is take from internal G-Drive. Thus format will be hard coded.
        """

        comb_index = None
        for s in self.symbol_list:
            #Load CSV with no header information, indexed on date
            self.symbol_data[s] = pd.io.parsers.read_csv(
                os.path.join(self.csv_dir, "%s_minute_prac.csv" % s), #hard coded!?
                header=0, index_col=0
                #,parse_dates=True,
                #names=['date', 'close', 'open','high', 'low', 'volume'] #needed for getattr????
            )
            self.symbol_data[s].index = pd.to_datetime(self.symbol_data[s].index, format="%Y%m%d%H%M%S")
            self.symbol_data[s].sort_index(inplace=True)

            #Combine the index to pad forward values
            if comb_index is None:
                comb_index = self.symbol_data[s].index
            else:
                comb_index.union(self.symbol_data[s].index)

            #Set the latest symbol data to None
            self.latest_symbol_data[s] = []
            #latest_symbol_data 다루는 방식 중요 / 점점 쌓여감

        for s in self.symbol_list:
            self.symbol_data[s] = self.symbol_data[s].\
                                    reindex(index=comb_index, method='pad').iterrows() #use .iterrows() to make it as Generator object!

    def _get_new_bar(self, symbol):
        """
        :return: the latest bar from data feed.
        """
        for bar in self.symbol_data[symbol]:
            yield bar

        #using yield method to create Generater to make it iterable.
        #Thus we can use next() function in update_bars
        #cf) Generater is iterater and memory efficient. Best for large dataset iterating only once in lifetime
        #https://tech.ssut.me/what-does-the-yield-keyword-do-in-python/


    def get_latest_bar(self, symbol):
        """
        :return: the last bar from the latest_symbol list.
        """
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("Symbol is not available!!")
            raise
        else:
            return bars_list[-1]

    def get_latest_n_bars(self, symbol, N=1):
        """
        :return: latest n bars or n-k if less available
        """
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("Symbol is not available!!")
            raise
        else:
            return bars_list[-N:]
        #update bar에서 latest_symbol_data에 넣어주는건 bar 하나인데 어떻게 -N개 만큼 가져올수 있는거지?

    def get_latest_bar_datetime(self, symbol):
        """
        :return: Python datetime object for the last bar
        """
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("Symbol is not available!!")
            raise
        else:
            return bars_list[-1][0]

    def get_latest_bar_value(self, symbol, val_type):
        """
        :param val_type: one of OHLCV, Quotes, Open Interest(OI)
        :return: returns one of values designated by val_type
        """
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("Symbol is not available!!")
            raise
        else:
            return getattr(bars_list[-1][1], val_type)

    def get_latest_n_bars_value(self, symbol, val_type, N=1):
        """
        :param val_type: one of OHLCV, Quotes, Open Interest(OI)
        :param N: Number of bars considered
        :return: returns one of N-bars values designated by val_type
        """
        try:
            bars_list = self.get_latest_n_bars(symbol, N)
        except KeyError:
            print("Symbol is not available!!")
            raise
        else:
            return np.array([getattr(bar[1], val_type) for bar in bars_list])

    def update_bars(self):
        """
        Pushes the latest bars to the bars_queue for each symbol in a tuple OHLCV format:
        (datetime, open, high, low, close, volume)
        """
        for s in self.symbol_list:
            try:
                bar = next(self._get_new_bar(s))
            except StopIteration: #when next() function gets to end, it emits StopIteration error
                self.continue_backtest = False
            else:
                if bar is not None:
                    self.latest_symbol_data[s].append(bar)

        #?
        # print("length: ", len(self.latest_symbol_data[s])) #Length가 계속 늘어남, 일정이상 커지면 과거 정보는 버려줘야하는거 아닌가?
        # print(self.latest_symbol_data[s])
        self.events.put(MarketEvent()) # put() 함수는 Queue에 Item을 넣는 함수
