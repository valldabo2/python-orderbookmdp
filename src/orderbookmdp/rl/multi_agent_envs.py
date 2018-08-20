import time
from datetime import datetime

import gym
import numpy as np

from orderbookmdp.order_book.constants import BUY
from orderbookmdp.order_book.constants import OIB_ID
from orderbookmdp.order_book.constants import OIB_PRICE
from orderbookmdp.order_book.constants import OIB_SIDE
from orderbookmdp.order_book.constants import OIB_SIZE
from orderbookmdp.order_book.constants import Q_ASK
from orderbookmdp.order_book.constants import Q_BID
from orderbookmdp.order_book.constants import SELL
from orderbookmdp.order_book.constants import TC_ID
from orderbookmdp.order_book.constants import T_ID
from orderbookmdp.order_book.constants import T_PRICE
from orderbookmdp.order_book.constants import T_SIDE
from orderbookmdp.order_book.constants import T_SIZE
from orderbookmdp.order_book.order_types import limit_message
from orderbookmdp.rl.app import get_multienv_app
from orderbookmdp.rl.dist_envs import DistEnv
from orderbookmdp.rl.dist_envs import SpreadEnv
from orderbookmdp.rl.market_env import MarketEnv
from orderbookmdp.rl.market_order_envs import MarketOrderEnv

order_tracking_types = {'dist', 'spread'}
matching_order_envs = {'market'}


