from src.orderbookmdp.rl.market_order_envs import MarketOrderEnv
from src.orderbookmdp.rl.dist_envs import SpreadEnv, DistEnv
import time


def run_env(env, n_episodes=5):
    t = time.time()
    for i in range(n_episodes):
        k = 0
        action_timer = time.time()
        obs = env.reset()
        done = False
        while not done:
            k += 1
            action = env.action_space.sample()  # [0, 0, 0, 0] #
            obs, reward, done, info = env.step(action)
        print('Actions per sec:{:.2f}, steps:{}'.format(k/(time.time() - action_timer), k))
    print('{} episodes took {:.2f} seconds'.format(n_episodes,
                                                   time.time()-t))


def speed_test_environments():
    print('################### SPEED TEST ###################')

    order_file_paths = '../data/feather/'
    snap_file_paths = '../data/snap_json/'
    # market_type = 'cyext'
    # ob_type = 'py'
    # price_level_type = 'deque'
    # price_levels_type = 'list'
    # print('Runs: {} {} {} {}'.format(market_type, ob_type, price_level_type, price_levels_type))
    # env = DistEnv(market_type=market_type, ob_type=ob_type, price_level_type=price_level_type,
    #               price_levels_type=price_levels_type, order_paths=order_file_paths, snapshot_paths=snap_file_paths,
    #               max_sequence_skip=150, random_start=False, max_episode_time='6hours')
    # run_env(env, 2)
    #
    # market_type = 'cyext'
    # ob_type = 'cy_price_book'
    # price_level_type = 'cydeque'
    # price_levels_type = 'cylist'
    # print('Runs: {} {} {} {}'.format(market_type, ob_type, price_level_type, price_levels_type))
    # env = SpreadEnv(market_type=market_type, ob_type=ob_type, price_level_type=price_level_type,
    #                 price_levels_type=price_levels_type, order_paths=order_file_paths, snapshot_paths=snap_file_paths,
    #                 max_sequence_skip=150, random_start=False, max_episode_time='6hours')
    # run_env(env, 2)

    market_type = 'cyext'
    ob_type = 'cy_price_book'
    price_level_type = 'cydeque'
    price_levels_type = 'cylist'
    print('Runs: {} {} {} {}'.format(market_type, ob_type, price_level_type, price_levels_type))
    env = MarketOrderEnv(order_paths=order_file_paths, snapshot_paths=snap_file_paths,
                         max_sequence_skip=15000, random_start=False, max_episode_time='8hours')
    run_env(env, 3)


if __name__=='__main__':
    speed_test_environments()
