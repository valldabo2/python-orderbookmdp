import abc
import threading
import webbrowser
from collections.__init__ import deque

import numpy as np
import pandas as pd
import requests
from custom_inherit import DocInheritMeta

import orderbookmdp._orderbookmdp
from orderbookmdp.order_book.constants import BUY
from orderbookmdp.order_book.constants import SELL
from orderbookmdp.order_book.market import ExternalMarket


def get_market(market_type, **kwargs):
    """ Returns a market based on the parameter.
    Parameters
    ----------
    market_type : str
        The type of market to return
    kwargs
        Additional settings for the market

    Returns
    -------
    market : Market

    """
    if market_type == 'pyext':
        return ExternalMarket(**kwargs)
    elif market_type == 'cyext':
        return orderbookmdp._orderbookmdp.CyExternalMarket(**kwargs)


class MarketEnv(metaclass=DocInheritMeta(style="numpy", abstract_base_class=True)):
    """ A market environment extending the `OpenAI gym class <https://github.com/openai/gym/blob/master/gym/core.py/>`_ .

    The main functions are the step and reset functions. In the step function the agent sends orders and receives a reward
    based on the orders/trades.

    A basic rendering function using `Dash <https://plot.ly/products/dash/>`_ is implemented. This opens a Flask server
    in another thread that renders different information about the market.

    Attributes
    ----------
    capital : float
        The capital of the agent
    funds : float
        The cash/funds of the agent
    possession : float
        The size of the asset the agent possesses
    price_n : int
        Number of price points to render back in time.
    trades_list : list
        All trades


    """
    # Set this in SOME subclasses
    metadata = {'render.modes': []}
    reward_range = (-float('inf'), float('inf'))
    spec = None

    def __init__(self, market_type='cyext',
                 market_setup=dict(tick_size=0.01, ob_type='cy_order_book', order_level_type='cydeque',
                                   order_levels_type='cylist', price_as_ints=True), initial_funds=10000, T_ID=1):
        """

        Parameters
        ----------
        market_type : str
            The type of market to be used
        market_setup : dict
            Parameters for the market
        initial_funds : float
            The initial cash of the agent
        T_ID : int
            The agent's trader id
        """

        # Market
        self._market_type = market_type
        self._market_setup = market_setup

        # Init Funds
        self.capital = initial_funds
        self.funds = initial_funds
        self.initial_funds = initial_funds
        self.possession = 0

        # Rendering
        self.render_app = None
        self.open_tab = False
        self.first_render = True
        self.price_n = 10000

        self.trades_list = []
        self.T_ID = T_ID

    def step(self, action):
        """ Sends orders based on the agents action and receives a reward based on trades that have occurred.

        The action is first converted to messages to the market. Then the messages are sent and trades are received.
        The reward is then calculated based on the trades.

        Parameters
        ----------
        action : numpy.array

        Returns
        -------
        obs : list[tuple, tuple]
            The current quotes of the market and private information about the agents portfolio
        reward : float
        done : bool
            If the episode has finished
        info : dict
            Additional information
        """
        messages = self.get_messages(action)
        trades, done, info = self.send_messages(messages)
        reward = self.get_reward(trades)
        obs = self.get_obs()
        return obs, reward, done, info

    @abc.abstractmethod
    def get_messages(self, action: np.array) -> tuple:
        """ Returns messages based on the action received.

        Parameters
        ----------
        action : numpy.array

        Returns
        -------
        messages: tuple

        """

    @abc.abstractmethod
    def get_reward(self, trades: list) -> tuple:
        """ Returns a reward based on trades

        Parameters
        ----------
        trades : list

        Returns
        -------
        reward : float

        """

    @abc.abstractmethod
    def send_messages(self, messages: tuple) -> (list, bool, dict):
        """ Sends all the messages to the market

        Parameters
        ----------
        messages : tuple

        Returns
        -------
        trades : list
        done : bool
            If the episode has finished or not.
        info : dict
            Extra information about the environment
        """

    @abc.abstractmethod
    def get_private_variables(self) -> tuple:
        """ Returns private variables of for the agent to observe. For example the possession of the agent.
        Returns
        -------
        private_variables : tuple

        """

    def get_obs(self) -> tuple:
        """ Returns an observation of the market. Currently the quotes.
        Returns
        -------
        observation : tuple

        """
        if hasattr(self, 'quotes'):
            obs = self.quotes
        else:
            obs = self.market.ob.price_levels.get_quotes()
            self.quotes = obs

        obs = (obs, self.get_private_variables())
        return obs

    def reset(self, market=None):
        """ Resets the environment with a market or creates a new one. Also resets the render app if needed.
        Parameters
        ----------
        market : Market
            If to use a specific market instead of a newly created one.

        Returns
        -------
        observation : tuple

        """
        if market is not None:
            self.market = market
        else:
            self.market = get_market(self._market_type, **self._market_setup)

        obs = self.get_obs()
        self.capital = self.initial_funds

        if self.render_app:
            self.render_app.use_reloader = False
            self.render_app.__setattr__('ask', deque(maxlen=self.price_n))
            self.render_app.__setattr__('bid', deque(maxlen=self.price_n))
            self.render_app.__setattr__('time', deque(maxlen=self.price_n))
            self.render_app.__setattr__('sellbook', {})
            self.render_app.__setattr__('buybook', {})
            self.render_app.__setattr__('trades_', [])

        return obs

    def render(self):
        """ Renders the environment in a dash app.

        """
        if self.first_render:
            self.render_app.use_reloader = False
            self.render_app.__setattr__('ask', deque(maxlen=self.price_n))
            self.render_app.__setattr__('bid', deque(maxlen=self.price_n))
            self.render_app.__setattr__('time', deque(maxlen=self.price_n))
            self.render_app.__setattr__('sellbook', {})
            self.render_app.__setattr__('buybook', {})
            self.render_app.__setattr__('trades_', [])

            self.app_thread = threading.Thread(target=self.render_app.run_server)
            self.app_thread.start()
            if not self.open_tab:
                self.open_tab = webbrowser.open_new('http://127.0.0.1:8050')

            self.first_render = False

        time_ = pd.to_datetime(self.market.time)
        ask, ask_vol, bid, bid_vol = self.quotes
        self.render_app.ask.append(ask)
        self.render_app.bid.append(bid)
        self.render_app.time.append(time_)

        self.render_app.trades_ = self.trades_list[-40:]
        ask, ask_vol, bid, bid_vol = self.quotes
        n = 50
        buy_book = {}
        for i in range(n):
            p = bid - i
            try:
                size = self.market.ob.price_levels.get_level(BUY, p).size
            except (KeyError, IndexError) as e:
                pass

            buy_book[p] = size
        n = 50
        sell_book = {}
        for i in range(n):
            p = ask + i
            try:
                size = self.market.ob.price_levels.get_level(SELL, p).size
            except (KeyError, IndexError) as e:
                pass
            sell_book[p] = size

        self.render_app.buybook = buy_book
        self.render_app.sellbook = sell_book

    def close(self):
        """ Shuts down the render app if needed.

        """
        if self.render_app:
            requests.post('http://127.0.0.1:8050/shutdown')
        return

    @abc.abstractmethod
    def seed(self, seed=None):
        """Sets the seed for this env's random number generator(s).
        """

        return

    # Set these in ALL subclasses
    @property
    @abc.abstractmethod
    def action_space(self):
        """gym.spaces : The action space of the environment."""

    @property
    @abc.abstractmethod
    def observation_space(self):
        """gym.spaces : The obervation space of the environment."""

    @property
    def unwrapped(self):
        """Completely unwrap this env.
        Returns:
            gym.Env: The base non-wrapped gym.MarketEnv instance
        """
        return self

    def __str__(self):
        if self.spec is None:
            return '<{} instance>'.format(type(self).__name__)
        else:
            return '<{}<{}>>'.format(type(self).__name__, self.spec.id)
