import gc
import os

import feather
import numpy as np
import pandas as pd
import ujson
from sortedcontainers.sortedlist import SortedList
from tqdm import tqdm
from joblib import Parallel, delayed


def save_snaps_from_file_path(data_dir, snapfile):
    with open(data_dir + '/json/' + snapfile, 'r') as f:
        snaps = f.readlines()
        for snap in snaps:
            snap = ujson.loads(snap)
            try:
                seq = snap['sequence']
                path = data_dir + '/snap_json/snap_' + str(seq) + '.json'
                if not os.path.isfile(path):
                    with open(path, 'w') as snapf:
                        ujson.dump(snap, snapf)
            except:  # noqa
                pass


def reformat_messages(data_dir, k, keys, price_dec, messfile):
    messages = []
    with open(data_dir + '/json/' + messfile, 'r') as f:
        mess = f.readlines()
        for m in mess:
            ms = ujson.loads(m)
            ms = {k: v for k, v in ms.items() if k in keys}
            messages.append(ms)

    df = pd.DataFrame(messages)
    del messages
    try:
        df['funds'] = df['funds'].astype(float)
    except KeyError:
        pass
    try:
        df['price'] = df['price'].astype(float).round(price_dec)
    except KeyError:
        pass
    try:
        df['size'] = df['size'].astype(float)
    except KeyError:
        pass

    df.replace('sell', 1, inplace=True)
    df.replace('buy', 0, inplace=True)
    df.side = df.side.fillna(-1)
    df.side = df.side.astype(int)
    df['trader_id'] = -1
    # df.time = pd.to_datetime(df.time)
    df.loc[df['size'].isnull(), 'size'] = -1

    start_seq = df['sequence'].values[0]
    end_seq = df['sequence'].values[-1]
    save_str = str(k) + '_' + str(int(start_seq)) + '_' + str(int(end_seq)) + '.feather'
    feather.write_dataframe(df, data_dir + '/feather/' + save_str)
    del df
    gc.collect()


def reformat(data_dir='../../../data', cores=1):
    print('Reformats data from:', data_dir)
    files = os.listdir(data_dir + '/json/')  # noqa
    snap_files = SortedList([filename for filename in files if 'snaps' in filename],
                            key=lambda fn: pd.to_datetime(fn[:-11], format='%d_%m_%Y_%H_%M_%S'))

    try:
        os.makedirs(data_dir + '/snap_json/')
    except FileExistsError:
        pass

    Parallel(n_jobs=cores)(delayed(save_snaps_from_file_path)(data_dir, snapfile) for snapfile in tqdm(snap_files))

    files = os.listdir(data_dir + '/json/')  # noqa
    mess_files = SortedList([filename for filename in files if 'mess' in filename],
                            key=lambda fn: pd.to_datetime(fn[:-10], format='%d_%m_%Y_%H_%M_%S'))

    keys = {'order_type', 'reason', 'sequence', 'side', 'size', 'type', 'price', 'funds', 'order_id', 'time'}
    price_tick = 0.01
    price_dec = int(np.log10(1 / price_tick))

    try:
        os.makedirs(data_dir + '/feather/')
    except FileExistsError:
        pass

    Parallel(n_jobs=cores)(delayed(reformat_messages)(
        data_dir, k, keys, price_dec, messfile) for k, messfile in tqdm(enumerate(list((mess_files)))))


if __name__ == '__main__':
    reformat()
