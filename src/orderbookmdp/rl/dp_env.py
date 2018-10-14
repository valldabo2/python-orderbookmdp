import numpy as np
from collections import deque
from orderbookmdp.rl.abstract_envs import ExternalMarketEnv
from orderbookmdp.order_book.constants import BUY, SELL, Q_BID, Q_ASK, T_SIZE, T_PRICE
HOLD = 2


class ForwardDpEnv(ExternalMarketEnv):
    def get_messages(self, action: np.array) -> tuple:
        pass

    def get_reward(self, trades: list) -> tuple:
        pass

    def send_messages(self, messages: tuple) -> (list, bool, dict):
        pass

    def get_private_variables(self) -> tuple:
        pass

    def seed(self, seed=None):
        pass

    @property
    def action_space(self):
        pass

    @property
    def observation_space(self):
        pass

    def send_order(self, side, amount):
        amount *= self.market.multiplier
        trades = self.market.ob.market_order_funds(amount, side, 1, self.market.time)
        if side == BUY:
            size = 0
            for trade in reversed(trades):
                size += trade[T_SIZE]
                self.market.ob.limit(trade[T_PRICE], SELL, trade[T_SIZE], -1, self.market.time)
            return size
        else: # SELL
            cap = 0
            for trade in reversed(trades):
                cap += trade[T_SIZE]*trade[T_PRICE]/self.market.multiplier
                self.market.ob.limit(trade[T_PRICE], BUY, trade[T_SIZE], -1, self.market.time)
            return cap


def get_diff_cap(env, T=100, capital=10000):
    diff_cap = np.zeros((T, 2, 3))
    for t in range(T):
        prev_quotes = env.market.ob.price_levels.get_quotes()
        prev_bid = prev_quotes[Q_BID]/env.market.multiplier

        print(prev_quotes, env.market.time)
        buy_poss = env.send_order(BUY, capital)
        sell_cap = env.send_order(SELL, capital)

        env.run_until_next_quote_update()
        quotes = env.market.ob.price_levels.get_quotes()
        bid = quotes[Q_BID]/env.market.multiplier

        diff_buy = buy_poss*bid - capital
        diff_cap[t, 0, BUY] = diff_buy

        diff_sell = sell_cap - capital
        diff_cap[t, 1, SELL] = diff_sell

        diff_hold = ((bid - prev_bid)/prev_bid) * capital
        diff_cap[t, 1, HOLD] = diff_hold

    diff_cap[:, 1, BUY] = diff_cap[:, 1, HOLD]

    return diff_cap


def prune(curr_cap, init_cap, T, t):
    return curr_cap/init_cap < 0.9 + t/T*0.1


def find_opt_path(diff_cap, init_cap, current_cap, T, t=0, opt_cap=-np.inf, opt_path=(), path=(), poss=0):

    if t == T:
        return path, current_cap
    if prune(current_cap, init_cap, T, t):
        return path, current_cap

    t += 1
    for a in range(3):
        if a == BUY:
            poss = 1
        elif a == SELL:
            poss = 0

        current_cap += diff_cap[t, poss, a]
        new_path = path + (a,)
        path, cap = find_opt_path(diff_cap, init_cap, current_cap, T, t, best_cap, best_path, new_path, poss)


if __name__ == '__main__':
    env = ForwardDpEnv()
    env.reset()

    T = 5
    cap = 10000
    diff_cap = get_diff_cap(env, T, cap)

    opt_path, opt_cap = find_opt_path(diff_cap, cap, cap, T)

