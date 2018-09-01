import logging
import time
from decimal import Decimal

import cbpro
from cbpro.websocket_client import WebsocketClient
from sortedcontainers.sorteddict import SortedDict


class GdaxOrderBook(WebsocketClient):
    def __init__(self, **kwargs):
        super(GdaxOrderBook, self).__init__(**kwargs)
        self.public_client = cbpro.PublicClient()
        self.asks = None
        self.message_count = 0

    def on_open(self):
        self.url = "wss://ws-feed.pro.coinbase.com/"
        self.products = ["BTC-USD"]
        self.channels = ['level2']

    def on_message(self, msg):
        if msg['type'] == 'snapshot':
            self.fill_snap(msg)
        else:
            self.update(msg)
        self.message_count += 1

    def fill_snap(self, snap):
        self.bids = SortedDict()
        self.asks = SortedDict()
        for bid in snap['bids']:
            self.bids[Decimal(bid[0])] = float(bid[1])
        for ask in snap['asks']:
            self.asks[Decimal(ask[0])] = float(ask[1])

    def update(self, message):
        if message['type'] == 'l2update':
            for changes in message['changes']:
                if changes[0] == 'buy':
                    self.bids[Decimal(changes[1])] = float(changes[2])
                else:
                    self.asks[Decimal(changes[1])] = float(changes[2])

    def get_quotes(self):
        if self.asks is not None:
            ask, askv = self.asks.peekitem(index=0)
            bid, bidv = self.bids.peekitem()
            return ask, askv, bid, bidv

    def on_close(self):
        logging.info("-- Goodbye! --")

    def on_error(self, e, data=None):
        self.error = e
        self.stop = True
        logging.info('{} - data: {}'.format(e, data))


if __name__ == '__main__':
    ws = GdaxOrderBook()
    ws.start()
    t = time.time()
    time.sleep(1)
    while ws.message_count < 10:
        if ws.message_count > 0:
            print(ws.get_quotes())
    ws.close()
