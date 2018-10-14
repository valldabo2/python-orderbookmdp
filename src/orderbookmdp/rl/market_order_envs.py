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
import logging


class MarketOrderEnv(ExternalMarketEnv):
    """ An environment that only sends a market order of its full funds (BUY) or possession (SELL).
    """
    def __init__(self, **kwargs):
        super(MarketOrderEnv, self).__init__(**kwargs)
        self.first_render = True
        self.possession = 0
        self.init_bp = False

        self.opt_funds = self.funds
        self.opt_poss = self.possession
        self.opt_capital = self.capital

    def get_messages(self, action: np.array) -> tuple:
        """ Returns a market order if possible. Actions are mapped 0=BUY, 1=SELL and 2=HOLD.
        Parameters
        ----------
        action : int

        Returns
        -------
        market_order : list

        """

        self.action = action
        if action == 0:  # Sell Order
            if self.possession > 0:
                return [market_message(SELL, self.possession, self.T_ID)]
        elif action == 2:  # Buy Order
            if self.funds > 0:
                return [market_message(BUY, -1, self.T_ID, self.funds)]
        return []

    def get_reward(self, trades: list, done) -> tuple:
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

        #if done and self.capital / self.initial_funds < self.min_capital_pct:
        #    return -1

        for trade in trades:
            if trade[T_ID] == self.T_ID:
                if trade[T_SIDE] == BUY:
                    self.funds -= trade[T_SIZE] * trade[T_PRICE] / self.market.multiplier
                    self.possession += trade[T_SIZE]*(1-self.taker_fee)
                    self.trades_list.append([trade[T_TIME], trade[T_SIZE], trade[T_PRICE], BUY])
                else:
                    self.funds += trade[T_SIZE] * (1-self.taker_fee) * trade[T_PRICE] / self.market.multiplier
                    self.possession -= trade[T_SIZE]
                    self.trades_list.append([trade[T_TIME], trade[T_SIZE], trade[T_PRICE], SELL])

        theo_sell_price = self.quotes[Q_BID] / self.market.multiplier
        new_capital = self.funds + self.possession * theo_sell_price
        reward = (new_capital - self.capital) / self.capital
        self.capital = new_capital

        self.update_opt_cap()

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

        if done:
            info['cap'] = self.capital/self.initial_funds
            info['opt_cap'] = self.opt_capital / self.initial_funds

        return trades, done, info

    def get_private_variables(self) -> tuple:
        """ Returns the agents possession as private variable
        """
        return self.possession, self.capital/self.initial_funds - 1

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

        time.sleep(0.005)  # TODO investigate why a halt is n

    def seed(self, seed=None):
        pass

    def reset(self, market=None):
        """ Resets the environment.

        Also resets the render app with zero portfolio.

        """
        obs = ExternalMarketEnv.reset(self, market)

        self.funds = self.initial_funds
        self.possession = 0

        bid = self.quotes[Q_BID]/self.market.multiplier
        self.capital = self.funds + self.possession * bid
        ask = self.quotes[Q_ASK] / self.market.multiplier
        self.prev_buying_power = self.capital / ask

        if not self.init_bp:
            self.init_buying_power = self.prev_buying_power
            self.init_bp = True

        if self.render_app:
            self.render_app.possession = deque(maxlen=self.price_n)
            self.render_app.funds = deque(maxlen=self.price_n)
            self.render_app.capital_change = deque(maxlen=self.price_n)


        self.opt_funds = self.funds
        self.opt_poss = self.possession
        self.opt_capital = self.capital

        self.memory_ask = ask
        self.memory_bid = bid

        return obs, self.get_private_variables()

    def update_opt_cap(self):
        bid = self.quotes[Q_BID] / self.market.multiplier
        ask = self.quotes[Q_ASK] / self.market.multiplier

        if self.opt_poss == 0 and bid - self.memory_ask > 0:
            self.opt_poss += self.opt_funds / self.memory_ask
            self.opt_funds = 0
            self.memory_ask = ask

        elif self.memory_bid - ask > 0:
            self.opt_funds += self.opt_poss * self.memory_bid
            self.opt_poss = 0
            self.memory_bid = bid

        self.memory_ask = min(self.memory_ask, ask)
        self.memory_bid = max(self.memory_bid, bid)

        self.opt_capital = self.opt_funds + self.opt_poss*bid

    @property
    def action_space(self):
        """ The action space is 0=BUY, 1==SELL, 0=HOLD"""
        return gym.spaces.Discrete(3)

    @property
    def observation_space(self):
        return gym.spaces.Box(low=-np.inf, high=np.inf, shape=(6,), dtype=np.float)


