import gc
import os
import random
import re

import numpy as np
import pandas as pd
import ujson


def load_orders(path):
    """
    Yields orders from a saved feather :py:class:`pandas.DataFrame`.

    Parameters
    ----------
    path: str
        Path to the saved feather dataframe

    Yields
    -------
    order
        An external order from the dataframe

    """

    # TODO, test appending multiple order dataframes for faster loading?
    df = pd.read_feather(path)
    for order in df.itertuples():
        yield order


def orderstream(order_paths='../../../data/feather/', snapshot_paths='../../../data/snap_json/', max_sequence_skip=1,
                random_start=False, **kwargs):
    """
    Generates a stream of orders, either a snapshot of the order book is returned when a disruption in the order stream
    happens or the next order is yielded.

    Parameters
    ----------
    order_paths: str
        Path to the orders
    snapshot_paths: str
        Path to the snapshots

    Yields
    -------
        order: list, snapshot: dict
            The first yield will have a snapshot. Then orders will be yielded with the snapshot as None.


    """
    order_files = os.listdir(order_paths)
    snap_files = os.listdir(snapshot_paths)

    order_files = sorted(order_files)
    snap_files = sorted(snap_files)

    snap_sequences = np.array([int(re.search(r'\d+', snap_sequence).group()) for snap_sequence in snap_files])

    while True:

        if not random_start:
            with open(snapshot_paths + snap_files[0]) as f:
                snap = ujson.load(f)
        else:
            random_snap = random.choice(snap_files)
            random_snap_seq = ''.join(filter(str.isdigit, random_snap))

            order_files_ = []

            for order_file in order_files:
                max_order_file_seq = int(order_file.split('_')[2].split('.')[0])
                if max_order_file_seq >= int(random_snap_seq):
                    order_files_.append(order_file)

            with open(snapshot_paths + random_snap) as f:
                snap = ujson.load(f)

        snap_seq = snap['sequence']
        prev_order_seq = snap_seq

        yield None, snap

        for orderfile in order_files:
            orders = load_orders(order_paths + orderfile)
            for order_arr in orders:
                order_seq = order_arr.sequence
                if order_seq < snap_seq:
                    prev_order_seq = order_seq
                    # prev_time = order_arr.time
                    continue
                else:

                    # TODO test a bigger gap when training but not testing
                    # A gap has occured, a new snapshot should be used.
                    if order_seq > prev_order_seq + max_sequence_skip:
                        # print(order_seq - prev_order_seq) # Check sequence skip
                        snap_k = (order_seq < snap_sequences).argmax()
                        with open(snapshot_paths + snap_files[snap_k]) as f:
                            snap = ujson.load(f)
                        yield None, snap
                        snap_seq = snap['sequence']

                    else:
                        yield order_arr, None

                prev_order_seq = order_seq
                # prev_time = order_arr.time
            gc.collect()


if __name__ == '__main__':
    import time
    start_time = None
    start_time_init = False
    t = time.time()

    for i in range(5):
        print_ = True
        ords = orderstream(max_sequence_skip=100, random_start=True)
        for mess, snap in ords:
            if snap:
                print('snap')
            else:
                if print_:
                    print(mess.time)
                    print_ = False
                if not start_time_init:
                    start_time = mess.time
                    start_time_init = True
                else:
                    if start_time == mess.time:
                        break
        print(time.time() - t)

    ords = orderstream(max_sequence_skip=100)
    for mess, snap in ords:
        if snap:
            print('snap')
        else:
            if not start_time_init:
                start_time = mess.time
                start_time_init = True
            else:
                if start_time == mess.time:
                    break
    print(time.time() - t)
