from src.orderbookmdp.order_book.market import BUY, SELL, ExternalMarket
from src.orderbookmdp.order_book.order_books import PyOrderBook as PyOB
from src.orderbookmdp.order_book.constants import BUY, SELL, OIB_ID
import time
from collections import deque
import numpy as np
from random import random
from src.orderbookmdp.order_book.orderstream import orderstream
from src.orderbookmdp._orderbookmdp import CyOrderBook

def test_real_orders(ds, market):
    fill_time = 0
    order_time = 0
    orders = 0

    updated = False
    for message, snap in ds:
        if snap:
            if not updated:
                t = time.time()
                market.fill_snap(snap)
                fill_time += time.time() - t
                updated = True
            else:
                break
        else:
            t = time.time()
            trades, oib = market.send_message(message)
            order_time += time.time() - t
            orders += 1

    return orders/order_time, fill_time


def test_random_orders(ob, orders):
    orderids = deque(maxlen=500)
    seconds = 0
    norders = 0
    for row in range(orders.shape[0]):
        order = orders[row, :]
        side, size, price = order

        t = time.time()

        # Limit Orders
        trades, oib = ob.limit(price, int(side), size, -1, '0')
        seconds += time.time() - t

        norders += 1
        if oib is not None:
            orderids.append(oib)

        # Change the orders
        if row % 1000 == 0:
            while len(orderids) > 0:
                oib = orderids.pop()

                if random() > 0.95:
                    size = np.round(abs(np.random.randn()) + 0.01, 3)
                    t = time.time()
                    ob.update(oib[OIB_ID], size)
                    seconds += time.time() - t
                    norders += 1
                else:
                    t = time.time()
                    ob.cancel(oib[OIB_ID])
                    seconds += time.time() - t
                    norders += 1

        # Some Market Orders
        if row % 500 == 0:
            for i in range(50):
                size = np.round(abs(np.random.randn()) + 0.01, 3) / 10
                if random() > 0.5:
                    t = time.time()
                    ob.market_order(size, BUY, -1, '0')
                    seconds += time.time() - t
                else:
                    t = time.time()
                    ob.market_order(size, SELL, -1, '0')
                    seconds += time.time() - t

        if ob.price_levels.exist_buy_orders() and ob.price_levels.exist_sell_orders():
            t = time.time()
            ob.price_levels.get_quotes()
            seconds += time.time() - t
    orders_per_sec = norders / seconds
    time_per_order = seconds / norders
    return orders_per_sec, time_per_order


