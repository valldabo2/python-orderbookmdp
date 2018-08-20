import abc

import numpy as np
from bintrees import FastAVLTree
from bintrees import FastRBTree
from sortedcontainers import SortedDict

import orderbookmdp._orderbookmdp
from orderbookmdp.order_book.constants import BUY
from orderbookmdp.order_book.constants import SELL
from orderbookmdp.order_book.price_level import DequeLevel
from orderbookmdp.order_book.price_level import OrderedDictLevel
from orderbookmdp.order_book.price_level import PriceLevel


def get_price_level(price_level_type: str) -> PriceLevel:
    """ Returns a price level based on parameter

    Parameters
    ----------
    price_level_type: str
        The type of price level to be used

    Returns
    -------
    price_level : PriceLevel

    """
    if price_level_type == 'ordered_dict':
        return OrderedDictLevel
    elif price_level_type == 'deque':
        return DequeLevel
    elif price_level_type == 'cydeque':
        return orderbookmdp._orderbookmdp.CyQeuePriceLevel


class PriceLevels(abc.ABC):
    """ Price levels containing order levels for different prices.

    The speed of the price level is of importance. Removing orders, acessing price levels are
    important functions.

    Attributes
    ----------
    price_level_constructor : constructor
        A constructor to create a price level

    """

    def __init__(self, price_level_type):
        """ Sets the price level constructor.

        Parameters
        ----------
        price_level_type: str
            The type of price level to be used
        """
        self.price_level_constructor = get_price_level(price_level_type)

    @abc.abstractmethod
    def get_level(self, side: int, price: int) -> PriceLevel:
        """ Returns the price level for a given side and price.
        Parameters
        ----------
        side : int
            BUY or SELL, the side of the level to get.
        price : int
            The price of the price level to get.

        Returns
        -------
        price_level: PriceLevel
        """

    @abc.abstractmethod
    def remove_level(self, side: int, price: int):
        """ Removes a price level for a given side and price.
        Parameters
        ----------
        side : int
            BUY or SELL, the side of the level to remove.
        price : int
            The price of the price level to remove.

        """

    @abc.abstractmethod
    def add_order(self, side: int, price: int, size: float, trader_id: int, order_id: int) -> list:
        """ Adds a order to a price level.

        Parameters
        ----------
        side: int
            BUY or SELL, see :py:mod:´OrderBookRL.order_book.constants´
        size: float
            Size of the order.
        price: float
            Price of the order
        trader_id: int
            Id of the trader sending the order
        order_id : int
            Id of the order to be added

        Returns
        -------
        order: list
            The added order
        """

    @abc.abstractmethod
    def get_ask(self) -> int:
        """ Gets the lowest sell price.
        Returns
        -------
        ask: int
        """

    @abc.abstractmethod
    def get_bid(self) -> int:
        """ Gets the highest buy price.
        Returns
        -------
        bid: int
        """

    @abc.abstractmethod
    def get_quotes(self) -> tuple:
        """ Returns the a tuple of quotes, (ask, ask_v, bid, bid_v)
        Returns
        -------
        quotes: tuple

        """

    @abc.abstractmethod
    def get_snap(self) -> dict:  # TODO add levels
        """ Returns the current snapshot of the order book.

        Returns
        -------
        snap: dict
            Contains all the limit orders in the market.
            Format: {'asks':[order1, order2, ...], 'bids': [order1, order2, ...]
        """

    @abc.abstractmethod
    def exist_buy_orders(self) -> bool:
        """ Returns true if there exists buy orders

        Returns
        -------
        bool
            True if successful, False otherwise.

        """

    @abc.abstractmethod
    def exist_sell_orders(self) -> bool:
        """ Returns true if there exists sell orders

        Returns
        -------
        bool
            True if successful, False otherwise.

        """

    @abc.abstractmethod
    def get_prices(self, side: int) -> int:
        """ Yields all the prices of a given side.

        Parameters
        ----------
        side : int
            BUY or SELL, which side to get prices for

        Yields
        -------
        price: int
        """

    def print_quotes(self, quotes):
        ask, ask_v, bid, bid_v = quotes
        m = '{:.5f}:av a:{:.2f} {:.2f}:b bv:{:.5f}'.format(ask_v, ask, bid, bid_v)
        print(m)