class MarketOrderEnvBuySell(MarketOrderEnv):
    def get_messages(self, action: np.array) -> tuple:
        """ Returns a market order if possible. Actions are mapped 0=BUY, 1=SELL and 2=HOLD.
        Parameters
        ----------
        action : int

        Returns
        -------
        market_order : list

        """

        self.action = action
        if action == BUY:  # Sell Order
            if self.funds > 0:
                return [market_message(BUY, -1, self.T_ID, self.funds)]
        elif action == SELL:  # Buy Order
            if self.possession > 0:
                return [market_message(SELL, self.possession, self.T_ID)]
        return []

    @property
    def action_space(self):
        """ The action space is 0=BUY, 1==SELL"""
        return gym.spaces.Discrete(2)


class MarketOrderEnvCumReturn(MarketOrderEnv):
    """
    Extends the Market Order Enviroment because it uses the cumulative return instead of the return as the reward.

    Attributes
    ----------
    cum_return : float
        The cumulative return
    """
    def __init__(self, **kwargs):
        super(MarketOrderEnvCumReturn, self).__init__(**kwargs)
        self.cum_return = 1

    def get_reward(self, trades: list, done):
        """ The reward is the cumulative return.

        :math:`reward_t = cum\_return_t - 1`

        Where cum_return is:

        :math:`cum\_return_t = 1*\prod_{i=1}^{t} 1+return_t`

        """
        return_ = MarketOrderEnv.get_reward(self, trades)
        self.cum_return = self.cum_return*(1+return_)
        reward = self.cum_return - 1

        self.update_opt_cap()

        return reward

    def reset(self, market=None):
        obs = MarketOrderEnv.reset(self, market)
        self.cum_return = 1
        return obs

    def get_private_variables(self):
        """

        Returns
        -------
        possession : float
        cum_return : float
        """
        return self.possession, self.cum_return

    @property
    def observation_space(self):
        return gym.spaces.Box(low=-np.inf, high=np.inf, shape=(6,), dtype=np.float)


class MarketOrderEnvAdjustment(MarketOrderEnv):
    """
    Extends the Market Order Enviroment because it uses a adjusted return instead of the return as the reward.

    """
    def __init__(self, **kwargs):
        super(MarketOrderEnvAdjustment, self).__init__(**kwargs)

    def get_reward(self, trades: list, done):
        """ The reward is the adjusted return.

        :math:`reward_t = return_t * \frac{cap_t}{cap_0}`

        """
        return_ = MarketOrderEnv.get_reward(self, trades)
        return_ *= self.capital/self.initial_funds

        self.update_opt_cap()

        return return_

    def get_private_variables(self):
        """

        Returns
        -------
        possession : float
        cum_return : float
        """
        return self.possession, self.capital/self.initial_funds

    @property
    def observation_space(self):
        return gym.spaces.Box(low=-np.inf, high=np.inf, shape=(6,), dtype=np.float)


