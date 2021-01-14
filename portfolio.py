import datetime
import queue
import numpy as np
import pandas as pd
from math import floor
import matplotlib.pyplot as plt

from event import FillEvent, OrderEvent
from performance import create_sharpe_ratio, create_drawdowns

class Portfolio(object):
    """
    The Portfolio class handles the positions and market valume of all instruments at a resolution of a "bar",
    i.e. secondly, minutely, hourly.

    The position DataFrame stores a time-index of the quantity of postion held.

    The holdings DataFrame stores the cash and total market holdings value of each symbol for a particular time-index,
    as well as the percentage change in portfolio total across bars.
    """

    def __init__(self, bars, events, start_date, initial_cap=10000.0):
        """
        Initialises the portfolio with bars and an event queue.
        Also includes a starting datetime index and initial capital
        :param bars: The DataHandler object with current market data.
        :param events: The Event Queue object.
        :param start_date: The start date of portfolio
        :param initial_cap: The starting capital in KRW
        """

        self.bars = bars #is bars a function?
        self.events = events
        self.symbol_list = self.bars.symbol_list #?
        self.start_date = start_date
        self.initial_cap = initial_cap

        self.all_positions = self.construct_all_positions()
        self.current_positions = self.construct_current_positions()
        self.all_holdings = self.construct_all_holdings()
        self.current_holdings = self.construct_current_holdings()

    def construct_all_positions(self):
        """
        Constructs the positions list using the start_date to determine when the time index will begin
        종목별 보유수량
        """
        all_pos_dict = dict((k,v) for k,v in [(s,0) for s in self.symbol_list])
        all_pos_dict["datetime"] = self.start_date
        return [all_pos_dict]

    def construct_all_holdings(self):
        """
        Constructs the holding list using the start_date to determine when the time index will begin
        종목별 평가금액, 현금, 수수료
        """
        d = dict((k,v) for k,v in [(s,0.0) for s in self.symbol_list])
        d['cash'] = self.initial_cap
        d['commission'] = 0.0
        d['total_value'] = self.initial_cap
        return [d]

    def construct_current_positions(self):
        """
        This constructs the dictionary which will hold the instantaneous position of the portfolio
        across all symbols.
        """
        d = dict((k, v) for k, v in [(s, 0) for s in self.symbol_list])
        return d

    def construct_current_holdings(self):
        """
        This constructs the dictionary which will hold th instantaneous value of the portfolio
        across all symbols.
        """
        d = dict((k, v) for k, v in [(s, 0.0) for s in self.symbol_list])
        d['cash'] = self.initial_cap
        d['commission'] = 0.0
        d['total_value'] = self.initial_cap
        return d #bracket 없는 것만 construct_all_holdings() 와 다름

        #live trading에서는 Brokerage에서 바로 요청 후 반영가능! backtesting은 계산 필요.

    def update_timeindex(self, event):
        """
        Adds a new record to the positions matrix for the current market date bar.
        This reflects the PREVIOUS bar, i.e. all current market data at this stage is known(OHLCV).

        Makes use of a MarketEvent from the events queue.
        :param event:
        """
        #Move timeindex by updating current positions
        #If position of stock change -> Make adjustment to current positions
        #Updated by update_timeindex() right after..
        #결국 current_position을 주축으로 계속 Fill과 Close가격에 변화에 따른 Holding의 변화를 모니터링 하고
        #이후 update_timeindex() 함수를 통해 반영하는 구조.
        latest_datetime = self.bars.get_latest_bar_datetime(self.symbol_list[0])

        #Update positions
        pos_dict = dict((k, v) for k, v in [(s,0) for s in self.symbol_list])
        pos_dict["datetime"] = latest_datetime

        for s in self.symbol_list:
            pos_dict[s] = self.current_positions[s]

        #Append the current positions
        self.all_positions.append(pos_dict)

        #Update holdings
        hold_dict = dict((k, v) for k, v in [(s, 0.0) for s in self.symbol_list])
        hold_dict["datetime"] = latest_datetime
        hold_dict['cash'] = self.current_holdings['cash']
        hold_dict['commission'] = self.current_holdings['commission']
        hold_dict['total_value'] = self.current_holdings['cash']

        for s in self.symbol_list:
            #Approximation by close price
            market_value = self.current_positions[s] * self.bars.get_latest_bar_value(s,'close')
            hold_dict[s] = market_value
            hold_dict['total_value'] += market_value

        #Append the current holdings
        self.all_holdings.append(hold_dict)

    def update_positions_from_fill(self, fill):
        """
        Takes a Fill object and updates the position matrix to reflect the new position.
        :param fill: The Fill object to update the position with
        """

        #Check whether the fill is a buy or sell
        fill_dir = 0
        if fill.direction == "BUY":
            fill_dir = 1
        elif fill.direction == "SELL":
            fill_dir = -1
        else:
            print("Fill direction error at position")

        #Update position list with new quantity
        self.current_positions[fill.symbol] += fill_dir * fill.quantity

    def update_holdings_from_fill(self, fill):
        """
        Takes a Fill object and updates the holding matrix to reflect the holdings value.
        :param fill: The Fill object to update the holdings with
        """

        # Check whether the fill is a buy or sell
        fill_dir = 0
        if fill.direction == "BUY":
            fill_dir = 1
        elif fill.direction == "SELL":
            fill_dir = -1
        else:
            print("Fill direction error at holdings")

        # Update holdings list with new quantity
        fill_cost = self.bars.get_latest_bar_value(fill.symbol, 'close') #Live Trading에서는 hts의 매입금액 사용하면 될듯, 결국 Slippage 비용도 여기에 반영해야함.
        cost = fill_dir * fill_cost * fill.quantity
        self.current_holdings[fill.symbol] += cost
        self.current_holdings['commission'] += fill.commission #수수료
        self.current_holdings["cash"] -= cost + fill.commission
        self.current_holdings['total_value'] -= cost + fill.commission #update_timeindex에서 q * close 된 평가금액 얹어줌.

    def update_fill(self, event):
        """
        Updates the portfolio current positions and holdings from FillEvent.
        :param event:
        """
        if event.type == 'FILL':
            self.update_positions_from_fill(event)
            self.update_holdings_from_fill(event)


    def generate_naive_order(self, signal):
        """
        Simply files an Order object as a constant quantity sizing of the signal object,
        without risk management or position sizing considerations.
        :param signal: The tuple containing Signal information
        """
        order = None

        symbol = signal.symbol
        direction = signal.signal_type
        strength = signal.strength
        cur_price = signal.cur_price

        mkt_quantity = 1
        est_fill_cost = cur_price * mkt_quantity #for Backtest & Slippage calc / slippage cost = fill_cost(HTS) - est_fill_cost
        cur_quantity = self.current_positions[symbol]
        order_type = 'MKT' #추후 지정가 주문도 고려필요

        if direction == 'LONG' and cur_quantity == 0:
            order = OrderEvent(symbol, order_type, mkt_quantity, 'BUY', est_fill_cost)
        if direction == 'SHORT' and cur_quantity == 0:
            order = OrderEvent(symbol, order_type, mkt_quantity, 'SELL', est_fill_cost)

        if direction == 'EXIT' and cur_quantity > 0:
            order = OrderEvent(symbol, order_type, abs(cur_quantity), 'SELL', est_fill_cost)
        if direction == 'EXIT' and cur_quantity < 0:
            order = OrderEvent(symbol, order_type, abs(cur_quantity), 'BUY', est_fill_cost)
        return order

    def update_signal(self, event):
        """
        Acts on a SignalEvent to generate new orders based on the portfolio logic.
        """
        if event.type == 'SIGNAL':
            order_event = self.generate_naive_order(event)
            self.events.put(order_event)

    def create_equity_curve_dataframe(self):
        """
        Creates a pandas DataFrame from the all_holdings list of dictionaries.
        :return:
        """
        curve = pd.DataFrame(self.all_holdings)
        curve.set_index('datetime', inplace=True)
        curve['returns'] = curve['total_value'].pct_change()
        curve['equity_curve'] = (1.0 + curve['returns']).cumprod()
        self.equity_curve = curve
        #class 변수로 만듦

    def output_summary_stats(self):
        """
        Creates a list of summary statistics for the portfolio.
        :return:
        """
        total_return = self.equity_curve['equity_curve'][-1]
        returns = self.equity_curve['returns']
        pnl = self.equity_curve['equity_curve']
        # self.equity_curve.to_csv("prac_equity_curve.csv")
        # pd.DataFrame(self.all_positions).to_csv("prac_position.csv")

        sharpe_ratio = create_sharpe_ratio(returns, periods='minutely')
        drawdown, max_dd, max_dd_duration = create_drawdowns(pnl)
        self.equity_curve['drawdown'] = drawdown

        stats = [
            ('Total_Return', "%0.2f%%" % ((total_return-1.0)*100.0)),
            ('Sharpe_Ratio', "%0.2f" % sharpe_ratio),
            ("Max Drawdown", "%0.2f%%" % (max_dd * 100.0)),
            ("Max Drawdown Dur.", "%d" % max_dd_duration)
        ]

        self.equity_curve.to_csv('equity_curve.csv')
        # pnl.plot()
        # plt.show()
        return stats

