import os

import feather
import numpy as np
import pandas as pd
import ujson


def reformat():
    data_dir = '../../../data/'

    files = os.listdir(data_dir + 'json/')  # noqa
    snap_files = sorted([filename for filename in files if 'snaps' in filename])

    for snapfile in snap_files:
        with open(data_dir + 'json/' + snapfile, 'r') as f:
            snaps = f.readlines()
            for snap in snaps:
                snap = ujson.loads(snap)
                seq = snap['sequence']
                print(seq)
                with open(data_dir + 'snap_json/snap_' + str(seq) + '.json', 'w') as snapf:
                    ujson.dump(snap, snapf)

    files = os.listdir(data_dir + 'json/')  # noqa
    mess_files = sorted([filename for filename in files if 'mess' in filename])

    keys = set(['order_type', 'reason', 'sequence', 'side', 'size', 'type', 'price', 'funds', 'order_id', 'time'])
    price_tick = 0.01
    price_dec = int(np.log10(1 / price_tick))

    # mess_files = mess_files[0:2]
    for k, messfile in enumerate(mess_files):

        print(k)
        messages = []
        with open(data_dir + 'json/' + messfile, 'r') as f:
            mess = f.readlines()
            for m in mess:
                ms = ujson.loads(m)
                ms = {k: v for k, v in ms.items() if k in keys}
                messages.append(ms)

        df = pd.DataFrame(messages)

        df['funds'] = df['funds'].astype(float)
        df['price'] = df['price'].astype(float).round(price_dec)
        df['size'] = df['size'].astype(float)
        df.replace('sell', 1, inplace=True)
        df.replace('buy', 0, inplace=True)
        df.side = df.side.fillna(-1)
        df.side = df.side.astype(int)
        df['trader_id'] = -1
        # df.time = pd.to_datetime(df.time)
        df.loc[df['size'].isnull(), 'size'] = -1

        start_seq = df['sequence'].values[0]
        end_seq = df['sequence'].values[-1]
        save_str = str(k) + '_' + str(start_seq) + '_' + str(end_seq) + '.feather'
        feather.write_dataframe(df, data_dir + 'feather/' + save_str)


if __name__ == '__main__':
    reformat()
