import datetime
import logging
import os

import cbpro
import pandas as pd
import ujson

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)


def save_snapshot():
    logging.info('downloads snapshot')
    snapshot = public_client.get_product_order_book('BTC-USD', level=3)
    date_time = datetime.datetime.now()
    dts = date_time.strftime('%d_%m_%Y_%H_%M_%S')
    with open(data_dir + dts + '_snaps.json', 'w') as f:
        ujson.dump(snapshot, f)
    logging.info('snapshot saved')


class DownloadWebsocketClient(cbpro.WebsocketClient):
    def change_file(self, msg):
        logging.info('changes file, messsage count: {}'.format(self.message_count))
        if self.file:
            self.file.close()
        self.message_seq = msg['sequence']
        date_time = pd.to_datetime(msg['time'])
        dts = date_time.strftime('%d_%m_%Y_%H_%M_%S')
        self.file = open(data_dir + dts + '_mess.json', 'w')

    def on_open(self):
        self.url = "wss://ws-feed.pro.coinbase.com/"
        self.products = ["BTC-USD"]
        self.message_count = 0
        self.datetime = datetime.datetime.now()
        self.snapshot_time_delta = pd.to_timedelta('60min').to_pytimedelta()
        self.file = None
        save_snapshot()

    def on_message(self, msg):

        if self.message_count % 10000 == 0:
            logging.info('message count: {}'.format(self.message_count))

        if self.message_count % 1000000 == 0:
            self.change_file(msg)
        self.file.write(ujson.dumps(msg) + '\n')
        self.message_count += 1

        mess_seq = msg['sequence']
        if mess_seq - self.message_seq > 1:
            logging.info('missed sequences: {}'.format(mess_seq - self.message_seq))
            save_snapshot()

        if self.message_count % 1000 == 0:
            now = datetime.datetime.now()
            if now - self.datetime > self.snapshot_time_delta:
                logging.info('saves snapshot timedelta')
                save_snapshot()
                self.datetime = now

        self.message_seq = mess_seq

    def on_close(self):
        logging.info("-- Goodbye! --")

    def on_error(self, e, data=None):
        self.error = e
        self.stop = True
        logging.info('{} - data: {}'.format(e, data))


def download(dir, time_delta='1 min'):

    time_delta = pd.to_timedelta(time_delta)
    date_time = pd.datetime.now()

    data_dir = dir + 'json/'
    try:
        os.makedirs(data_dir)
    except FileExistsError:
        pass

    try:
        break_ = False
        while not break_:
            public_client = cbpro.PublicClient()
            wsClient = DownloadWebsocketClient()
            wsClient.start()
            while not wsClient.error:
                if pd.datetime.now() - date_time < time_delta:
                    break_ = True
                    break
                pass
            wsClient.close()
    except KeyboardInterrupt:
        wsClient.close()

if __name__ == '__main__':
    download('../../../data/')
