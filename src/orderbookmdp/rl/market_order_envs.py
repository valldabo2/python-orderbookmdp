import time
from collections.__init__ import deque

import gym
import numpy as np

from orderbookmdp.order_book.constants import BUY
from orderbookmdp.order_book.constants import Q_ASK
from orderbookmdp.order_book.constants import Q_BID
from orderbookmdp.order_book.constants import SELL
from orderbookmdp.order_book.constants import T_ID
from orderbookmdp.order_book.constants import T_PRICE
from orderbookmdp.order_book.constants import T_SIDE
from orderbookmdp.order_book.constants import T_SIZE
from orderbookmdp.order_book.constants import T_TIME
from orderbookmdp.order_book.order_types import market_message
from orderbookmdp.rl.abstract_envs import ExternalMarketEnv
from orderbookmdp.rl.app import get_portfolio_app
from orderbookmdp.rl.market_env import MarketEnv


class MarketOrderEnv(ExternalMarketEnv):
    """ An environment that only sends a market order of its full funds (BUY) or possession (SELL).
    """

    def __init__(self, **kwargs):
        super(MarketOrderEnv, self).__init__(**kwargs)
        self.first_render = True

    def get_messages(self, action: np.array) -> tuple:
        """ Returns a market order if possible. Actions are mapped 0=BUY, 1=SELL and 2=HOLD.
        Parameters
        ----------
        action : int

        Returns
        -------
        market_order : list

        """
        if action == 0:  # Buy Order
            if self.funds > 0:
                return [market_message(BUY, -1, self.T_ID, self.funds)]
        elif action == 1:  # Sell Order
            if self.possession > 0:
                return [market_message(SELL, self.possession, self.T_ID)]
        return []

    def get_reward(self, trades: list) -> tuple:
        """ Returns the reward as the percentage change in capital.

        :math:`capital = funds + possession*theoretical\_sell\_price`

        Where the theoretical sell price is the current bid.

        Parameters
        ----------
        trades : list

        Returns
        -------
        reward : float

        """
        for trade in trades:
            if trade[T_ID] == self.T_ID:

                if trade[T_SIDE] == BUY:
                    self.funds -= trade[T_SIZE] * trade[T_PRICE] / self.market.multiplier
                    self.possession += trade[T_SIZE]
                    self.trades_list.append([trade[T_TIME], trade[T_SIZE], trade[T_PRICE], BUY])
                else:
                    self.funds += trade[T_SIZE] * trade[T_PRICE] / self.market.multiplier
                    self.possession -= trade[T_SIZE]
                    self.trades_list.append([trade[T_TIME], trade[T_SIZE], trade[T_PRICE], SELL])

        theo_sell_price = self.quotes[Q_BID] / self.market.multiplier
        new_capital = self.funds + self.possession * theo_sell_price
        reward = (new_capital - self.capital) / self.capital
        self.capital = new_capital

        return reward

    def send_messages(self, messages: tuple) -> (list, dict, bool):
        trades = []
        info = {}
        for mess in messages:
            trades_, oib = self.market.send_message(mess)
            if len(trades_) > 0:
                trades.extend(trades_)

        trades_, done = self.run_until_next_quote_update()
        if len(trades_) > 0:
            trades.extend(trades_)

        return trades, done, info

    def get_private_variables(self) -> tuple:
        """ Returns the agents possession as private variable
        """
        return self.possession,

    def render(self, mode=None):
        """ Renders a dash app with the portfolio of the agent.

        """
        if self.first_render:
            self.render_app = get_portfolio_app()
            self.render_app.__setattr__('possession', deque(maxlen=self.price_n))
            self.render_app.__setattr__('funds', deque(maxlen=self.price_n))
            self.render_app.__setattr__('capital_change', deque(maxlen=self.price_n))

        MarketEnv.render(self)

        self.render_app.possession.append(self.possession)
        self.render_app.funds.append(self.funds)
        self.render_app.capital_change.append(self.capital / self.initial_funds)

        time.sleep(0.001)  # TODO investigate why a halt is n

    def seed(self, seed=None):
        pass

    def reset(self, market=None):
        """ Resets the environment.

        Also resets the render app with zero portfolio.

        """
        obs = ExternalMarketEnv.reset(self, market)

        theo_sell_price = self.quotes[Q_ASK]
        self.capital = self.funds + self.possession * theo_sell_price

        if self.render_app:
            self.render_app.possession = deque(maxlen=self.price_n)
            self.render_app.funds = deque(maxlen=self.price_n)
            self.render_app.capital_change = deque(maxlen=self.price_n)

        return obs, self.get_private_variables()

    @property
    def action_space(self):
        """ The action space is 0=BUY, 1==SELL, 0=HOLD"""
        return gym.spaces.Discrete(3)

    @property
    def observation_space(self):
        return gym.spaces.Box(low=-np.inf, high=np.inf, shape=(5,), dtype=np.float)


if __name__ == '__main__':
    env = MarketOrderEnv(max_sequence_skip=100, max_episode_time='2h', random_start=True)
    k = 0
    for i in range(5):
        obs = env.reset()
        done = False
        print('reset', env.market.time)
        while not done:
            action = env.action_space.sample()
            action = 2
            obs, reward, done, info = env.step(action)
            #env.render()
        print('stops', env.market.time)
    env.close()
