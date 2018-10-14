from src.orderbookmdp.rl.multi_agent_envs import MultiAgentOrderEnv, get_actions_dict
import time


def run_env(n_episodes=5):
    trader_id = 1
    random_agent_list = []
    agent_list = []
    for i in range(3):
        random_agent_list.append('dist_' + str(trader_id))
        trader_id += 1
        agent_list.append('dist_' + str(trader_id))
        trader_id += 1
    for i in range(3):
        random_agent_list.append('spread_' + str(trader_id))
        trader_id += 1
        agent_list.append('spread_' + str(trader_id))
        trader_id += 1
    for i in range(3):
        random_agent_list.append('market_' + str(trader_id))
        trader_id += 1
        agent_list.append('market_' + str(trader_id))
        trader_id += 1

    t = time.time()
    env = MultiAgentOrderEnv(agent_list, random_agent_list)
    for i in range(n_episodes):
        k = 0
        action_timer = time.time()
        obs = env.reset()
        print('reset')
        done = {'__all__': False}
        while not done['__all__']:
            action_dict = get_actions_dict(obs)
            obs, reward, done, info = env.step(action_dict)
            k += 1
            if k % 10000 == 0:
                break
        print('Actions per sec:{:.2f}'.format(k / (time.time() - action_timer)))
    print('{} episodes took {:.2f} seconds'.format(n_episodes,
                                                   time.time() - t))


def speed_test_environments():
    print('################### SPEED TEST ###################')
    run_env(4)


if __name__=='__main__':
    speed_test_environments()
