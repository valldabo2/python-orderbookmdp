import gc
import os
import random
import re
from copy import deepcopy

import numpy as np
import pandas as pd
import ujson
from sortedcontainers.sortedlist import SortedList

MESSAGE_TYPES = {'received', 'done', 'change'}


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

    order_paths = order_paths
    snapshot_paths = snapshot_paths

    order_files = os.listdir(order_paths)
    snap_files = os.listdir(snapshot_paths)

    order_files = SortedList(order_files, key=lambda x: int(x.split('_')[0]))

    snap_files = sorted(snap_files)
    snap_files_ = []
    min_order_files_seq = int(order_files[0].split('_')[1])
    for snap_file in snap_files:
        snap_seq_ = int(''.join(filter(str.isdigit, snap_file)))
        if snap_seq_ > min_order_files_seq:
            snap_files_.append(snap_file)

    snap_files = snap_files
    snap_sequences = np.array([int(re.search(r'\d+', snap_sequence).group()) for snap_sequence in snap_files])

    random_start = random_start
    max_seq_skip = max_sequence_skip

    while True:
        if random_start:
            snap_file = random.choice(snap_files)
            snap_seq = ''.join(filter(str.isdigit, snap_file))
            order_files_ = []
            for order_file in order_files:
                max_order_file_seq = int(order_file.split('_')[2].split('.')[0])
                if max_order_file_seq >= int(snap_seq):
                    order_files_.append(order_file)
            order_files_ = order_files_
        else:
            snap_file = snap_files[0]
            order_files_ = deepcopy(order_files)

        with open(snapshot_paths + snap_file) as f:
            snap = ujson.load(f)
        snap_sequence = snap['sequence']
        prev_order_seq = snap_sequence

        yield None, snap

        break_ = False
        for order_file in order_files_:
            orders = load_orders(order_paths + order_file)
            for order in orders:
                if order.sequence < snap_sequence:
                    pass
                else:
                    if order.sequence - prev_order_seq > max_seq_skip:
                        print('To large gap', order.sequence - prev_order_seq)

                        if random_start:
                            break_ = True
                            break
                        else:
                            snap_seq_k = (snap_sequences >= order.sequence).argmax()
                            snap_file = snap_files[snap_seq_k]
                            with open(snapshot_paths + snap_file) as f:
                                snap = ujson.load(f)
                            snap_sequence = snap['sequence']
                            yield None, snap
                    else:
                        if order.type in MESSAGE_TYPES:
                            yield order, None
                prev_order_seq = order.sequence
            gc.collect()
            if break_:
                break


if __name__ == '__main__':
    import time

    start_order_id = None
    start_order_type = None
    start_order_init = False
    init_snap = False
    t = time.time()
    print_ = True
    ords = orderstream(max_sequence_skip=10000, random_start=False)
    k = 0
    for mess, snap in ords:
        k += 1
        if snap:
            if not init_snap:
                print('snap')
                init_snap = True
        else:

            if k % 500000 == 0:
                print(mess.time)

            if print_:
                print(mess.time)
                print_ = False
            if not start_order_init:
                start_order_id = mess.order_id
                start_order_type = mess.type
                start_order_init = True

            else:
                if start_order_id == mess.order_id:
                    if start_order_type == mess.type:
                        break
