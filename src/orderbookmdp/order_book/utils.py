

def to_int(price: float, multiplier: int):
    """ Converts a price to an integer.

    :math:`price_{int} = int(price_{float}*multiplier)`

    Parameters
    ----------
    price : float
    multiplier : int

    Returns
    -------
    price : int

    """
    return int((price+10e-10)*multiplier)


def to_float(price: int, tick_dec: int, multiplier: int):
    """ Converts a price to an float.

    :math:`price_{float} = price_{int}/multiplier`

    Parameters
    ----------
    price : int
    tick_dec: int
    multiplier : int

    Returns
    -------
    price : float

    """
    return round(price/float(multiplier), tick_dec)
