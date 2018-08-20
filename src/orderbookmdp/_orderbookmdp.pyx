def long(args):
    return max(args, key=len)

from collections import deque
import numpy as np
from cpython cimport list

cdef int BUY = 0
cdef int SELL = 1
# Limit Order: [side, price, size, trader_id, order_id]
cdef int O_SIDE = 0
cdef int O_PRICE = 1
cdef int O_SIZE = 2
cdef int O_TRADER_ID = 3
cdef int O_ID = 4
# Trade : (trader_id, counter_part_id, price, size, order_id, side, time)
cdef int T_ID = 0
cdef int TC_ID = 1
cdef int T_PRICE = 2
cdef int T_SIZE = 3
cdef int T_OID = 4
cdef int T_SIDE = 5
cdef int T_TIME = 6
# Order in Book : (order_id, size, side, price)
cdef int OIB_ID = 0
cdef int OIB_SIZE = 1
cdef int OIB_SIDE = 2
cdef int OIB_PRICE = 3
# Quotes : (ask, ask_v, bid, bid_v)
cdef int Q_ASK = 0
cdef int Q_ASKV = 1
cdef int Q_BID = 2
cdef int Q_BIDV = 3
# External Trader
cdef int EXT_ID = -1
# Snapshot Order : [price, size, external_market_order_id]
cdef int SO_PRICE = 0
cdef int SO_SIZE = 1
cdef int SO_EXT_ID = 2


cdef class CyQeuePriceLevel:

    cdef float size
    cdef public object orders

    def __init__(self):
        self.size = 0.0
        self.orders = deque()

    cpdef append(self, list order):
        self._add(order)
        self.size += order[O_SIZE]

    @property
    def size(self):
        return self.size

    cdef _add(self, list order):
        """Example function with PEP 484 type annotations.

        The return type must be duplicated in the docstring to comply
        with the NumPy docstring style.

        Parameters
        ----------
        param1
            The first parameter.
        param2
            The second parameter.

        Returns
        -------
        bool
            True if successful, False otherwise.

        """
        self.orders.append(order)

    cpdef delete(self, list order):
        """Example function with PEP 484 type annotations.

        The return type must be duplicated in the docstring to comply
        with the NumPy docstring style.

        Parameters
        ----------
        param1
            The first parameter.
        param2
            The second parameter.

        Returns
        -------
        bool
            True if successful, False otherwise.

        """
        self._remove(order)
        self.size -= order[O_SIZE]

    cdef _remove(self, list order):
        """Example function with PEP 484 type annotations.

        The return type must be duplicated in the docstring to comply
        with the NumPy docstring style.

        Parameters
        ----------
        param1
            The first parameter.
        param2
            The second parameter.

        Returns
        -------
        bool
            True if successful, False otherwise.

        """
        self.orders.remove(order)

    cpdef update(self, list order, double diff):
        """Example function with PEP 484 type annotations.

        The return type must be duplicated in the docstring to comply
        with the NumPy docstring style.

        Parameters
        ----------
        param1
            The first parameter.
        param2
            The second parameter.

        Returns
        -------
        bool
            True if successful, False otherwise.

        """
        self.size += diff
        order[O_SIZE] += diff

    cpdef list get_first(self):
        """Example function with PEP 484 type annotations.

        The return type must be duplicated in the docstring to comply
        with the NumPy docstring style.

        Parameters
        ----------
        param1
            The first parameter.
        param2
            The second parameter.

        Returns
        -------
        bool
            True if successful, False otherwise.

        """
        return self.orders[0]

    cpdef delete_first(self, list order):
        """Example function with PEP 484 type annotations.

        The return type must be duplicated in the docstring to comply
        with the NumPy docstring style.

        Parameters
        ----------
        param1
            The first parameter.
        param2
            The second parameter.

        Returns
        -------
        bool
            True if successful, False otherwise.

        """
        self._remove_first()
        self.size -= order[O_SIZE]

    cdef _remove_first(self):
        """Example function with PEP 484 type annotations.

        The return type must be duplicated in the docstring to comply
        with the NumPy docstring style.

        Parameters
        ----------
        param1
            The first parameter.
        param2
            The second parameter.

        Returns
        -------
        bool
            True if successful, False otherwise.

        """
        self.orders.popleft()

    cpdef is_not_empty(self):
        """Example function with PEP 484 type annotations.

        The return type must be duplicated in the docstring to comply
        with the NumPy docstring style.

        Parameters
        ----------
        param1
            The first parameter.
        param2
            The second parameter.

        Returns
        -------
        bool
            True if successful, False otherwise.

        """
        return len(self.orders) > 0

    cpdef list get_last(self):
        """Example function with PEP 484 type annotations.

        The return type must be duplicated in the docstring to comply
        with the NumPy docstring style.

        Parameters
        ----------
        param1
            The first parameter.
        param2
            The second parameter.

        Returns
        -------
        bool
            True if successful, False otherwise.

        """
        return self.orders[-1]

    cpdef delete_last(self, list order):
        """Example function with PEP 484 type annotations.

        The return type must be duplicated in the docstring to comply
        with the NumPy docstring style.

        Parameters
        ----------
        param1
            The first parameter.
        param2
            The second parameter.

        Returns
        -------
        bool
            True if successful, False otherwise.

        """
        self._remove_last()
        self.size -= order[O_SIZE]

    cdef _remove_last(self):
        """Example function with PEP 484 type annotations.

        The return type must be duplicated in the docstring to comply
        with the NumPy docstring style.

        Parameters
        ----------
        param1
            The first parameter.
        param2
            The second parameter.

        Returns
        -------
        bool
            True if successful, False otherwise.

        """
        self.orders.pop()

    cpdef is_empty(self):
        return len(self.orders) == 0