if __name__=='__main__':
    n_orders = 100000
    # Side, Size, Price
    orders = np.vstack([
        np.random.choice([BUY, SELL], n_orders),
        np.round(abs(np.random.randn(n_orders)) + 0.01, 3),
        (np.round(np.random.randn(n_orders) + 100, 2)*100).astype(int)
    ]).T

    print('################### SPEED TEST ###################')
    mess = 'Order Level:{} Price Levels:{}    \t'
    mess += 'RANDOM orders/sec:{:.2e}\ttime/order:{:.2e}\tREAL orders/sec:{:.2e}\tfill time:{:.2f}'

    # price_level = 'ordered_dict'
    # price_levels = 'sorted_dict'
    # ob = PyOB(price_level_type=price_level, price_levels_type=price_levels)
    # ra_ops, ra_tpo = test_random_orders(ob, orders)
    # ds = orderstream(order_paths='../data/feather/', snapshot_paths='../data/snap_json/')
    # m = ExternalMarket(price_level_type=price_level, price_levels_type=price_levels)
    # re_ops, re_tpo = test_real_orders(ds, m)
    # print(mess.format(price_level, price_levels, ra_ops, ra_tpo, re_ops, re_tpo))
    #
    # price_levels = 'fast_rb'
    # ob = PyOB(price_level_type=price_level, price_levels_type=price_levels)
    # ra_ops, ra_tpo = test_random_orders(ob, orders)
    # ds = orderstream(order_paths='../data/feather/', snapshot_paths='../data/snap_json/')
    # m = ExternalMarket(price_level_type=price_level, price_levels_type=price_levels)
    # re_ops, re_tpo = test_real_orders(ds, m)
    # print(mess.format(price_level, price_levels, ra_ops, ra_tpo, re_ops, re_tpo))
    #
    # price_levels = 'fast_avl'
    # ob = PyOB(price_level_type=price_level, price_levels_type=price_levels)
    # ra_ops, ra_tpo = test_random_orders(ob, orders)
    # ds = orderstream(order_paths='../data/feather/', snapshot_paths='../data/snap_json/')
    # m = ExternalMarket(price_level_type=price_level, price_levels_type=price_levels)
    # re_ops, re_tpo = test_real_orders(ds, m)
    # print(mess.format(price_level, price_levels, ra_ops, ra_tpo, re_ops, re_tpo))
    #
    # price_levels = 'fast_rb'
    # price_level = 'deque'
    # ob = PyOB(price_level_type=price_level, price_levels_type=price_levels)
    # ra_ops, ra_tpo = test_random_orders(ob, orders)
    # ds = orderstream(order_paths='../data/feather/', snapshot_paths='../data/snap_json/')
    # m = ExternalMarket(price_level_type=price_level, price_levels_type=price_levels)
    # re_ops, re_tpo = test_real_orders(ds, m)
    # print(mess.format(price_level, price_levels, ra_ops, ra_tpo, re_ops, re_tpo))
    #
    # price_levels = 'fast_avl'
    # price_level = 'deque'
    # ob = PyOB(price_level_type=price_level, price_levels_type=price_levels)
    # ra_ops, ra_tpo = test_random_orders(ob, orders)
    # ds = orderstream(order_paths='../data/feather/', snapshot_paths='../data/snap_json/')
    # m = ExternalMarket(price_level_type=price_level, price_levels_type=price_levels)
    # re_ops, re_tpo = test_real_orders(ds, m)
    # print(mess.format(price_level, price_levels, ra_ops, ra_tpo, re_ops, re_tpo))
    #
    # price_levels = 'list'
    # price_level = 'deque'
    # ob = PyOB(price_level_type=price_level, price_levels_type=price_levels)
    # ra_ops, ra_tpo = test_random_orders(ob, orders)
    # ds = orderstream(order_paths='../data/feather/', snapshot_paths='../data/snap_json/')
    # m = ExternalMarket(price_level_type=price_level, price_levels_type=price_levels)
    # re_ops, re_tpo = test_real_orders(ds, m)
    # print(mess.format(price_level, price_levels, ra_ops, ra_tpo, re_ops, re_tpo))
    #
    # price_levels = 'fast_avl'
    # price_level = 'cydeque'
    # ob = PyOB(price_level_type=price_level, price_levels_type=price_levels)
    # ra_ops, ra_tpo = test_random_orders(ob, orders)
    # ds = orderstream(order_paths='../data/feather/', snapshot_paths='../data/snap_json/')
    # m = ExternalMarket(price_level_type=price_level, price_levels_type=price_levels)
    # re_ops, re_tpo = test_real_orders(ds, m)
    # print(mess.format(price_level, price_levels, ra_ops, ra_tpo, re_ops, re_tpo))
    #
    # price_levels = 'list'
    # price_level = 'cydeque'
    # ob = PyOB(price_level_type=price_level, price_levels_type=price_levels)
    # ra_ops, ra_tpo = test_random_orders(ob, orders)
    # ds = orderstream(order_paths='../data/feather/', snapshot_paths='../data/snap_json/')
    # m = ExternalMarket(price_level_type=price_level, price_levels_type=price_levels)
    # re_ops, re_tpo = test_real_orders(ds, m)
    # print(mess.format(price_level, price_levels, ra_ops, ra_tpo, re_ops, re_tpo))
    #
    # price_levels = 'cylist'
    # price_level = 'cydeque'
    # ob = PyOB(price_level_type=price_level, price_levels_type=price_levels)
    # ra_ops, ra_tpo = test_random_orders(ob, orders)
    # ds = orderstream(order_paths='../data/feather/', snapshot_paths='../data/snap_json/')
    # m = ExternalMarket(price_level_type=price_level, price_levels_type=price_levels)
    # re_ops, re_tpo = test_real_orders(ds, m)
    # print(mess.format(price_level, price_levels, ra_ops, ra_tpo, re_ops, re_tpo))

    print('Cython Order Book')
    price_levels = 'cylist'
    price_level = 'cydeque'
    ob = CyOrderBook(price_level_type=price_level, price_levels_type=price_levels)
    ra_ops, ra_tpo = test_random_orders(ob, orders)
    ds = orderstream(order_paths='../data/feather/', snapshot_paths='../data/snap_json/')
    m = ExternalMarket(price_level_type=price_level, price_levels_type=price_levels)
    re_ops, re_tpo = test_real_orders(ds, m)
    print(mess.format(price_level, price_levels, ra_ops, ra_tpo, re_ops, re_tpo))