class MarketOrderEnvBuyingPower(MarketOrderEnv):

    def get_reward(self, trades: list, done) -> tuple:
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
                    self.possession += trade[T_SIZE]*(1-self.taker_fee)
                    self.trades_list.append([trade[T_TIME], trade[T_SIZE], trade[T_PRICE], BUY])
                else:
                    self.funds += trade[T_SIZE] * (1-self.taker_fee) * trade[T_PRICE] / self.market.multiplier
                    self.possession -= trade[T_SIZE]
                    self.trades_list.append([trade[T_TIME], trade[T_SIZE], trade[T_PRICE], SELL])

        theo_sell_price = self.quotes[Q_BID] / self.market.multiplier
        self.capital = self.funds + self.possession * theo_sell_price
        theo_buy_price = self.quotes[Q_ASK] / self.market.multiplier
        buying_power = self.capital / theo_buy_price
        reward = (buying_power - self.prev_buying_power)/self.prev_buying_power
        self.prev_buying_power = buying_power

        self.update_opt_cap()

        return reward

    def get_private_variables(self):
        """

        Returns
        -------
        possession : float
        cum_return : float
        """
        return self.possession, self.prev_buying_power/self.init_buying_power

    @property
    def observation_space(self):
        return gym.spaces.Box(low=-np.inf, high=np.inf, shape=(6,), dtype=np.float)


class MarketOrderEnvEndReward(MarketOrderEnv):

    def get_reward(self, trades: list, done) -> tuple:
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
                    self.possession += trade[T_SIZE]*(1-self.taker_fee)
                    self.trades_list.append([trade[T_TIME], trade[T_SIZE], trade[T_PRICE], BUY])
                else:
                    self.funds += trade[T_SIZE] * (1-self.taker_fee) * trade[T_PRICE] / self.market.multiplier
                    self.possession -= trade[T_SIZE]
                    self.trades_list.append([trade[T_TIME], trade[T_SIZE], trade[T_PRICE], SELL])

        theo_sell_price = self.quotes[Q_BID] / self.market.multiplier
        new_capital = self.funds + self.possession * theo_sell_price
        self.capital = new_capital

        self.update_opt_cap()

        if done:
            return self.capital/self.initial_funds - 1
        else:
            return 0


class MarketOrderEnvFunds(MarketOrderEnv):

    def get_reward(self, trades: list, done) -> tuple:
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
                    self.possession += trade[T_SIZE]*(1-self.taker_fee)
                    self.trades_list.append([trade[T_TIME], trade[T_SIZE], trade[T_PRICE], BUY])
                else:
                    self.funds += trade[T_SIZE] * (1-self.taker_fee) * trade[T_PRICE] / self.market.multiplier
                    self.possession -= trade[T_SIZE]
                    self.trades_list.append([trade[T_TIME], trade[T_SIZE], trade[T_PRICE], SELL])

        sp = self.quotes[Q_BID] / self.market.multiplier
        prev_sp = self.prev_quotes[Q_BID] / self.market.multiplier
        bp = self.quotes[Q_ASK] / self.market.multiplier
        prev_bp = self.prev_quotes[Q_ASK] / self.market.multiplier

        # Possible capital increase/decrease if bought all funds
        p_cap = (self.funds/prev_bp)*(sp - prev_sp)
        # Possible chance of getting a better price at next timestep, buy price when down
        p_buy = (self.funds/sp)*(bp - prev_bp)

        new_capital = self.funds + self.possession * sp
        reward = (new_capital - p_cap - p_buy - self.capital)/self.capital
        self.capital = self.possession*sp + self.funds

        self.update_opt_cap()

        return reward

    def get_private_variables(self) -> tuple:
        """ Returns the agents possession as private variable
        """
        return self.possession, self.quotes[Q_ASK] - self.quotes[Q_BID]

    @property
    def observation_space(self):
        return gym.spaces.Box(low=-np.inf, high=np.inf, shape=(6,), dtype=np.float)


