# -*- coding: utf-8 -*-
""" All indexes for accessing information in different lists such as a trade, order etc.

Attributes
----------
BUY = 0
SELL = 1
Limit Order : [side, price, size, trader_id, order_id]
Trade : (trader_id, counter_part_id, price, size, order_id, side, time)
Order in Book : (order_id, size, side, price)
Quotes : (ask, ask_v, bid, bid_v)
External Trader = -1
Snapshot Order : [price, size, external_market_order_id]

"""
BUY = 0
SELL = 1
# Limit Order: [side, price, size, trader_id, order_id]
O_SIDE = 0
O_PRICE = 1
O_SIZE = 2
O_TRADER_ID = 3
O_ID = 4
# Trade : (trader_id, counter_part_id, price, size, order_id, side, time)
T_ID = 0
TC_ID = 1
T_PRICE = 2
T_SIZE = 3
T_OID = 4
T_SIDE = 5
T_TIME = 6
# Order in Book : (order_id, size, side, price)
OIB_ID = 0
OIB_SIZE = 1
OIB_SIDE = 2
OIB_PRICE = 3
# Quotes : (ask, ask_v, bid, bid_v)
Q_ASK = 0
Q_ASKV = 1
Q_BID = 2
Q_BIDV = 3
# External Trader
EXT_ID = -1
# Snapshot Order : [price, size, external_market_order_id]
SO_PRICE = 0
SO_SIZE = 1
SO_EXT_ID = 2
