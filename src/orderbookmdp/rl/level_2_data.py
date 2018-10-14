from sortedcontainers.sorteddict import SortedDict
from orderbookmdp.rl.market_order_envs import MarketOrderEnv
from orderbookmdp.order_book.constants import BUY, SELL
from numba import jit
import time
from collections import deque
import sys
import pandas as pd
from multiprocessing import Pool
from multiprocessing import Process
from multiprocessing.pool import ThreadPool
import threading
from multiprocessing import cpu_count
import multiprocessing
import math
import itertools


def get_level_2(price_levels, max_capital, multiplier):
    snap_shot = {'buy': list(), 'sell': list()}
    temp_cap = max_capital
    for price in price_levels.get_prices(BUY):
        size = price_levels.get_level(BUY, price).size
        price /= multiplier
        snap_shot['buy'].append((price, size))
        temp_cap -= size * price
        if temp_cap <= 0:
            break

    temp_cap = max_capital
    for price in price_levels.get_prices(SELL):
        size = price_levels.get_level(SELL, price).size
        price /= multiplier
        snap_shot['sell'].append((price, size))
        temp_cap -= size * price
        if temp_cap <= 0:
            break

    #snap_shot['buy'] = list(reversed(snap_shot['buy']))
    return snap_shot


def get_level_2_sequence(T=10, initial_funds=100, order_path='../../../data/feather/',
                         snapshot_path='../../../data/snap_json/'):
    data = []
    env = MarketOrderEnv(initial_funds=initial_funds, random_start=False, order_paths=order_path,
                         snapshot_paths=snapshot_path,  max_sequence_skip=10000)
    max_capital = 10 * env.initial_funds
    env.reset()
    for t in range(T):
        env.step(0)  # SELL
        level_2 = get_level_2(env.market.ob.price_levels, max_capital, env.market.multiplier)
        time = env.market.time
        data.append((time, level_2))
    return data


def match(level_2_sequences, capital, funds, possession, t, action, takerfee):
    if action == BUY:
        pl = level_2_sequences[t][1]
        if funds > 0:
            possession += match_buy(pl['sell'], funds, takerfee)
            funds = 0
        #sell_cap = match_sell(pl['buy'], possession, 0)
        sell_price = pl['buy'][-1][0]
        capital = sell_price*possession
    else:
        if possession > 0:
            pl = level_2_sequences[t][1]
            funds += match_sell(pl['buy'], possession, takerfee)
            possession = 0
            capital = funds

    return funds, possession, capital


#@jit(nopython=True)
def match_buy(sell_book, amount, takerfee):
    matched_size = 0
    for price, size in sell_book:
        ms_ = amount / price
        ms = min(ms_, size)
        matched_size += ms
        amount -= ms * price
        if abs(amount) < 10e-10:
            return matched_size*(1-takerfee)


#@jit(nopython=True)
def match_sell(buy_book, sell_size, takerfee):
    matched_amount = 0
    for price, size in buy_book:
        ms = min(size, sell_size)
        matched_amount += ms * price
        sell_size -= ms
        if abs(sell_size) < 10e-10:
            return matched_amount*(1-takerfee)


def break_condition(capital, initial_funds, t, T):
    return capital / initial_funds < 0.99 + 0.005 * (t / T)

global sells
sells = set()


def back_track_opt_paths(init_funds, capital, funds, possession, level_2_sequences, t, T, takerfee, path=()):
    if t == T:
        return (path, capital/init_funds)
    paths = []
    for action in [BUY, SELL]:
        if action == SELL and t not in sells:
            sys.stdout.write('\r' + 'Pct done:{:.2f}%'.format(len(sells)/T*100))
            sells.add(t)
        new_funds, new_possession, new_capital = match(level_2_sequences, capital, funds,
                                                       possession, t, action, takerfee)
        if not break_condition(new_capital, init_funds, t + 1, T):
            ret_paths = back_track_opt_paths(init_funds, new_capital, new_funds, new_possession,
                                             level_2_sequences, t + 1, T, takerfee, path + (action,))
            if len(ret_paths) > 0:
                paths.append(ret_paths)

    return paths


def back_track_threaded(init_funds, T, takerfee, level_2_sequences, num_threads=1):
    pool = Pool(num_threads)
    depth = math.log2(num_threads)
    arguments = []
    for comb in itertools.product([BUY, SELL], repeat=int(depth)):
        t = 0
        funds = init_funds
        capital = init_funds
        possession = 0
        break_= False
        path = ()

        for action in comb:
            new_funds, new_possession, new_capital = match(level_2_sequences, capital, funds,
                                                           possession, t, action, takerfee)
            t += 1
            if break_condition(new_capital, init_funds, t, T):
                break_ = True
                print('breaks')
                break
        if break_:
            break
        else:
            arguments.append((init_funds, new_capital, new_funds, new_possession,
                              level_2_sequences, t + 1, T, takerfee, path + (action,)))

    print(len(arguments))
    paths = pool.starmap(back_track_opt_paths, arguments)

    return paths


def flatten(aList):
    result = []
    for entry in aList:
        if isinstance(entry, list):
            result += flatten(entry)
        else:
            result.append(entry)
    return result


def test(lvl2_seqs, init_funds, T, takerfee):
    paths = back_track_opt_paths(init_funds, init_funds, init_funds, 0, lvl2_seqs, 0, T, takerfee)
    return paths


if __name__ == '__main__':
    init_funds = 10000
    T = 150
    takerfee = 0.002
    print('Creates level 2 sequences')

    lvl2_seqs = get_level_2_sequence(T, init_funds)
    print('Finds opt paths')
    t = time.time()
    paths = test(lvl2_seqs, init_funds, T, takerfee)
    #paths = back_track_threaded(init_funds, T, takerfee, lvl2_seqs, num_threads=8)
    print()
    print(time.time() - t)
    paths = flatten(paths)
    print(len(paths))
    cr = pd.Series([p[1] for p in paths])
    cr = cr.sort_values(ascending=False)
    print(cr.head())

