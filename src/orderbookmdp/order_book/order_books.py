import abc

from custom_inherit import DocInheritMeta

import orderbookmdp._orderbookmdp
from orderbookmdp.order_book.constants import BUY
from orderbookmdp.order_book.constants import O_ID
from orderbookmdp.order_book.constants import O_PRICE
from orderbookmdp.order_book.constants import O_SIDE
from orderbookmdp.order_book.constants import O_SIZE
from orderbookmdp.order_book.constants import O_TRADER_ID
from orderbookmdp.order_book.constants import SELL
from orderbookmdp.order_book.price_levels import AVLTreePriceLevels
from orderbookmdp.order_book.price_levels import ListPriceLevels
from orderbookmdp.order_book.price_levels import PriceLevels
from orderbookmdp.order_book.price_levels import RBTreePriceLevels
from orderbookmdp.order_book.price_levels import SortedDictPriceLevels


def get_price_levels(price_levels_type: str, price_level_type: str, **kwargs) -> PriceLevels:
    """
    Returns a type or price levels based on the parameters

    Parameters
    ----------
    price_levels_type: str
        Type or price levels for the order book.
    price_level_type: str
        Type of order level for the price levels
    kwargs

    Returns
    -------
        price_levels: PriceLevels

    """
    if price_levels_type == 'sorted_dict':
        return SortedDictPriceLevels(price_level_type, **kwargs)
    elif price_levels_type == 'fast_rb':
        return RBTreePriceLevels(price_level_type, **kwargs)
    elif price_levels_type == 'fast_avl':
        return AVLTreePriceLevels(price_level_type, **kwargs)
    elif price_levels_type == 'list':
        return ListPriceLevels(price_level_type, **kwargs)
    elif price_levels_type == 'cylist':
        return orderbookmdp._orderbookmdp.CyListPriceLevels(price_level_type, **kwargs)


class OrderBook(metaclass=DocInheritMeta(style="numpy", abstract_base_class=True)):
    """ A abstract class defining a order book interface.

    The main functions are the functions for the messages. Sending a limit order, market order etc. The order book handles
    the matching and storing of limit orders.

    Important notes is the speed of adding a limit order, cancelling a limit order or updating a limit order.

    Attributes
    ----------
    orders : dict
        All current orders in the order book, key is the order id
    order_id : int
        The internal order id set by the order book. Is incremented for each order sent to the order book.

    """

    def __init__(self, price_level_type='cydeque', price_levels_type='cylist'):
        self.price_levels = get_price_levels(price_levels_type, price_level_type)
        self.orders = {}
        self.order_id = 0

    @abc.abstractmethod
    def limit(self, price: float, side: int, size: float, trader_id: int) -> (list, tuple):
        """
        Handles a limit order sent to the order book. Matches the limit order if possible, otherwise puts it in the order book.

        Parameters
        ----------
        price: float
            Price of the order.
        side: int
            BUY or SELL, see :py:mod:´OrderBookRL.order_book.constants´
        size: float
            Size of the order.
        trader_id: int
            Id of the trader sending the order

        Returns
        -------
            trades, order_in_book
                trades: list
                    If trades have occurred due the the message, all the trades are returned. Otherwise empty list
                order_in_book: tuple
                    If a limit order has been placed which size has not fully been matched, the remaining order in book
                    is returned. Otherwise -1.

        """

    @abc.abstractmethod
    def market_order(self, size: float, side: int, trader_id: int) -> list:
        """
        Handles a market order sent to the order book. Matches the market order if possible.

        Parameters
        ----------
        side: int
            BUY or SELL, see :py:mod:´OrderBookRL.order_book.constants´
        size: float
            Size of the order.
        trader_id: int
            Id of the trader sending the order

        Returns
        -------
            trades: list
                If trades have occurred due the the message, all the trades are returned. Otherwise empty list

        """

    @abc.abstractmethod
    def market_order_funds(self, funds: float, side: int, trader_id: int) -> list:
        """
        Handles a market order sent to the order book. Matches the market order if possible.

        Parameters
        ----------
        funds: float
            Size of the order.
        side: int
            BUY or SELL, see :py:mod:´OrderBookRL.order_book.constants´
        trader_id: int
            Id of the trader sending the order

        Returns
        -------
            trades: list
                If trades have occurred due the the message, all the trades are returned. Otherwise empty list

        """

    @abc.abstractmethod
    def cancel(self, order_id: int):
        """
        Attempts to cancel a order by its order id

        Parameters
        ----------
        order_id: int
            The order id of the order to be cancelled

        """

    @abc.abstractmethod
    def update(self, order_id: int, size: float):
        """
        Attempts to update a order by its order id

        Parameters
        ----------
        order_id: int
            The order id of the order to be updated
        size: float
            The new size of the order

        """


