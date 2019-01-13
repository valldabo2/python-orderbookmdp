"""
Module that contains the command line app.

Why does this file exist, and why not put this in __main__?

  You might be tempted to import things from __main__ later, but that will cause
  problems: the code will get executed twice:

  - When you run `python -mnameless` python will execute
    ``__main__.py`` as a script. That means there won't be any
    ``nameless.__main__`` in ``sys.modules``.
  - When you import __main__ it will get executed again (as a module) because
    there's no ``nameless.__main__`` in ``sys.modules``.

  Also see (1) from http://click.pocoo.org/5/setuptools/#setuptools-integration
"""
import argparse

from orderbookmdp.data_all.download_gdax import download
from orderbookmdp.data_all.reformat_data import reformat

parser = argparse.ArgumentParser(description='Either downloads or reformats data from a directory.')

parser.add_argument('command', choices=['download', 'reformat'])
parser.add_argument('--download_time', type=str, default='10000 days', help='Time to download')
parser.add_argument('--dir', default='data', help='The directory to download or reformat')
parser.add_argument('--product', default='BTC-USD', help='The product to download')
parser.add_argument('--cores', default=1, type=int, help='Number of cores to use for reformating')

def main(args=None):
    args = parser.parse_args(args=args)
    if args.command == 'download':
        download(args.dir, args.download_time, args.product)
    elif args.command == 'reformat':
        reformat(args.dir, args.cores)
