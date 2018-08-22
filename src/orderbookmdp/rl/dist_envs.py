import time
from copy import deepcopy

import gym
import numpy as np

from orderbookmdp.order_book.constants import BUY
from orderbookmdp.order_book.constants import O_ID
from orderbookmdp.order_book.constants import O_SIZE
from orderbookmdp.order_book.constants import OIB_ID
from orderbookmdp.order_book.constants import OIB_PRICE
from orderbookmdp.order_book.constants import OIB_SIDE
from orderbookmdp.order_book.constants import OIB_SIZE
from orderbookmdp.order_book.constants import Q_ASK
from orderbookmdp.order_book.constants import Q_BID
from orderbookmdp.order_book.constants import SELL
from orderbookmdp.order_book.constants import T_ID
from orderbookmdp.order_book.constants import T_PRICE
from orderbookmdp.order_book.constants import T_SIDE
from orderbookmdp.order_book.constants import T_SIZE
from orderbookmdp.order_book.constants import T_TIME
from orderbookmdp.order_book.constants import TC_ID
from orderbookmdp.order_book.order_books import get_price_levels
from orderbookmdp.order_book.order_types import cancel_message
from orderbookmdp.order_book.order_types import change_message
from orderbookmdp.order_book.order_types import limit_message
from orderbookmdp.order_book.price_level import SortedTradesLevel
from orderbookmdp.rl.abstract_envs import ExternalMarketEnv
from orderbookmdp.rl.abstract_envs import OrderTrackingEnv
from orderbookmdp.rl.app import get_dist_app
from orderbookmdp.rl.env_utils import get_pdf
from orderbookmdp.rl.market_env import MarketEnv