class MultiAgentOrderEnv(MarketEnv):
    """An environment that hosts multiple independent agents.
        Agents are identified by (string) agent ids. Note that these "agents" here
        are not to be confused with RLlib agents.
        Examples:
            >>> env = MyMultiAgentEnv()
            >>> obs = env.reset()
            >>> print(obs)
            {
                "car_0": [2.4, 1.6],
                "car_1": [3.4, -3.2],
                "traffic_light_1": [0, 3, 5, 1],
            }
            >>> obs, rewards, dones, infos = env.step(
                action_dict={
                    "car_0": 1, "car_1": 0, "traffic_light_1": 2,
                })
            >>> print(rewards)
            {
                "car_0": 3,
                "car_1": -1,
                "traffic_light_1": 0,
            }
            >>> print(dones)
            {
                "car_0": False,
                "car_1": True,
                "__all__": False,
            }
        """

    def __init__(self, agent_list, random_agent_list=[], market_type='cyext',
                 market_setup=dict(tick_size=0.01, ob_type='cy_order_book', order_level_type='cydeque',
                                   order_levels_type='cylist', max_price=150, min_price=50), initial_funds=10000,
                 episode_seconds=60):
        super(MultiAgentOrderEnv, self).__init__(market_type, market_setup, initial_funds, T_ID=None)

        self.trader_id = 1

        # Init random spread
        random_agent_list.append('spread_-1')
        tot_agent_list = agent_list + random_agent_list

        self.agents_dict = self.setup_agent_dict(tot_agent_list)
        self.random_agents_list = random_agent_list
        self.agents_list = agent_list

        self.market_order_random_agents = [agent_id for agent_id in random_agent_list if
                                           agent_id in matching_order_envs]
        self.non_market_order_random_agents = [agent_id for agent_id in random_agent_list if
                                               agent_id not in matching_order_envs]

        self.market_order_agents = [agent_id for agent_id in agent_list if agent_id in matching_order_envs]
        self.non_market_order_agents = [agent_id for agent_id in random_agent_list if
                                        agent_id not in matching_order_envs]

        self.episode_seconds = episode_seconds

        self.traders_type = {}
        for agent_id in tot_agent_list:
            agent_type, trader_id = agent_id.split('_')
            self.traders_type[int(trader_id)] = agent_type

    def setup_agent_dict(self, agent_list: list):
        agents_dict = {}
        for agent_id in agent_list:
            agents_dict[agent_id] = {}
            agent_type, trader_id = agent_id.split('_')
            if agent_type == 'dist':
                agents_dict[agent_id]['env'] = DistEnv(T_ID=int(trader_id), market_type=self._market_type,
                                                       market_setup=self._market_setup)
                agents_dict[agent_id]['env'].snap = {'asks': [], 'bids': []}
            elif agent_type == 'spread':
                agents_dict[agent_id]['env'] = SpreadEnv(T_ID=int(trader_id), market_type=self._market_type,
                                                         market_setup=self._market_setup)
                agents_dict[agent_id]['env'].snap = {'asks': [], 'bids': []}
            elif agent_type == 'market':
                agents_dict[agent_id]['env'] = MarketOrderEnv(T_ID=int(trader_id), market_type=self._market_type,
                                                              market_setup=self._market_setup)
                agents_dict[agent_id]['env'].snap = {'asks': [], 'bids': []}
            else:
                raise NotImplementedError('Agent_type:{} is not implemented'.format(agent_id))

        return agents_dict

    def step(self, action_dict):
        """Run one timestep of the environment's dynamics. When end of
        episode is reached, you are responsible for calling `reset()`
        to reset this environment's state.
        Accepts an action and returns a tuple (observation, reward, done, info).
        Args:
            action (object): an action provided by the environment
        Returns:
            observation (object): agent's observation of the current environment
            reward (float) : amount of reward returned after previous action
            done (boolean): whether the episode has ended, in which case further step() calls will return undefined results
            info (dict): contains auxiliary diagnostic information (helpful for debugging, and sometimes learning)
        """
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
        trades = []
        info = {}
        done = {}
        obs = {}

        ask, bid = self.quotes[Q_ASK], self.quotes[Q_BID]
        if ask == self.market.ob.price_levels.max_price:
            self.init_sell('spread_-1')
            self.quotes = self.market.ob.price_levels.get_quotes()
        if bid == self.market.ob.price_levels.min_price:
            self.init_buy('spread_-1')
            self.quotes = self.market.ob.price_levels.get_quotes()

        for agent_id in self.random_agents_list:
            if self.agents_dict[agent_id]['env'].capital <= 0:  # Refills random agents capital
                self.agents_dict[agent_id]['env'].capital = self.agents_dict[agent_id]['env'].initial_funds
            action = self.agents_dict[agent_id]['env'].action_space.sample()
            messages = self.agents_dict[agent_id]['env'].get_messages(action)

            self.market.time = datetime.utcnow().strftime("%Y-%m-%-d %H:%M:%S.%f")
            trades_, done_, info_ = self.send_messages(messages)
            trades.extend(trades_)

        for agent_id in self.agents_list:
            action = action_dict[agent_id]
            messages = self.agents_dict[agent_id]['env'].get_messages(action)
            self.market.time = datetime.utcnow().strftime("%Y-%m-%-d %H:%M:%S.%f")
            trades_, done_, info_ = self.send_messages(messages)
            trades.extend(trades_)
            info[agent_id] = info_

        reward = self.get_reward(trades)

        self.quotes = self.market.ob.price_levels.get_quotes()
        for agent_id in self.agents_list:
            done[agent_id] = self.agents_dict[agent_id]['env'].capital <= 0
            obs[agent_id] = (self.quotes, self.agents_dict[agent_id]['env'].get_private_variables())

        done['__all__'] = time.time() - self.init_time > self.episode_seconds
        self.trades_list.extend(trades)

        return obs, reward, done, info

    def send_messages(self, messages: tuple) -> (list, dict, bool):
        trades = []
        for mess in messages:
            trades_, oib = self.market.send_message(mess)
            if oib is not None:
                agent_id = self.traders_type[mess.trader_id] + '_' + str(mess.trader_id)
                order_in_book = self.agents_dict[agent_id]['env'].orders_in_book.add_order(oib[OIB_SIDE],
                                                                                           oib[OIB_PRICE],
                                                                                           oib[OIB_SIZE],
                                                                                           self.T_ID, oib[OIB_ID])
                self.agents_dict[agent_id]['env'].orders_in_book_dict[oib[OIB_ID]] = order_in_book
            if len(trades_) > 0:
                trades.extend(trades_)

        return trades, {}, False

    def reset(self):
        MarketEnv.reset(self)

        agent_list = list(self.agents_dict.keys())
        agent_list.remove('spread_-1')
        # init limits
        self.agents_dict['spread_-1']['env'].reset(self.market)
        self.init_limits()

        for agent_id in agent_list:
            self.agents_dict[agent_id]['env'].reset(self.market)

        self.market.time = datetime.utcnow().strftime("%Y-%m-%-d %H:%M:%S.%f")

        self.quotes = self.market.ob.price_levels.get_quotes()
        obs = self.get_obs()

        self.init_time = time.time()

        return obs

    def init_limits(self):
        agent_id = 'spread_-1'
        self.init_buy(agent_id)
        self.init_sell(agent_id)

    def init_sell(self, agent_id):
        trades, oib = self.market.send_message(limit_message(SELL, 1, (100 + 1) * self.market.multiplier, -1))
        order_in_book = self.agents_dict[agent_id]['env'].orders_in_book.add_order(oib[OIB_SIDE], oib[OIB_PRICE],
                                                                                   oib[OIB_SIZE],
                                                                                   self.T_ID, oib[OIB_ID])
        self.agents_dict[agent_id]['env'].orders_in_book_dict[oib[OIB_ID]] = order_in_book

    def init_buy(self, agent_id):
        trades, oib = self.market.send_message(limit_message(BUY, 1, (100 - 1) * self.market.multiplier, -1))
        order_in_book = self.agents_dict[agent_id]['env'].orders_in_book.add_order(oib[OIB_SIDE], oib[OIB_PRICE],
                                                                                   oib[OIB_SIZE],
                                                                                   self.T_ID, oib[OIB_ID])
        self.agents_dict[agent_id]['env'].orders_in_book_dict[oib[OIB_ID]] = order_in_book

    def get_messages(self, action_dict: dict) -> tuple:
        pass

    @staticmethod
    def diff(new, old):
        return (new - old) / old

    def get_reward(self, trades: list, reward_dict=None) -> tuple:
        prev_capital_dict = {agent_id: self.agents_dict[agent_id]['env'].capital for agent_id in
                             self.agents_dict.keys()}

        for trade in trades:
            t_id_ = trade[T_ID]
            tc_id_ = trade[TC_ID]
            t_type = self.traders_type[t_id_]
            tc_type = self.traders_type[tc_id_]
            t_id = t_type + '_' + str(t_id_)
            tc_id = tc_type + '_' + str(tc_id_)
            t = self.agents_dict[t_id]['env']
            tc = self.agents_dict[tc_id]['env']

            order_cost = trade[T_PRICE] * trade[T_SIZE] / self.market.multiplier

            # Trader bought
            if trade[T_SIDE] == BUY:
                t.funds -= order_cost
                t.possession += trade[T_SIZE]

                tc.funds += order_cost
                tc.possession -= trade[T_SIZE]

                # Update order tracking of certain agent types
                if tc_type in order_tracking_types:
                    tc.update_order_tracking(SELL, trade)


            # Trader sold
            else:
                t.funds += order_cost
                t.possession -= trade[T_SIZE]

                tc.funds -= order_cost
                tc.possession += trade[T_SIZE]

                # Update order tracking of certain agent types
                if tc_type in order_tracking_types:
                    tc.update_order_tracking(BUY, trade)

        if reward_dict is None:
            reward_dict = {}
            for agent_id in prev_capital_dict:
                prev_capital = prev_capital_dict[agent_id]
                new_capital = self.agents_dict[agent_id]['env'].capital
                r = self.diff(new_capital, prev_capital)
                reward_dict[agent_id] = r
        else:
            for agent_id in prev_capital_dict:
                prev_capital = prev_capital_dict[agent_id]
                new_capital = self.agents_dict[agent_id]['env'].capital
                r = self.diff(new_capital, prev_capital)
                reward_dict[agent_id] += r
        return reward_dict

    def seed(self, seed=None):
        pass

    def get_obs(self) -> dict:
        if hasattr(self, 'quotes'):
            obs = self.quotes
        else:
            obs = self.market.ob.price_levels.get_quotes()
            self.quotes = obs

        obs_dict = {}
        for agent_id in self.agents_dict:
            obs_dict[agent_id] = [obs, self.agents_dict[agent_id]['env'].get_private_variables()]
        return obs_dict

    def render(self, mode='human'):

        if self.first_render:
            self.render_app = get_multienv_app()

        MarketEnv.render(self)
        time.sleep(0.1)  # TODO investigate why a halt is n

    def get_private_variables(self) -> tuple:
        pass

    @property
    def action_space(self):
        pass

    @property
    def observation_space(self):
        pass


