import json
from types import SimpleNamespace
from unittest import TestCase

import numpy as np

from orderbookmdp._orderbookmdp import CyExternalMarket
from orderbookmdp.order_book.constants import BUY
from orderbookmdp.order_book.constants import EXT_ID
from orderbookmdp.order_book.constants import SELL
from orderbookmdp.order_book.constants import SO_PRICE
from orderbookmdp.order_book.constants import SO_SIZE
from orderbookmdp.order_book.market import ExternalMarket
from orderbookmdp.order_book.utils import to_int

tick = 0.01
tick_dec = int(np.log10(1 / tick))
multiplier = int(10 ** tick_dec)


def load():

    with open('tests/testdata/messages.json', 'rb') as messages_json_file:
        messages = json.load(messages_json_file)
    with open('tests/testdata/beginning_level_3.json', 'rb') as begin_json_file:
        beginning_level_3 = json.load(begin_json_file)
    with open('tests/testdata/ending_level_3.json', 'rb') as end_json_file:
        ending_level_3 = json.load(end_json_file)
    try:
        assert beginning_level_3['sequence'] + 1 == messages[0]['sequence']
        assert ending_level_3['sequence'] == messages[-1]['sequence']
    except AssertionError:
        print("Problem with sample data sequences")
    return beginning_level_3, ending_level_3, messages


def agg_snap(snap):
    agg = {'asks': {}, 'bids': {}}
    # Snapshot Order : [price, size, external_market_order_id]
    for so_order in snap['bids']:
        p = round(float(so_order[SO_PRICE]), tick_dec)
        s = float(so_order[SO_SIZE])
        if p not in agg['bids']:
            agg['bids'][p] = s
        else:
            agg['bids'][p] += s

    for so_order in snap['asks']:
        p = round(float(so_order[SO_PRICE]), tick_dec)
        s = float(so_order[SO_SIZE])
        if p not in agg['asks']:
            agg['asks'][p] = s
        else:
            agg['asks'][p] += s

    return agg