cdef class CyListPriceLevels:

    cdef double tick_size
    cdef int tick_dec
    cdef int max_index
    cdef public int max_price
    cdef public int min_price
    cdef int bid_index
    cdef int ask_index
    cdef list price_level_list

    def __init__(self, price_level_type, tick_size=0.01, max_price=13000, min_price=5000, **kwargs):

        self.tick_size = tick_size
        self.tick_dec = int(np.log10(1/self.tick_size))
        self.max_price = int(max_price*10**self.tick_dec)
        self.min_price = int(min_price*10**self.tick_dec)
        self.max_index = self.max_price - self.min_price
        self.bid_index = 0
        self.ask_index = self.max_index

        self.price_level_list = [CyQeuePriceLevel() for _ in range(self.max_index + 1)]

    cdef int get_price_index(self, int price):
        return price - self.min_price

    cdef int get_price(self, int index):
        return index + self.min_price

    cpdef CyQeuePriceLevel get_level(self, int side, int price):
        return self.price_level_list[self.get_price_index(price)]

    cpdef is_empty(self, int index):
        return len(self.price_level_list[index].orders) == 0

    cpdef remove_level(self, int side, int price):
        cdef int price_index = self.get_price_index(price)
        self.price_level_list[price_index] = CyQeuePriceLevel()
        if price_index == self.ask_index:
            while self.is_empty(self.ask_index) and self.ask_index < self.max_index:
                self.ask_index += 1
        elif price_index == self.bid_index:
            while self.is_empty(self.bid_index) and self.bid_index > 0:
                self.bid_index -= 1

    cpdef add_order(self, int side, long int price, double size, int trader_id, long int order_id):
        if self.min_price <= price < self.max_price:
            price_index = self.get_price_index(price)
            price_level = self.price_level_list[price_index]
            order = [side, price, size, trader_id, order_id]
            price_level.append(order)
            if side == BUY and price_index > self.bid_index:
                self.bid_index = price_index
            elif side == SELL and price_index < self.ask_index:
                self.ask_index = price_index
            return order
        else:
            return -1


    cpdef int get_ask(self):
        return self.get_price(self.ask_index)

    cpdef int get_bid(self):
        return self.get_price(self.bid_index)

    cpdef dict get_snap(self):
        cdef dict snap = {'asks': {}, 'bids': {}}
        for buy_index in self.get_indexes(BUY):
            snap['bids'][self.get_price(buy_index)] = self.price_level_list[buy_index].size
        for ask_index in self.get_indexes(SELL):
            snap['asks'][self.get_price(ask_index)] = self.price_level_list[ask_index].size
        return snap

    cpdef exist_buy_orders(self):
        return len(self.price_level_list[self.bid_index].orders) > 0

    cpdef exist_sell_orders(self):
        return len(self.price_level_list[self.ask_index].orders) > 0

    def get_indexes(self, int side):
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

    def get_prices(self, int side):
        for index in self.get_indexes(side):
            yield self.get_price(index)
        return

    cpdef get_quotes(self):
        ask, bid = self.get_ask(), self.get_bid()
        bid_v = self.price_level_list[self.bid_index].size
        ask_v = self.price_level_list[self.ask_index].size
        return np.array([ask, ask_v, bid, bid_v]) # Quotes : (ask, ask_v, bid, bid_v)