def get_actions_dict(obs_dict: dict) -> dict:
    actions_dict = {}
    for agent_id in obs_dict:
        agent_type, trader_id = agent_id.split('_')
        if agent_type == 'dist':
            actions_dict[agent_id] = gym.spaces.Box(low=-2.9, high=10, shape=(4,), dtype=np.float).sample()
        elif agent_type == 'spread':
            actions_dict[agent_id] = gym.spaces.Box(low=-0.1, high=2, shape=(2,), dtype=np.float).sample()
        elif agent_type == 'market':
            actions_dict[agent_id] = gym.spaces.Discrete(3).sample()
        else:
            raise NotImplementedError('Agent_type:{} is not implemented'.format(agent_id))
    return actions_dict


if __name__ == '__main__':
    trader_id = 1
    random_agent_list = []
    agent_list = []
    for i in range(3):
        random_agent_list.append('dist_' + str(trader_id))
        trader_id += 1
        agent_list.append('dist_' + str(trader_id))
        trader_id += 1
    for i in range(3):
        random_agent_list.append('spread_' + str(trader_id))
        trader_id += 1
        agent_list.append('spread_' + str(trader_id))
        trader_id += 1
    for i in range(3):
        random_agent_list.append('market_' + str(trader_id))
        trader_id += 1
        agent_list.append('market_' + str(trader_id))
        trader_id += 1

    env = MultiAgentOrderEnv(agent_list, random_agent_list, episode_seconds=10)
    for i in range(5):
        obs = env.reset()
        # print(env.quotes)
        done = {'__all__': False}
        while not done['__all__']:
            action_dict = get_actions_dict(obs)
            obs, reward, done, info = env.step(action_dict)
            # print(env.quotes, env.market.time)
            env.render()
    env.close()
