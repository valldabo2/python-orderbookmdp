from copy import deepcopy
import numpy as np
import pandas as pd
from more_itertools import spy

from orderbookmdp.order_book.constants import O_ID
from orderbookmdp.order_book.constants import O_PRICE
from orderbookmdp.order_book.constants import O_SIZE
from orderbookmdp.order_book.constants import T_OID
from orderbookmdp.order_book.constants import T_SIZE
from orderbookmdp.order_book.order_books import get_price_levels
from orderbookmdp.data.orderstream import orderstream
from orderbookmdp.rl.env_utils import quote_differs, quote_differs_pct
from orderbookmdp.rl.market_env import MarketEnv


class OrderTrackingEnv(MarketEnv):
    """ An abstract env that keeps track of all the orders the agent has in the order book.

    Attributes
    ----------
    orders_in_book_dict : dict
        All the orders in the book
    orders_in_book : PriceLevels

    """

    def __init__(self, **kwargs):
        """ Sets up the orders in book to keep track of.
        """
        super(OrderTrackingEnv, self).__init__(**kwargs)
        # self.orders_in_book = get_price_levels(market_setup['price_levels_type'], market_setup['price_level_type'])

        kwargs = deepcopy(self._market_setup)
        kwargs['price_levels_type'] = 'fast_avl'
        multiplier = 10 ** np.log10(1 / kwargs['tick_size'])
        if kwargs.get('max_price'):
            kwargs['max_price'] = int(kwargs['max_price'] * multiplier)
            kwargs['min_price'] = int(kwargs['min_price'] * multiplier)
        self.orders_in_book = get_price_levels(**kwargs)
        self.orders_in_book_dict = {}

    def update_order_tracking(self, matched_side, trade):
        """ Updates the order tracking.


        Parameters
        ----------
        matched_side
        trade

        Returns
        -------

        """
        # Updates order tracking
        matched_size = trade[T_SIZE]

        # print(self.orders_in_book_dict)
        try:  # The orders could be removed before this happens
            order = self.orders_in_book_dict[trade[T_OID]]
            price_level = self.orders_in_book.get_level(matched_side, order[O_PRICE])
            if matched_size < order[O_SIZE]:
                price_level.update(order, -matched_size)
            else:
                self.delete_order_from_level(matched_side, order, price_level)
        except KeyError as e:
            pass
            # print(e)

    def delete_order_from_level(self, side, order, price_level):
        price_level.delete(order)
        self.orders_in_book_dict.pop(order[O_ID])
        if price_level.is_empty():
            self.orders_in_book.remove_level(side, order[O_PRICE])


class ExternalMarketEnv(MarketEnv):
    """ An abstract env that handles orders from an external market.

    By handling orders from an external market it is possible to simulate an external market or add artificial messages
    to an external market at any point in time.

    Attributes
    ----------
    os : orderstream
        The orderstream that gives messages from the external market
    filled : bool
        If the env has been filled by a snapshot
    """

    def __init__(self, max_episode_time='10days',
                 order_paths='../../../data/feather/', snapshot_paths='../../../data/snap_json/', **kwargs):
        super(ExternalMarketEnv, self).__init__(**kwargs)
        self.os = orderstream(order_paths, snapshot_paths, **kwargs)
        self.filled = False
        self.snap = None
        self.max_episode_time_delta = pd.to_timedelta(max_episode_time).to_timedelta64()

    def run_until_next_quote_update(self) -> (list, bool):
        """ Sends messages from the external order stream until the quotes of the market has changed.

        Returns
        -------
        trades : list
        done : bool

        """
        trades = []
        done = False
        prev_quotes = self.market.ob.price_levels.get_quotes()
        for mess, snap in self.os:
            if snap is not None:  # Should return done and save snap to next reset
                self.snap = snap
                return [], True
            else:
                trades_, oib = self.market.send_message(mess, external=True)
                if len(trades_) > 0:
                    trades.extend(trades_)
                quotes = self.market.ob.price_levels.get_quotes()
                try:
                    if quote_differs_pct(prev_quotes, quotes):
                        self.quotes = quotes
                        return trades, done
                    elif np.datetime64(self.market.time) - self.start_time >= self.max_episode_time_delta:
                        return trades, True

                except ZeroDivisionError as e:  # TODO why zero in quotes?
                    return trades, done


    def reset(self, market=None):
        """ Resets the market with a new snapshot.

        Parameters
        ----------
        market : Market
            If to use a specific market instead of a newly created one.

        Returns
        -------

        observation : tuple
        """
        MarketEnv.reset(self, market=market)

        if self.snap is None:  # Initial filling
            mess, snap = self.os.__next__()
            prev_mess = mess
            while snap is None:
                mess, snap = self.os.__next__()
        else:
            snap = self.snap  # Fill from new snap

        next_message, self.os = spy(self.os, n=1)
        next_message = next_message[0][0]

        self.start_time = np.datetime64(next_message.time)
        self.market.time = next_message.time

        self.market.fill_snap(snap)
        self.quotes = self.market.ob.price_levels.get_quotes()

        obs = self.quotes

        return obs
