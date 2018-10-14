import logging
import time
from decimal import Decimal
import cbpro
from cbpro.websocket_client import WebsocketClient
from sortedcontainers.sorteddict import SortedDict
from orderbookmdp.rl.secrets import KEY, API_SECRET, PASSPHRASE
import numpy as np
import abc
import logging
import gym
from orderbookmdp.rl.env_utils import quote_differs_pct
from copy import deepcopy
np.set_printoptions(formatter={'float': '{: 0.3f}'.format})


class GdaxOrderBook(WebsocketClient):
    def __init__(self, product='BTC-USD', **kwargs):
        super(GdaxOrderBook, self).__init__(**kwargs)
        self.public_client = cbpro.PublicClient()
        self.products = [product]
        self.message_count = 0
        self.initialized = False

    def on_open(self):
        self.url = "wss://ws-feed.pro.coinbase.com/"
        self.channels = ['level2']

    def on_message(self, msg):
        if msg['type'] == 'snapshot':
            logging.info('Resets orderbook')
            self.fill_snap(msg)
            self.initialized = True
            logging.info('Reset complete')
        else:
            self.update(msg)
        self.message_count += 1

    def fill_snap(self, snap):
        self.bids = SortedDict()
        self.asks = SortedDict()
        for bid in snap['bids']:
            self.bids[Decimal(bid[0])] = Decimal(bid[1])
        for ask in snap['asks']:
            self.asks[Decimal(ask[0])] = Decimal(ask[1])

    def update(self, message):
        if message['type'] == 'l2update':
            for changes in message['changes']:
                chg = Decimal(changes[2])
                price = Decimal(changes[1])
                if changes[0] == 'buy':
                    if chg == 0:
                        self.bids.pop(price)
                    else:
                        self.bids[price] = chg
                else:
                    if chg == 0:
                        self.asks.pop(price)
                    else:
                        self.asks[price] = chg

    def get_quotes(self):
        if self.asks is not None:
            ask, askv = self.asks.peekitem(index=0)
            bid, bidv = self.bids.peekitem()
            return ask, askv, bid, bidv

    def on_close(self):
        logging.info("-- Closes orderbook connection! --")

    def on_error(self, e, data=None):
        self.error = e
        self.stop = True
        logging.info('{} - data: {}'.format(e, data))


class GdaxEnv:
    def __init__(self, product, **kwargs):

        self.kwargs = kwargs
        self.product = product

        self.auth_client = cbpro.AuthenticatedClient(KEY, API_SECRET, PASSPHRASE)
        self.cp, self.bp = product.split('-')  # Counter product and base product, BTC-USD ex.
        accounts = self.auth_client.get_accounts()
        for account in accounts:  # Finds counter product account and base product account
            if account['currency'] == self.cp:
                self.ca = account
            if account['currency'] == self.bp:
                self.ba = account

        self.funds = Decimal(self.ba['available'])
        self.possession = Decimal(self.ca['available'])
        self.max_buy_funds = Decimal(10-10)

    def reset(self):
        self.ob = GdaxOrderBook(self.product, **self.kwargs)
        self.ob.start()
        while not self.ob.initialized:
            pass
        quotes = np.array(self.ob.get_quotes(), dtype='float')

        return quotes, self.get_private_variables()


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
        reward = 0
        done = False
        info = {}
        obs = False
        if action == 0:  # Buy Order
            if self.funds > 0:
                buy_funds = min(self.max_buy_funds, self.funds)
                #self.auth_client.place_market_order(self.product, 'buy', funds=self.funds)
                print('buys', self.funds)

        elif action == 1:  # Sell Order
            if self.possession > 0:
                print('sells', self.possession)
                self.auth_client.place_market_order(self.product, 'sell', size=self.possession)

        self.possession = Decimal(self.auth_client.get_account(self.ca['id'])['available'])
        self.funds = Decimal(self.auth_client.get_account(self.ba['id'])['available'])

        obs = self.run_until_quote_update()

        return obs, reward, done, info

    def close(self):
        self.ob.close()

    def run_until_quote_update(self):
        prev_quotes = np.array(self.ob.get_quotes(), dtype='float')
        quotes = deepcopy(prev_quotes)

        while not quote_differs_pct(prev_quotes, quotes):
            quotes = np.array(self.ob.get_quotes(), dtype='float')

        return quotes, self.get_private_variables()

    @abc.abstractmethod
    def get_private_variables(self) -> tuple:
        """ Returns private variables of for the agent to observe. For example the possession of the agent.
        Returns
        -------
        private_variables : tuple

        """

    @property
    def action_space(self):
        """ The action space is 0=BUY, 1==SELL, 0=HOLD"""
        return gym.spaces.Discrete(3)


class GdaxMarketOrderEnv(GdaxEnv):
    def get_private_variables(self):
        return float(self.possession),


def run_order_book():
    ws = GdaxOrderBook(product='BTC-EUR')
    ws.start()
    t = time.time()
    time.sleep(1)
    while ws.message_count < 10:
        if ws.message_count > 0:
            print(ws.get_quotes())
    ws.close()


def run_env():
    env = GdaxMarketOrderEnv(product='BTC-EUR')
    obs = env.reset()
    for k in range(100):
        action = env.action_space.sample()
        obs, reward, done, info = env.step(action)
        logging.info((obs, action))
    env.close()


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
    #  run_order_book()
    run_env()