class MarketOrderEnvCritic(MarketOrderEnv):
    def get_reward(self, trades: list, done):
        for trade in trades:
            if trade[T_ID] == self.T_ID:
                if trade[T_SIDE] == BUY:
                    self.funds -= trade[T_SIZE] * trade[T_PRICE] / self.market.multiplier
                    self.possession += trade[T_SIZE]*(1-self.taker_fee)
                    self.trades_list.append([trade[T_TIME], trade[T_SIZE], trade[T_PRICE], BUY])
                else:
                    self.funds += trade[T_SIZE] * (1-self.taker_fee) * trade[T_PRICE] / self.market.multiplier
                    self.possession -= trade[T_SIZE]
                    self.trades_list.append([trade[T_TIME], trade[T_SIZE], trade[T_PRICE], SELL])

        sp, bp = self.quotes[Q_BID]/self.market.multiplier, self.quotes[Q_ASK]/self.market.multiplier
        prev_sp, prev_bp = self.prev_quotes[Q_BID]/self.market.multiplier, self.prev_quotes[Q_ASK]/self.market.multiplier

        self.capital = self.possession * sp + self.funds

        dsp = sp - prev_sp
        dbp = bp - prev_bp

        reward = -1
        if self.action == 0: #Sell
            if dsp < 0:
                reward = 1
        elif self.action == 2: # BUY
            if dsp > 0:
                reward = 1
        else: # HOLD
            if self.funds == 0 and dsp > 0:
                reward = 1
            if self.possession == 0 and dsp < 0:
                reward = 1

        self.update_opt_cap()
        return reward


class MarketOrderEnvOpt(MarketOrderEnv):
    def get_reward(self, trades: list, done):
        for trade in trades:
            if trade[T_ID] == self.T_ID:
                if trade[T_SIDE] == BUY:
                    self.funds -= trade[T_SIZE] * trade[T_PRICE] / self.market.multiplier
                    self.possession += trade[T_SIZE] * (1 - self.taker_fee)
                    self.trades_list.append([trade[T_TIME], trade[T_SIZE], trade[T_PRICE], BUY])
                else:
                    self.funds += trade[T_SIZE] * (1 - self.taker_fee) * trade[T_PRICE] / self.market.multiplier
                    self.possession -= trade[T_SIZE]
                    self.trades_list.append([trade[T_TIME], trade[T_SIZE], trade[T_PRICE], SELL])

        sp = self.quotes[Q_BID] / self.market.multiplier

        prev_cap = self.capital
        self.capital = self.possession * sp + self.funds
        cap_change = self.capital - prev_cap

        prev_opt_cap = self.opt_capital
        self.update_opt_cap()
        opt_cap_change = self.opt_capital - prev_opt_cap

        reward = (cap_change-opt_cap_change) / self.initial_funds

        return reward

    def get_private_variables(self):
        """

        Returns
        -------
        possession : float
        cum_return : float
        """
        return self.funds/self.capital, (self.capital - self.opt_capital)/self.opt_capital

    @property
    def observation_space(self):
        return gym.spaces.Box(low=-np.inf, high=np.inf, shape=(6,), dtype=np.float)


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

    env = MarketOrderEnvBuySell(taker_fee=0.002,  min_capital_pct=0.1,
                                    max_sequence_skip=10000, max_episode_time='6hours', random_start=True)
    t = time.time()
    for i in range(10):
        k = 0
        obs = env.reset()
        print(obs)
        done = False
        rewards = 0
        print('reset', env.market.time)
        while not done:
            action = env.action_space.sample()
            #action = 0
            # if k % 2 == 0:
            #     action = 0
            # else:
            #     action = 1
            obs, reward, done, info = env.step(action)
            rewards += reward
            #env.render()
            k += 1
            if k % 100000 == 0:
                print(env.market.time, reward, env.capital/env.initial_funds, env.opt_capital/env.initial_funds)
        print(env.market.time, reward, env.capital / env.initial_funds, env.opt_capital / env.initial_funds)

        print('stops time:{}, total_reward:{:.2f} steps:{}'.format( env.market.time, rewards, k))

    env.close()
    print('time', time.time() - t)
