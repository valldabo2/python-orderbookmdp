import multiprocessing as mp


def rec(n):
    if n == 0:
        return (0,)
    return (n,) + rec(n-1)


def foo(n):
    list.append(rec(n))


if __name__ == '__main__':
    manager = mp.Manager()
    list = manager.list()
    p = mp.Process(target=foo, args=(10,))
    p.start()
    p2 = mp.Process(target=foo, args=(5,))
    p2.start()
    p.join()
    p2.join()

    print(list)
