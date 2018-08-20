from types import SimpleNamespace


def limit_message(side: int, size: float, price: float, trader_id: int) -> SimpleNamespace:
    """
    Returns a limit order message

    Parameters
    ----------
    side: int
        BUY or SELL, see :py:mod:´OrderBookRL.order_book.constants´
    size: float
        Size of the order.
    price: float
        Price of the order
    trader_id: int
        Id of the trader sending the order

    Returns
    -------
    message: SimpleNamespace
        The limit order message

    """
    return SimpleNamespace(side=side, size=size, price=price, trader_id=trader_id,
                           order_type='limit', type='received')


def market_message(side: int, size: float, trader_id: int, funds=None):
    """
    Returns a market order message

    Parameters
    ----------
    side: int
        BUY or SELL, see :py:mod:´OrderBookRL.order_book.constants´
    size: float
        Size of the order.
    trader_id: int
        Id of the trader sending the order
    funds: float, optional
        If to use funds instead of size for the market order. Will be used if provided.

    Returns
    -------
    message: SimpleNamespace
        The market order message

    """
    if funds:
        return SimpleNamespace(side=side, trader_id=trader_id, funds=funds, size=-1,
                               type='received', order_type='market')
    else:
        return SimpleNamespace(side=side, size=size, trader_id=trader_id,
                               type='received', order_type='market')


def cancel_message(order_id: int) -> SimpleNamespace:
    """
    Returns a cancellation message

    Parameters
    ----------
    order_id: int
        The order id of the order to be cancelled

    Returns
    -------
    message: SimpleNamespace
        The cancellation message

    """
    return SimpleNamespace(order_id=order_id, type='done', reason='canceled')


def change_message(order_id: int, size: float) -> SimpleNamespace:
    """
    Returns a order change message

    Parameters
    ----------
    order_id: int
        The order id of the order to be updated
    size: float
        The new size of the order

    Returns
    -------
    message: SimpleNamespace
        The order change message

    """
    return SimpleNamespace(order_id=order_id, size=size, type='change')