class SpreadEnv(ExternalMarketEnv, OrderTrackingEnv):
    """ An environment that puts a buy and a sell limit order on a certain tick distance from the bid and the ask.

    It keeps track of its orders and updates them accordingly.

    Attributes
    ----------
    min_order_capital : int
        The minimum capital to put an order of
    min_change_order_capital : int
        The minimum capital to change update an order to
    max_action : int
        The maximum tick distance to ever use
    default_action : np.array
        The default action always to start from

    """

    def __init__(self, **kwargs):
        super(SpreadEnv, self).__init__(**kwargs)
        self.trades = SortedTradesLevel(), SortedTradesLevel()

        mul = 10 ** np.log10(1 / self._market_setup['tick_size'])
        self.min_order_capital = (self.initial_funds / 100) * mul
        self.min_change_order_capital = (self.initial_funds / 100) * mul

        self.max_action = 50
        self.default_action = np.array([1, 1])

    def match(self, side: int, size: float, price: int) -> (int, float):
        """ Matches previous trades with new trades.

        The best buy orders (lowest price) are matched with the best sell orders (highest price). No match occurs if
        no trades of the other side (BUY/SELL) has occurred.

        The returned volume weighted spread vws is calculated as:
        :math:`vws=(sell_{price} - buy_{price})*size`

        Parameters
        ----------
        side : int
        size : float
        price : int

        Returns
        -------
        volume_weighted_spread : float
        size : float
            The remaining size of the trade that as occured.

        """
        volume_weighted_spread = 0
        while self.trades[side].is_not_empty() and size > 0:
            opposite_trade = self.trades[side].get_first()
            opposite_size = opposite_trade[T_SIZE]
            if size < opposite_size:
                volume_weighted_spread += (price - opposite_trade[T_PRICE]) * size
                self.trades[side].update(opposite_trade, -size)
                size = 0
                break
            else:
                # size >= opposite_trade[T_SIZE]
                volume_weighted_spread += (price - opposite_trade[T_PRICE]) * opposite_size
                self.trades[side].delete_first(opposite_trade)
                size -= opposite_size

        if side == SELL:  # Negate volume weighted spread if sold
            return -volume_weighted_spread, size
        else:
            return volume_weighted_spread, size

    def send_messages(self, messages: tuple) -> (list, dict, bool):
        trades = []
        info = {}
        for mess in messages:
            trades_, oib = self.market.send_message(mess)
            if oib is not None:
                order_in_book = self.orders_in_book.add_order(oib[OIB_SIDE], oib[OIB_PRICE], oib[OIB_SIZE],
                                                              self.T_ID, oib[OIB_ID])
                self.orders_in_book_dict[oib[OIB_ID]] = order_in_book
            if len(trades_) > 0:
                trades.extend(trades_)

        trades_, done = self.run_until_next_quote_update()
        if len(trades_) > 0:
            trades.extend(trades_)

        return trades, done, info

    def get_messages(self, action: np.array) -> tuple:
        action = (action * 10).astype(int)
        action = action + self.default_action
        action = np.clip(action, a_min=1, a_max=self.max_action)
        buy_dist, sell_dist = action

        ask, bid = self.quotes[Q_ASK], self.quotes[Q_BID]
        if ask > self.prev_ask:
            rel_bid_price = ask - 1
        else:
            rel_bid_price = bid

        if bid < self.prev_bid:
            rel_ask_price = bid + 1
        else:
            rel_ask_price = ask

        rel_ask_price += sell_dist

        self.prev_ask = ask
        self.prev_bid = bid

        buy_prices = [rel_bid_price - buy_dist]
        buy_sizes = [(self.funds * self.market.multiplier) / buy_prices[0]]
        sell_prices = [rel_ask_price + sell_dist]
        sell_sizes = [(self.funds * self.market.multiplier) / sell_prices[0]]

        if self.render_app:
            self.render_state = (action, buy_prices, buy_sizes, sell_prices, sell_sizes)

        return self.adjust_orders(buy_sizes, buy_prices, sell_sizes, sell_prices)

    def adjust_orders(self, buy_sizes, buy_prices, sell_sizes, sell_prices):
        """ Creates messages so that the orders in book are updated accordingly to the prices and sizes wanted.

        Creates limit orders, updates and cancellations based on the current order in books and the reuested prices and sizes.

        Parameters
        ----------
        buy_sizes : np.array
            Wanted buy prizes
        buy_prices : np.array
            Wanted buy sizes
        sell_sizes : np.array
            Wanted sell prizes
        sell_prices : np.array
            Wanted sell sizes

        Returns
        -------
        messages : list

        """
        messages = []

        buy_dict = dict(zip(buy_prices, buy_sizes))
        oib_buy_prices = list(p for p in self.orders_in_book.get_prices(BUY))
        for p in oib_buy_prices:
            price_level = self.orders_in_book.get_level(BUY, p)
            if p in buy_dict:
                size = price_level.size
                size_diff = buy_dict[p] - size

                if abs(p * size_diff) > self.min_change_order_capital:
                    if size_diff > 0:
                        messages.append(limit_message(BUY, size_diff, p, self.T_ID))
                    elif size_diff < 0:
                        size_diff = -size_diff

                        while price_level.is_not_empty():
                            order = price_level.get_last()
                            order_size = order[O_SIZE]
                            change_diff = min(size_diff, order_size)
                            # A order lies to small to compensate for the quantity diff, should then be removed:
                            if change_diff == order_size:
                                messages.append(cancel_message(order[O_ID]))
                                self.delete_order_from_level(BUY, order, price_level)
                                size_diff -= order_size
                                if size_diff == 0:
                                    break
                            # A order is large enough to be reduced in quantity
                            else:
                                messages.append(change_message(order[O_ID], size=order_size - change_diff))
                                price_level.update(order, -change_diff)
                                break
                buy_dict.pop(p)
            else:
                # Removes all orders on price level not active anymore
                for order in price_level.orders:
                    messages.append(cancel_message(order[O_ID]))
                    self.orders_in_book_dict.pop(order[O_ID])
                self.orders_in_book.remove_level(BUY, p)

        for price, size in buy_dict.items():
            if price * size > self.min_order_capital:
                messages.append(limit_message(BUY, size, price, self.T_ID))

        sell_dict = dict(zip(sell_prices, sell_sizes))
        oib_sell_prices = list(p for p in self.orders_in_book.get_prices(SELL))
        for p in oib_sell_prices:
            price_level = self.orders_in_book.get_level(SELL, p)
            if p in sell_dict:
                size = price_level.size
                size_diff = sell_dict[p] - size
                if abs(p * size_diff) > self.min_change_order_capital:
                    if size_diff > 0:
                        messages.append(limit_message(SELL, size_diff, p, self.T_ID))
                    elif size_diff < 0:
                        size_diff = -size_diff
                        while price_level.is_not_empty():
                            order = price_level.get_last()
                            order_size = order[O_SIZE]
                            change_diff = min(size_diff, order_size)
                            # A order lies to small to compensate for the quantity diff, should then be removed:
                            if change_diff == order_size:
                                messages.append(cancel_message(order[O_ID]))
                                self.delete_order_from_level(SELL, order, price_level)
                                size_diff -= order_size
                                if size_diff == 0:
                                    break
                            # A order is large enough to be reduced in quantity
                            else:
                                messages.append(change_message(order[O_ID], size=order_size - change_diff))
                                price_level.update(order, -change_diff)
                                break
                sell_dict.pop(p)
            else:
                # Removes all orders on price level not active anymore
                for order in price_level.orders:
                    messages.append(cancel_message(order[O_ID]))
                    self.orders_in_book_dict.pop(order[O_ID])
                self.orders_in_book.remove_level(SELL, p)

        for price, size in sell_dict.items():
            if price * size > self.min_order_capital:
                messages.append(limit_message(SELL, size, price, self.T_ID))

        return messages

    def get_private_variables(self) -> tuple:
        """ No private variables implemented yet.
        Returns
        -------
        private_variables : tuple
        """
        return ()

    def get_reward(self, trades: list) -> float:
        """ Calculates the reward based on the trades that has occured.

        The reward is calculated based on previous trades and the current trades. If a buy trade has occurred, the
        volume_weighted_spread :py:meth:`match` is calculated from previous sell trades. Vice versa for a sell trade.

        """
        reward = 0
        for trade in trades:
            # sent order matched and not against oneself
            if trade[T_ID] == self.T_ID and trade[TC_ID] != self.T_ID:
                # Sent buy order and got matched, gets spread from sell side
                if trade[T_SIDE] == BUY:
                    self.trades_list.append([trade[T_TIME], trade[T_SIZE], trade[T_PRICE], BUY])
                    # Match against previous sell trades
                    r, rem_size = self.match(SELL, trade[T_SIZE], trade[T_PRICE])
                    r += reward
                    if rem_size > 0:
                        trade = list(trade)
                        trade[T_SIZE] = rem_size
                        self.trades[BUY].append(trade)
                # Sent sell order and got matched, gets spread from buy side
                else:
                    self.trades_list.append([trade[T_TIME], trade[T_SIZE], trade[T_PRICE], SELL])
                    # Match against previous buy trades
                    r, rem_size = self.match(BUY, trade[T_SIZE], trade[T_PRICE])
                    reward += r
                    if rem_size > 0:
                        trade = list(trade)
                        trade[T_SIZE] = rem_size
                        self.trades[SELL].append(trade)

            # someone matched on own order in book and not against oneself, TC = trade counterparty
            elif trade[TC_ID] == self.T_ID and trade[T_ID] != self.T_ID:
                # Someone bought on our sell order, we got a sell trade, matches against old buy trades
                if trade[T_SIDE] == BUY:
                    self.trades_list.append([trade[T_TIME], trade[T_SIZE], trade[T_PRICE], SELL])
                    # Since someone bought on our sell order in the book, we need to remove the matched size from our
                    # order tracking
                    self.update_order_tracking(SELL, trade)
                    # Match against previous sell trades
                    reward, rem_size = self.match(BUY, trade[T_SIZE], trade[T_PRICE])
                    if rem_size > 0:
                        trade = list(trade)
                        trade[T_SIZE] = rem_size
                        self.trades[SELL].append(trade)

                # Someone sold to our buy trade, we got a buy trade, matches against old sell trades
                else:
                    self.trades_list.append([trade[T_TIME], trade[T_SIZE], trade[T_PRICE], BUY])
                    # Since someone sold on our buy order in the book, we need to remove the matched size from our
                    # order tracking
                    self.update_order_tracking(BUY, trade)

                    reward, rem_size = self.match(SELL, trade[T_SIZE], trade[T_PRICE])
                    if rem_size > 0:
                        trade = list(trade)
                        trade[T_SIZE] = rem_size
                        self.trades[BUY].append(trade)

        return reward / self.market.multiplier

    def render(self, mode='human'):

        if self.first_render:
            self.render_app = get_dist_app()
            self.render_app.__setattr__('buyorders', {})
            self.render_app.__setattr__('sellorders', {})

        MarketEnv.render(self)

        try:
            self.render_app.render_state = self.render_state
        except Exception as e:
            print(e)

        order_snap = self.orders_in_book.get_snap()
        self.render_app.buyorders = order_snap['bids']
        self.render_app.sellorders = order_snap['asks']

        time.sleep(0.0001)  # TODO investigate why a halt is needed for the flask app in other thread

    def seed(self, seed=None):
        pass

    @property
    def observation_space(self):
        return gym.spaces.Box(low=-np.inf, high=np.inf, shape=(4,), dtype=np.float)

    @property
    def action_space(self):
        """ The action space is :math:`buy_{distance}, sell_{distance} = action`

        The action are distances in ticks:

        :math:`buy_{distance}, sell_{distance} = action[0], action[1]`

        Sets the buy limit order with a distance from the bid:

        :math:`buy_{price} = bid - buy_{distance}`

        And the sell limit order with a distance from the ask:

        :math:`sell_{price} = ask + sell_{distance}`

        """
        return gym.spaces.Box(low=-0.1, high=2, shape=(2,), dtype=np.float)

    def reset(self, market=None):
        obs = super(SpreadEnv, self).reset(market)
        # self.orders_in_book = get_price_levels(market_setup['price_levels_type'], market_setup['price_level_type'])
        kwargs = deepcopy(self._market_setup)
        kwargs['price_levels_type'] = 'fast_avl'
        if kwargs.get('max_price'):
            kwargs['max_price'] = int(kwargs['max_price'] * self.market.multiplier)
            kwargs['min_price'] = int(kwargs['min_price'] * self.market.multiplier)
        self.orders_in_book = get_price_levels(**kwargs)
        self.orders_in_book_dict = {}
        self.trades = SortedTradesLevel(), SortedTradesLevel()

        self.prev_ask = self.quotes[Q_ASK]
        self.prev_bid = self.quotes[Q_BID]

        if self.render_app:
            self.render_app.__setattr__('buyorders', {})
            self.render_app.__setattr__('sellorders', {})

        return obs


