class Event(object):
    """
    Event is base class providing an interface for all subsequent events,
    that will trigger further events in the trading infrastructure
    """
    pass

class MarketEvent(Event):
    """
    Handles the event of receiving a new market update with
    corresponding bars
    """

    def __init__(self):
        """
        initialises the Marketevent
        """
        self.type = 'MARKET'

class SignalEvent(Event):
    """
    Handles the event of sending a Signal from a Strategy object.
    This is received by a Portfolio object and acted upon
    """

    def __init__(self, strategy_id, symbol, datetime, signal_type, strength, cur_price):
        """
        Initialises SignalEvent.

        :param strategy_id: The unique identifier of strategy
        :param symbol: The Ticker Symbol ex) "005930"
        :param datetime: The timestamp at which the signal was generated
        :param signal_type: "LONG" of "SHORT"
        :param strength: An adjustment factor to scale quantity at Portfolio level. Useful for pairs-trading
        """
        self.type = "SIGNAL"
        self.strategy_id = strategy_id
        self.symbol = symbol
        self.datetime = datetime
        self.signal_type = signal_type
        self.strength = strength
        self.cur_price = cur_price

class OrderEvent(Event):
    """
    Handles the event of sending an Order to an execution system.
    The order contains a symbol (ex "005930"), a type (Market or Limit), quantity and a direction
    """

    def __init__(self, symbol, order_type, quantity, direction, est_fill_cost):
        """
        Initialises the order type.
        :param symbol: The instrument to trade
        :param order_type: "MKT" or "LMT"
        :param quantity: Non-negative INT
        :param direction: "BUY" or "SELL"
        """
        self.type = "ORDER"
        self.symbol = symbol
        self.order_type = order_type
        self.quantity = quantity
        self.direction = direction
        self.est_fill_cost = est_fill_cost

    def print_order(self):
        """
        Outputs the values within the Order.
        """
        print("Order: Symbols=%s, Type=%s, Quantity=%s, Direction=%s, est_Fill_Cost=%s" %
              (self.symbol, self.order_type, self.quantity, self.direction, self.est_fill_cost))

class FillEvent(Event):
    """
    Encapsulates the notion of a Filled Order, as returned from a brokerage.
    Stores the quantity of an instrument actually filled and at what price.
    In addition, stores the commission of the trade from the brokerage
    """

    def __init__(self, timeindex, symbol, exchange, quantity, direction, fill_cost, est_fill_cost, commission=None):
        """
        Initialises the FillEvent object.
        :param timeindex: The bar-resolution when the order was filled.
        :param symbol: The instrument which was filled
        :param exchange: The exchange where order was filled ex) Kiwoom
        :param quantity: The filled quantity
        :param direction: The direction of fill ("BUY" or "SELL")
        :param fill_cost: Holding Value in Wons
        :param commission: Commission paid
        """

        self.type = "FILL"
        self.timeindex = timeindex
        self.symbol = symbol
        self.exchange = exchange
        self.quantity = quantity
        self.direction = direction
        self.fill_cost = fill_cost #매입금액을 의미/ 내가 주문넣은 가격대비 비싸게 사면 반영댐(slippage)/ backtesting시에는 직접 계산
        self.est_fill_cost = est_fill_cost

        #Calculat Commission
        if commission is None:
            self.commission = self.calc_commission()
        else:
            self.commission = commission

    def calc_commission(self, mkt="Stocks"):
        """
        Calculates the fees of trading based on an Korean Stock Market norm
        추후 보완 필요!
        Slippage need to be added! Not here 여기는 수수료만 다루기
        """

        #Backtesting시에는 Slippage없이 signal이 나온 close로 그대로 체결되는것으로 가정
        #추후 보완필요!
        if self.exchange == "BT":
            fill_cost = self.est_fill_cost
        else:
            fill_cost = self.fill_cost

        transaction_cost = 0
        if mkt == "Stocks" and self.direction == "SELL":
            transaction_cost = 0.003 * fill_cost
        elif mkt == "Futures":
            transaction_cost = "need calculation"

        return transaction_cost