class PyOrderBook(OrderBook):
    """An implementation of the abstract class :py:class:`OrderBook`.
    """
    def limit(self, price: float, side: int, size: float, trader_id: int, time: str) -> (list, tuple):
        trades = []
        if side == BUY:
            if self.price_levels.exist_sell_orders():
                ask = self.price_levels.get_ask()
                while price >= ask:
                    price_level = self.price_levels.get_level(SELL, ask)
                    while price_level.is_not_empty():
                        level_entry = price_level.get_first()
                        level_entry_size = level_entry[O_SIZE]
                        if size < level_entry_size:
                            price_level.update(level_entry, -size)
                            # Trade : (trader_id, counter_part_id, price, size, order_id)
                            trades.append((trader_id, level_entry[O_TRADER_ID], ask, size, level_entry[O_ID], side, time))
                            return trades, None
                        else:
                            price_level.delete_first(level_entry)
                            self.orders.pop(level_entry[O_ID])
                            if price_level.is_empty():
                                self.price_levels.remove_level(SELL, ask)
                            size -= level_entry_size
                            # Trade : (trader_id, counter_part_id, price, size, order_id)
                            trades.append((trader_id, level_entry[O_TRADER_ID], ask, level_entry_size, level_entry[O_ID], side, time))
                            if size == 0:
                                return trades, None

                    if self.price_levels.exist_sell_orders():
                        ask = self.price_levels.get_ask()
                    else:
                        break

            self.order_id += 1
            # Limit Order: [side, price, size, trader_id, order_id]
            order = self.price_levels.add_order(side, price, size, trader_id, self.order_id)
            if order != -1:
                self.orders[self.order_id] = order
                # Order in Book : (order_id, size, side, price)
                order_in_book = (self.order_id, size, side, price)

                return trades, order_in_book
            else:
                return trades, None
        else:
            if self.price_levels.exist_buy_orders():
                bid = self.price_levels.get_bid()
                while price <= bid:
                    price_level = self.price_levels.get_level(BUY, bid)
                    while price_level.is_not_empty():
                        level_entry = price_level.get_first()
                        level_entry_size = level_entry[O_SIZE]
                        if size < level_entry_size:
                            price_level.update(level_entry, -size)
                            # Trade : (trader_id, counter_part_id, price, size, order_id)
                            trades.append((trader_id, level_entry[O_TRADER_ID], bid, size, level_entry[O_ID], side, time))
                            return trades, None
                        else:
                            price_level.delete_first(level_entry)
                            self.orders.pop(level_entry[O_ID])
                            if price_level.is_empty():
                                self.price_levels.remove_level(BUY, bid)
                            size -= level_entry_size
                            # Trade : (trader_id, counter_part_id, price, size, order_id)
                            trades.append((trader_id, level_entry[O_TRADER_ID], bid, level_entry_size, level_entry[O_ID], side, time))
                            if size == 0:
                                return trades, None

                    if self.price_levels.exist_buy_orders():
                        bid = self.price_levels.get_bid()
                    else:
                        break

            self.order_id += 1
            # Limit Order: [side, price, size, trader_id, order_id]
            order = self.price_levels.add_order(side, price, size, trader_id, self.order_id)

            if order != -1:
                self.orders[self.order_id] = order
                # Order in Book : (order_id, size, side, price)
                order_in_book = (self.order_id, size, side, price)

                return trades, order_in_book
            else:
                return trades, None

    def cancel(self, order_id: int):
        if order_id in self.orders:
            order = self.orders.pop(order_id)
            level = self.price_levels.get_level(order[O_SIDE], order[O_PRICE])
            level.delete(order)
            if level.is_empty():
                self.price_levels.remove_level(order[O_SIDE], order[O_PRICE])

    def update(self, order_id: int, size: float):
        if order_id in self.orders:
            order = self.orders[order_id]
            price_level = self.price_levels.get_level(order[O_SIDE], order[O_PRICE])
            price_level.update(order, size - order[O_SIZE])

    def market_order(self, size: float, side: int, trader_id: int, time: str) -> list:
        trades = []
        if side == BUY:
            while (size > 0) and self.price_levels.exist_sell_orders():
                ask = self.price_levels.get_ask()
                price_level = self.price_levels.get_level(SELL, ask)
                while price_level.is_not_empty():
                    level_entry = price_level.get_first()
                    level_entry_size = level_entry[O_SIZE]
                    if size < level_entry_size:
                        price_level.update(level_entry, -size)
                        # Trade : (trader_id, counter_part_id, price, size, order_id)
                        trades.append((trader_id, level_entry[O_TRADER_ID], ask, size, level_entry[O_ID], side, time))
                        return trades
                    else:
                        price_level.delete_first(level_entry)
                        self.orders.pop(level_entry[O_ID])
                        size -= level_entry_size
                        # Trade : (trader_id, counter_part_id, price, size, order_id)
                        trades.append((trader_id, level_entry[O_TRADER_ID], ask, level_entry_size, level_entry[O_ID], side, time))
                        if size == 0:
                            return trades

                self.price_levels.remove_level(SELL, ask)
        else:
            while (size > 0) and self.price_levels.exist_buy_orders():
                bid = self.price_levels.get_bid()
                price_level = self.price_levels.get_level(BUY, bid)
                while price_level.is_not_empty():
                    level_entry = price_level.get_first()
                    level_entry_size = level_entry[O_SIZE]
                    if size < level_entry_size:
                        price_level.update(level_entry, -size)
                        # Trade : (trader_id, counter_part_id, price, size, order_id)
                        trades.append((trader_id, level_entry[O_TRADER_ID], bid, size, level_entry[O_ID], side, time))
                        return trades
                    else:
                        price_level.delete_first(level_entry)
                        self.orders.pop(level_entry[O_ID])
                        size -= level_entry_size
                        # Trade : (trader_id, counter_part_id, price, size, order_id)
                        trades.append((trader_id, level_entry[O_TRADER_ID], bid, level_entry_size, level_entry[O_ID], side, time))
                        if size == 0:
                            return trades

                self.price_levels.remove_level(BUY, bid)
        return trades

    def market_order_funds(self, funds: float, side: int, trader_id: int, time: str) -> list:
        trades = []
        if side == BUY:
            while (funds > 0) and self.price_levels.exist_sell_orders():
                ask = self.price_levels.get_ask()
                size = funds / ask
                price_level = self.price_levels.get_level(SELL, ask)
                while price_level.is_not_empty():
                    level_entry = price_level.get_first()
                    level_entry_size = level_entry[O_SIZE]
                    if size < level_entry_size:
                        price_level.update(level_entry, -size)
                        # Trade : (trader_id, counter_part_id, price, size, order_id)
                        trades.append((trader_id, level_entry[O_TRADER_ID], ask, size, level_entry[O_ID], side, time))
                        return trades
                    else:
                        price_level.delete_first(level_entry)
                        self.orders.pop(level_entry[O_ID])
                        size -= level_entry_size
                        # Trade : (trader_id, counter_part_id, price, size, order_id)
                        trades.append((trader_id, level_entry[O_TRADER_ID], ask, level_entry_size, level_entry[O_ID], side, time))
                        if size == 0:
                            return trades
                        else:
                            funds -= level_entry_size * ask

                self.price_levels.remove_level(SELL, ask)
        else:
            while (funds > 0) and self.price_levels.exist_buy_orders():
                bid = self.price_levels.get_bid()
                size = funds / bid
                price_level = self.price_levels.get_level(BUY, bid)
                while price_level.is_not_empty():
                    level_entry = price_level.get_first()
                    level_entry_size = level_entry[O_SIZE]
                    if size < level_entry_size:
                        price_level.update(level_entry, -size)
                        # Trade : (trader_id, counter_part_id, price, size, order_id)
                        trades.append((trader_id, level_entry[O_TRADER_ID], bid, size, level_entry[O_ID], side, time))
                        return trades
                    else:
                        price_level.delete_first(level_entry)
                        self.orders.pop(level_entry[O_ID])
                        size -= level_entry_size
                        # Trade : (trader_id, counter_part_id, price, size, order_id)
                        trades.append((trader_id, level_entry[O_TRADER_ID], bid, level_entry_size, level_entry[O_ID], side, time))
                        if size == 0:
                            return trades
                        else:
                            funds -= level_entry_size * bid

                self.price_levels.remove_level(BUY, bid)
        return trades
