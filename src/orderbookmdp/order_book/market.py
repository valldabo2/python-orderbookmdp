# -*- coding: utf-8 -*-
"""A limit order book market with defined order types in :py:mod:`OrderBookRL.order_book.order_types`.

The main function is to send a message to the market, receiving a possible trade or the order placed in the book.
A trade and a order is simply a list contaning information about them, see :py:mod:`OrderBookRL.order_book.constants`
for indexes of a trade and a order.

The abstract class :py:class:`Market` must implement send_message. An implementation of an :py:class:`ExternalMarket`
is implemented which can be used with an external flow of messages such as level 3 orderbook data.
The :py:class:`ExternalMarket` is first filled with a snapshot of the external order book and then artificial or real
messages can be sent.

"""

import abc

import numpy as np
from custom_inherit import DocInheritMeta

import orderbookmdp._orderbookmdp
from orderbookmdp.order_book.constants import BUY
from orderbookmdp.order_book.constants import EXT_ID
from orderbookmdp.order_book.constants import OIB_ID
from orderbookmdp.order_book.constants import SELL
from orderbookmdp.order_book.constants import SO_EXT_ID
from orderbookmdp.order_book.constants import SO_PRICE
from orderbookmdp.order_book.constants import SO_SIZE
from orderbookmdp.order_book.order_books import OrderBook
from orderbookmdp.order_book.order_books import PyOrderBook
from orderbookmdp.order_book.utils import to_int


def get_ob(ob_type: str, price_levels_type: str, price_level_type: str) -> OrderBook:
    """
    Returns an order book depending on the parameters

    Parameters
    ----------
    ob_type: str
        Type of order book.
    price_levels_type: str
        Type or price levels for the order book.
    price_level_type: str
        Type of order level for the price levels

    Returns
    -------
        orderbook: OrderBook

    """
    if ob_type == 'py':
        return PyOrderBook(price_levels_type, price_level_type)
    if ob_type == 'cy_order_book':
        return orderbookmdp._orderbookmdp.CyOrderBook(price_levels_type, price_level_type)


class Market(metaclass=DocInheritMeta(style="numpy", abstract_base_class=True)):
    """
    An abstract market class where an implementation needs to implement send_messages. A market always has an
    order book which is set in :py:meth:`__init__`.

    Attributes
    ----------
    ob: OrderBook
        The markets order book.
    tick_size: float
        The minimum multiple of price difference in a market.
    tick_dec: int
        Number of decimals in tick_size
    multipler: int
        10**tick_dec. Used to multiply price to int

    """

    def __init__(self, tick_size=0.01, ob_type='py', price_level_type='ordered_dict',
                 price_levels_type='sorted_dict'):
        """
        Parameters
        ----------
        tick_size: float
            The minimum multiple of price difference in a market.
        ob_type: str
            Type of order book.
        price_levels_type: str
            Type or price levels for the order book.
        price_level_type: str
            Type of order level for the price levels
        """
        self.ob = get_ob(ob_type, price_level_type, price_levels_type)
        self.tick_size = tick_size
        self.tick_dec = int(np.log10(1 / tick_size))
        self.multiplier = 10**self.tick_dec

    @abc.abstractmethod
    def send_message(self, message: dict) -> (list, tuple):
        """
        The main function of the market. The market receives a message and returns a possible trade or an order in the book.

        Parameters
        ----------
        message: SimpleNamespace
            Can for example be a limit order, market order, cancelation message etc. See :py:mod:`OrderBookRL.order_book.order_types`
            for different types

        Returns
        -------
            trades, order_in_book
                trades: list
                    If trades have occurred due the the message, all the trades are returned. Otherwise empty list
                order_in_book: tuple
                    If a limit order has been placed which size has not fully been matched, the remaining order in book
                    is returned. Otherwise -1.

        """


class ExternalMarket(Market):
    """
    An implementation of a :py:class:`Market` which can be used with an external flow of messages. When initiated, should
    be filled with a snapshot of the order book and then progressed with artificial or real messages.

    Attributes
    ----------
    external_market_order_ids : dict
        Keeps track of the external order ids if for example a cancellation or update of an external order occurs.
    time : str
        The current time of the market

    """
    def __init__(self, tick_size=0.01, ob_type='py', price_level_type='ordered_dict',
                 price_levels_type='sorted_dict',):
        super(ExternalMarket, self).__init__(tick_size, ob_type, price_level_type, price_levels_type)
        self.external_market_order_ids = {}
        self.time = '2000-1-1 00:00'

    def send_message(self, mess: dict, external=False) -> (list, tuple):
        """

        Parameters
        ----------
        message: SimpleNamespace
            Can for example be a limit order, market order, cancelation message etc. See :py:mod:`OrderBookRL.order_book.order_types`
            for different types
        external: bool
            If the message is an external message

        """
        trades, order_in_book = [], None
        mess_type = mess.type

        if external:
            self.time = mess.time

        if mess_type == 'received':
            order_type = mess.order_type
            if order_type == 'limit':

                if external:
                    trades, order_in_book = self.ob.limit(to_int(mess.price, self.multiplier),
                                                          mess.side, mess.size, mess.trader_id, self.time)
                else:
                    trades, order_in_book = self.ob.limit(mess.price,
                                                          mess.side, mess.size, mess.trader_id, self.time)

                if external and order_in_book is not None:
                    self.external_market_order_ids[mess.order_id] = order_in_book[OIB_ID]
            elif order_type == 'market':
                if mess.size != -1:
                    trades = self.ob.market_order(mess.size, mess.side, mess.trader_id, self.time)
                else:
                    trades = self.ob.market_order_funds(mess.funds*self.multiplier, mess.side, mess.trader_id, self.time)
        elif mess_type == 'done':
            if mess.reason == 'canceled':
                if external:
                    try:
                        order_id = self.external_market_order_ids.pop(mess.order_id)
                        self.ob.cancel(order_id)
                    except (ValueError, KeyError) as e:
                        # TODO Fix
                        # traceback.print_exc()
                        # print(mess)
                        pass
                else:
                    try:
                        self.ob.cancel(mess.order_id)
                    except (ValueError, KeyError) as e:
                        # TODO Fix
                        pass

        elif mess_type == 'change':
            if external:
                order_id = self.external_market_order_ids[mess.order_id]
                self.ob.update(order_id, mess.size)
            else:
                self.ob.update(mess.order_id, mess.size)

        return trades, order_in_book

    def fill_snap(self, snap: dict):
        """
        Fills the market with orders from a snapshot. The snapshot contains all limit orders in a market at a given time.

        Parameters
        ----------
        snap: dict
            Contains all the limit orders in the market. Format: {'asks':[order1, order2, ...], 'bids': [order1, order2, ...]

        """
        for message in snap['bids']:
            _, oib = self.ob.limit(to_int(float(message[SO_PRICE]), self.multiplier), BUY, float(message[SO_SIZE]), EXT_ID, self.time)
            if oib is not None:
                self.external_market_order_ids[message[SO_EXT_ID]] = oib[OIB_ID]
        for message in snap['asks']:
            _, oib = self.ob.limit(to_int(float(message[SO_PRICE]), self.multiplier), SELL, float(message[SO_SIZE]), EXT_ID, self.time)
            if oib is not None:
                self.external_market_order_ids[message[SO_EXT_ID]] = oib[OIB_ID]