class DistEnv(SpreadEnv):
    """ A extension of the :py:class:`SpreadEnv` that has a full distribution of orders.

    Has one distribution of buy orders from bid and a certain amount of tick sizes downwards.
    Vice versa for the sell orders. One example distribution is to place the orders according to a
    `beta distribution <https://en.wikipedia.org/wiki/Beta_distribution>`_.


    Attributes
    ----------
    n_tick_levels : int
        The number of tick levels to put orders away from the anchor price, bid in buy case.
    n_price_levels : int
        The number of price levels to put orders in. Must be smaller than the number of tick levels.

    """

    def __init__(self, pdf_type='beta', **kwargs):

        super(DistEnv, self).__init__(**kwargs)

        self.max_action, self.default_action, self.dist_pdf = get_pdf(pdf_type)
        self.n_tick_levels = 40
        self.n_price_levels = 10
        self.x = np.linspace(0.01, 1 - 0.01, self.n_price_levels)
        self.x_shift = np.arange(start=0, stop=self.n_tick_levels, step=int(self.n_tick_levels / self.n_price_levels),
                                 dtype=np.int)

    def funds_dist(self, a, b):
        probs = self.dist_pdf(self.x, a, b)
        probs /= probs.sum()
        funds = self.funds / 2
        funds_dist = probs * funds
        return funds_dist

    def get_messages(self, action: np.array) -> tuple:
        action = action + self.default_action
        action = np.clip(action, a_min=0.01, a_max=self.max_action)
        buy_alpha, buy_beta, sell_alpha, sell_beta = action
        buy_funds_dist = self.funds_dist(buy_alpha, buy_beta)
        sell_funds_dist = self.funds_dist(sell_alpha, sell_beta)

        ask, bid = self.quotes[Q_ASK], self.quotes[Q_BID]
        if ask > self.prev_ask:
            rel_bid_price = ask - 1
        else:
            rel_bid_price = bid

        if bid < self.prev_bid:
            rel_ask_price = bid + 1
        else:
            rel_ask_price = ask

        self.prev_ask = ask
        self.prev_bid = bid

        buy_prices = int(rel_bid_price) - self.x_shift
        buy_sizes = buy_funds_dist * self.market.multiplier / buy_prices
        sell_prices = int(rel_ask_price) + self.x_shift
        sell_sizes = sell_funds_dist * self.market.multiplier / sell_prices

        if self.render_app:
            self.render_state = (action, buy_prices, buy_sizes, sell_prices, sell_sizes)

        return self.adjust_orders(buy_sizes, buy_prices, sell_sizes, sell_prices)

    @property
    def action_space(self):
        """ The action space is the buy and sell distributions beta and alpha.

        :math:`buy_{\\alpha}, buy_{\\beta}, sell_{\\alpha}, sell_{\\beta} = action`

        """
        return gym.spaces.Box(low=-2.9, high=10, shape=(4,), dtype=np.float)


if __name__ == '__main__':
    env = DistEnv(max_episode_time='2h', max_sequence_skip=100, random_start=True)
    for i in range(3):
        obs = env.reset()
        done = False
        print('reset', env.market.time)
        while not done:
            action = env.action_space.sample()
            obs, reward, done, info = env.step(action)
            env.render()
        print('done', env.market.time)

    env.close()