class TestExternalMarket(TestCase):

    def messages(self, m, b_lvl_3, e_lvl_3, messages):
        m.fill_snap(b_lvl_3)

        prev_seq = b_lvl_3['sequence']

        for k, message in enumerate(messages):
            seq = message['sequence']
            self.assertEqual(seq, prev_seq + 1)
            prev_seq = seq

            if 'price' in message:
                message['price'] = round(float(message['price']), tick_dec)
            if 'size' in message:
                message['size'] = float(message['size'])
            else:
                message['size'] = -1
            if 'funds' in message:
                message['funds'] = float(message['funds'])
            else:
                message['funds'] = -1
            if 'side' in message:
                message['side'] = BUY if message['side'] == 'buy' else SELL

            message['trader_id'] = EXT_ID

            mess = SimpleNamespace(**message)
            m.send_message(mess, external=True)

        self.assertEqual(seq, e_lvl_3['sequence'])
        snap = m.ob.price_levels.get_snap()
        corr_snap = agg_snap(e_lvl_3)

        for price in corr_snap['asks']:
            corr = corr_snap['asks'][price]
            self.price_level(corr, price, 'asks', snap, m)
        for price in corr_snap['bids']:
            corr = corr_snap['bids'][price]
            self.price_level(corr, price, 'bids', snap, m)

    def fill_snap(self, m_type, price_level_type, price_levels_type, b_lvl_3, e_lvl_3):

        if m_type == 'py':
            m = ExternalMarket(tick_size=0.01, ob_type='py',
                               price_level_type=price_level_type, price_levels_type=price_levels_type)
        elif m_type == 'cy':
            m = CyExternalMarket(tick_size=0.01, ob_type='py',
                                 price_level_type=price_level_type, price_levels_type=price_levels_type)

        m.fill_snap(b_lvl_3)
        snap = m.ob.price_levels.get_snap()
        corr_snap = agg_snap(b_lvl_3)

        for price in corr_snap['asks']:
            corr = corr_snap['asks'][price]
            self.price_level(corr, price, 'asks', snap, m)
        for price in corr_snap['bids']:
            corr = corr_snap['bids'][price]
            self.price_level(corr, price, 'bids', snap, m)

        if m_type == 'py':
            m = ExternalMarket(tick_size=0.01, ob_type='py',
                               price_level_type=price_level_type, price_levels_type=price_levels_type)
        elif m_type == 'cy':
            m = CyExternalMarket(tick_size=0.01, ob_type='py',
                                 price_level_type=price_level_type, price_levels_type=price_levels_type)

        m.fill_snap(e_lvl_3)
        snap = m.ob.price_levels.get_snap()
        corr_snap = agg_snap(e_lvl_3)

        for price in sorted(corr_snap['asks']):
            corr = corr_snap['asks'][price]
            self.price_level(corr, price, 'asks', snap, m)
        for price in sorted(corr_snap['bids']):
            corr = corr_snap['bids'][price]
            self.price_level(corr, price, 'bids', snap, m)

    def price_level(self, corr, price, side, snap, m):
        price_int = to_int(price, multiplier)

        if hasattr(m.ob.price_levels, 'max_price'):
            if m.ob.price_levels.min_price < price_int < m.ob.price_levels.max_price:
                market = snap[side][price_int]
                diff = corr - market
                assert abs(diff) < 10e-4, 'Diff :{:.2e} in price:{}'.format(diff, price)  # TODO floating point error large in cython
                # print(diff, price)
        else:
            market = snap[side][price_int]
            diff = corr - market
            assert abs(diff) < 10e-4, 'Diff :{:.2e} in price:{}'.format(diff, price)

    def test_send_message_sorted_ordered(self):
        b_lvl_3, e_lvl_3, messages = load()
        m = ExternalMarket(price_level_type='ordered_dict',
                           price_levels_type='sorted_dict')
        self.messages(m, b_lvl_3, e_lvl_3, messages)

    def test_fill_snap_sorted_ordered(self):
        b_lvl_3, e_lvl_3, messages = load()
        self.fill_snap('py', 'ordered_dict', 'sorted_dict', b_lvl_3, e_lvl_3)

    def test_fill_snap_rb_ordered(self):
        b_lvl_3, e_lvl_3, messages = load()
        self.fill_snap('py', 'ordered_dict', 'fast_rb', b_lvl_3, e_lvl_3)

    def test_send_message_rb_ordered(self):
        b_lvl_3, e_lvl_3, messages = load()
        m = ExternalMarket(price_level_type='ordered_dict',
                           price_levels_type='fast_rb')
        self.messages(m, b_lvl_3, e_lvl_3, messages)

    def test_send_message_avl_ordered(self):
        b_lvl_3, e_lvl_3, messages = load()
        m = ExternalMarket(price_level_type='ordered_dict',
                           price_levels_type='fast_avl')
        self.messages(m, b_lvl_3, e_lvl_3, messages)

    def test_fill_snap_avl_ordered(self):
        b_lvl_3, e_lvl_3, messages = load()
        self.fill_snap('py', 'ordered_dict', 'fast_avl', b_lvl_3, e_lvl_3)

    def test_fill_snap_avl_deque(self):
        b_lvl_3, e_lvl_3, messages = load()
        self.fill_snap('py', 'deque', 'fast_avl', b_lvl_3, e_lvl_3)

    def test_send_message_avl_deque(self):
        b_lvl_3, e_lvl_3, messages = load()
        m = ExternalMarket(price_level_type='deque',
                           price_levels_type='fast_avl')
        self.messages(m, b_lvl_3, e_lvl_3, messages)

    def test_fill_snap_rb_deque(self):
        b_lvl_3, e_lvl_3, messages = load()
        self.fill_snap('py', 'deque', 'fast_rb', b_lvl_3, e_lvl_3)

    def test_send_message_rb_deque(self):
        b_lvl_3, e_lvl_3, messages = load()
        m = ExternalMarket(price_level_type='deque',
                           price_levels_type='fast_rb')
        self.messages(m, b_lvl_3, e_lvl_3, messages)

    def test_fill_snap_list_deque(self):
        b_lvl_3, e_lvl_3, messages = load()
        self.fill_snap('py', 'deque', 'list', b_lvl_3, e_lvl_3)

    def test_send_message_list_deque(self):
        b_lvl_3, e_lvl_3, messages = load()
        m = ExternalMarket(price_level_type='deque',
                           price_levels_type='list')
        self.messages(m, b_lvl_3, e_lvl_3, messages)

    def test_fill_snap_avl_cydeque(self):
        b_lvl_3, e_lvl_3, messages = load()
        self.fill_snap('py', 'cydeque', 'fast_avl', b_lvl_3, e_lvl_3)

    def test_send_message_avl_cydeque(self):
        b_lvl_3, e_lvl_3, messages = load()
        m = ExternalMarket(price_level_type='cydeque',
                           price_levels_type='fast_avl')
        self.messages(m, b_lvl_3, e_lvl_3, messages)

    def test_fill_snap_cylist_cydeque(self):
        b_lvl_3, e_lvl_3, messages = load()
        self.fill_snap('py', 'cydeque', 'cylist', b_lvl_3, e_lvl_3)

    def test_send_message_cylist_cydeque(self):
        b_lvl_3, e_lvl_3, messages = load()
        m = ExternalMarket(price_level_type='cydeque',
                           price_levels_type='cylist')
        self.messages(m, b_lvl_3, e_lvl_3, messages)

    def test_fill_snap_cymarket_cylist_cydeque(self):
        b_lvl_3, e_lvl_3, messages = load()
        self.fill_snap('cy', 'cydeque', 'cylist', b_lvl_3, e_lvl_3)

    def test_send_message_cymarket_cylist_cydeque(self):
        b_lvl_3, e_lvl_3, messages = load()
        m = CyExternalMarket(price_level_type='cydeque', price_levels_type='cylist')
        self.messages(m, b_lvl_3, e_lvl_3, messages)