class SortedDictPriceLevels(PriceLevels):
    def __init__(self, price_level_type, max_price=1500000, min_price=300000, **kwargs):
        super(SortedDictPriceLevels, self).__init__(price_level_type)
        self.price_levels = SortedDict(), SortedDict()  # BUY, SELL
        self.max_price = max_price
        self.min_price = min_price

    def get_level(self, side: int, price: float) -> PriceLevel:
        return self.price_levels[side][price]

    def add_order(self, side: int, price: float, size: float, trader_id: int, order_id: int) -> list:

        if self.min_price <= price <= self.max_price:
            # diff = round(price, 2) - price
            # if abs(diff) > 10e-13:
            #    print('p:{:.15f} diff:{:.3e}'.format(price, diff))

            if price not in self.price_levels[side]:
                self.price_levels[side][price] = self.price_level_constructor()
            order = [side, price, size, trader_id, order_id]
            self.price_levels[side][price].append(order)
            return order
        else:
            return -1

    def remove_level(self, side: int, price: float):
        self.price_levels[side].pop(price)

    def get_ask(self) -> float:
        return self.price_levels[SELL].keys()[0]

    def get_bid(self) -> float:
        return self.price_levels[BUY].keys()[-1]

    def get_snap(self) -> dict:
        snap = {'asks': {}, 'bids': {}}
        for bid_price in self.price_levels[BUY]:
            snap['bids'][bid_price] = self.get_level(BUY, bid_price).size
        for ask_price in self.price_levels[SELL]:
            snap['asks'][ask_price] = self.get_level(SELL, ask_price).size
        return snap

    def exist_buy_orders(self) -> bool:
        return self.price_levels[BUY].__len__() > 0

    def exist_sell_orders(self) -> bool:
        return self.price_levels[SELL].__len__() > 0

    def get_prices(self, side: int) -> int:
        for price in self.price_levels[side]:
            yield price

    def get_quotes(self) -> tuple:
        ask, bid = self.get_ask(), self.get_bid()
        bid_v = self.price_levels[BUY][bid].size
        ask_v = self.price_levels[SELL][ask].size
        return ask, ask_v, bid, bid_v  # Quotes : (ask, ask_v, bid, bid_v)


class RBTreePriceLevels(SortedDictPriceLevels):
    def __init__(self, price_level_type, **kwargs):
        super(RBTreePriceLevels, self).__init__(price_level_type, **kwargs)
        self.price_levels = FastRBTree(), FastRBTree()

    def get_ask(self) -> float:
        return self.price_levels[SELL].min_key()

    def get_bid(self) -> float:
        return self.price_levels[BUY].max_key()


class AVLTreePriceLevels(RBTreePriceLevels):
    def __init__(self, price_level_type, **kwargs):
        super(AVLTreePriceLevels, self).__init__(price_level_type, **kwargs)
        self.price_levels = FastAVLTree(), FastAVLTree()


class ListPriceLevels(PriceLevels):
    def __init__(self, price_level_type, tick_size=0.01, max_price=1500000, min_price=300000):
        super(ListPriceLevels, self).__init__(price_level_type)

        self.tick_size = tick_size
        self.tick_dec = int(np.log10(1 / self.tick_size))

        self.max_price = max_price
        self.min_price = min_price

        self.max_index = max_price - min_price

        self.bid_index = 0
        self.ask_index = self.max_index

        self.price_level_list = [self.price_level_constructor() for _ in range(self.max_index + 1)]

    def get_price_index(self, price: int) -> int:
        return price - self.min_price

    def get_price(self, index: int) -> float:
        return index + self.min_price

    def get_level(self, side: int, price: int) -> PriceLevel:
        return self.price_level_list[self.get_price_index(price)]

    def is_empty(self, index):
        return len(self.price_level_list[index].orders) == 0

    def remove_level(self, side: int, price: int):
        price_index = self.get_price_index(price)
        self.price_level_list[price_index] = self.price_level_constructor()
        if price_index == self.ask_index:
            while self.is_empty(self.ask_index) and self.ask_index < self.max_index:
                self.ask_index += 1
        elif price_index == self.bid_index:
            while self.is_empty(self.bid_index) and self.bid_index > 0:
                self.bid_index -= 1

    def add_order(self, side: int, price: float, size: float, trader_id: int, order_id: int) -> list:
        if self.min_price <= price <= self.max_price:
            price_index = self.get_price_index(price)
            price_level = self.price_level_list[price_index]
            order = [side, price, size, trader_id, order_id]
            price_level.append(order)
            if side == BUY and price_index >= self.bid_index:
                self.bid_index = price_index
            elif side == SELL and price_index <= self.ask_index:
                self.ask_index = price_index
            return order
        else:
            return -1

    def get_ask(self) -> int:
        return self.get_price(self.ask_index)

    def get_bid(self) -> int:
        return self.get_price(self.bid_index)

    def get_snap(self) -> dict:
        snap = {'asks': {}, 'bids': {}}

        for buy_index in self.get_indexes(BUY):
            snap['bids'][self.get_price(buy_index)] = self.price_level_list[buy_index].size
        for ask_index in self.get_indexes(SELL):
            snap['asks'][self.get_price(ask_index)] = self.price_level_list[ask_index].size
        return snap

    def exist_buy_orders(self) -> bool:
        return len(self.price_level_list[self.bid_index].orders) > 0

    def exist_sell_orders(self) -> bool:
        return len(self.price_level_list[self.ask_index].orders) > 0

    def get_indexes(self, side: int):
        if side == BUY:
            buy_index = self.bid_index
            while buy_index >= 0:
                if not self.is_empty(buy_index):
                    yield buy_index
                buy_index -= 1
            return
        else:
            ask_index = self.ask_index
            while ask_index <= self.max_index:
                if not self.is_empty(ask_index):
                    yield ask_index
                ask_index += 1
            return

    def get_prices(self, side: int) -> float:
        for index in self.get_indexes(side):
            yield self.get_price(index)
        return

    def get_quotes(self) -> tuple:
        ask, bid = self.get_ask(), self.get_bid()
        bid_v = self.price_level_list[self.bid_index].size
        ask_v = self.price_level_list[self.ask_index].size
        return ask, ask_v, bid, bid_v  # Quotes : (ask, ask_v, bid, bid_v)
