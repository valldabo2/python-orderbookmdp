from copy import deepcopy
from orderbookmdp.order_book.constants import BUY, SELL
from orderbookmdp.rl.market_order_envs import MarketOrderEnvBuySell
from itertools import tee


class CopyAbleMarketOrderEnvBuySell(MarketOrderEnvBuySell):
    def __deepcopy__(self, memo):
        deepcopy_method = self.__deepcopy__
        self.__deepcopy__ = None
        os = self.os
        os, os_copy = tee(os)
        self.os = None
        cp = deepcopy(self, memo)
        self.__deepcopy__ = deepcopy_method
        self.os = os
        cp.os = os_copy
        cp.__deepcopy__ = deepcopy_method
        # custom treatments
        # for instance: cp.id = None
        return cp


def break_condition(env, t, T):
    return env.capital/env.initial_funds < 0.9 + 0.1*(t/T)


def back_track_opt_paths(env, T, path=()):
    if len(path) == T:
        return path
    paths = []
    for action in [BUY, SELL]:
        env_copy = deepcopy(env)
        env_copy.step(action)
        if not break_condition(env_copy, len(path) + 1, T):
            paths += back_track_opt_paths(env_copy, T, path + (action,))
    return paths


if __name__ == '__main__':
    env = CopyAbleMarketOrderEnvBuySell()
    env.reset()
    T = 10
    paths = back_track_opt_paths(env, T)
    print(paths)