cdef class CyOrderBook:

    cdef long int order_id
    cdef dict orders
    cdef public CyListPriceLevels price_levels

    def __init__(self, price_level_type='cydeque', price_levels_type='cylist', **kwargs):

        self.orders = {}
        self.order_id = 0
        self.price_levels = CyListPriceLevels(price_level_type, **kwargs)

    def limit(self, long int price, int side, double size, int trader_id, str time):

        cdef list trades = []

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

                    self.price_levels.remove_level(BUY, bid)
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

    def cancel(self, int order_id):
        if order_id in self.orders:
            order = self.orders.pop(order_id)
            level = self.price_levels.get_level(order[O_SIDE], order[O_PRICE])
            level.delete(order)
            if not level.is_not_empty():
                self.price_levels.remove_level(order[O_SIDE], order[O_PRICE])

    def update(self, int order_id, double size):
        if order_id in self.orders:
            order = self.orders[order_id]
            price_level = self.price_levels.get_level(order[O_SIDE], order[O_PRICE])
            price_level.update(order, size - order[O_SIZE])

    def market_order(self, double size, int side, int trader_id, str time):

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

    def market_order_funds(self, double funds, int side, int trader_id, str time):
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


cpdef long int to_int(double price, int multiplier):
    return int((price+10e-8)*multiplier)



cpdef double to_float(int price, int tick_dec, int multiplier):
    return round(price/float(multiplier), tick_dec)

cdef class CyExternalMarket:

    cdef public CyOrderBook ob
    cdef double tick_size
    cdef int tick_dec
    cdef dict external_market_order_ids
    cdef public int multiplier
    cdef public object time

    def __init__(self, tick_size=0.01, ob_type='cy_order_book', price_level_type='cydeque',
                 price_levels_type='cylist', **kwargs):
        self.tick_size = tick_size
        self.tick_dec = int(np.log10(1 / tick_size))
        self.multiplier = 10**self.tick_dec
        self.ob = CyOrderBook(price_level_type='cydeque', price_levels_type='cylist', **kwargs)
        self.external_market_order_ids = {}
        self.time = '2000-1-1 00:00'


    def send_message(self, mess, external=False):
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
                        #traceback.print_exc()
                        #print(mess)
                        pass
                else:
                    try:
                        self.ob.cancel(mess.order_id)
                    except (ValueError, KeyError) as e:
                        # TODO Fix
                        #print(mess)
                        pass

        elif mess_type == 'change':
            if external:
                order_id = self.external_market_order_ids[mess.order_id]
                self.ob.update(order_id, mess.size)
            else:
                self.ob.update(mess.order_id, mess.size)

        return trades, order_in_book

    def fill_snap(self, snap):
        for message in snap['bids']:

            _, oib = self.ob.limit(to_int(float(message[SO_PRICE]), self.multiplier), BUY, float(message[SO_SIZE]), EXT_ID, self.time)
            if oib is not None:
                self.external_market_order_ids[message[SO_EXT_ID]] = oib[OIB_ID]

        for message in snap['asks']:

            price_int = to_int(float(message[SO_PRICE]), self.multiplier)

            _, oib = self.ob.limit(to_int(float(message[SO_PRICE]), self.multiplier), SELL, float(message[SO_SIZE]), EXT_ID, self.time)
            if oib is not None:
                self.external_market_order_ids[message[SO_EXT_ID]] = oib[OIB_ID]





