import numpy as np
from numba import jit


@jit(nopython=True, parallel=True)
def quote_differs(a, b):
    """ Numba Jitted version of if quote a and b differs.

    Parameters
    ----------
    a : quote
    b : quote

    Returns
    -------
    bool
        True of quote and and b differs, otherwise false
    """
    for i in range(4):
        if a[i] != b[i]:
            return True
    return False


def pct_change(new, old):
    """ Percentage change of new and old value.

    Parameters
    ----------
    new
    old

    Returns
    -------

    """
    return ((new - old) / old) * 100


@jit(nopython=True, parallel=True)
def beta_pdf(x, a, b):
    """ Returns pdf of a beta distribution given inputs x, alpha a and beta b.

    Parameters
    ----------
    x
    a
    b

    Returns
    -------

    """
    return np.power(x, a - 1) * np.power(1 - x, b - 1)


def get_pdf(pdf_type='beta'):
    """ Returns pdf of given input parameter.

    Parameters
    ----------
    pdf_type

    Returns
    -------

    """
    if pdf_type == 'beta':
        max_action = 10 + 3
        default_action = np.array([0.5, 3.0, 0.5, 3.0])
        return max_action, default_action, beta_pdf
