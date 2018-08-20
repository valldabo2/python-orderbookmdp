import abc
from collections.__init__ import OrderedDict
from collections.__init__ import deque

from custom_inherit import DocInheritMeta
from sortedcontainers import SortedList

from orderbookmdp.order_book.constants import O_ID
from orderbookmdp.order_book.constants import O_SIZE
from orderbookmdp.order_book.constants import T_PRICE


class PriceLevel(metaclass=DocInheritMeta(style="numpy", abstract_base_class=True)):
    """ A price level containing orders.

    A price level contains orders with the same price. The total size of the level is the sum of all order sizes.

    Attributes
    ----------
    size : float
        The total size of all orders in the price level.
    orders
        All the orders in the price level.

    """

    def __init__(self):
        """ Initializes the size to 0.

        """
        self.size = 0

    def append(self, order: list):
        """ Adds an order to the end of the price level and adds the size.

        Parameters
        ----------
        order: list
            The order to be added.

        """
        self._add(order)
        self.size += order[O_SIZE]

    @abc.abstractmethod
    def _add(self, order: list):
        """ Adds the order to the end of the list

        Parameters
        ----------
        order: list
            The order to be added.

        """

    def delete(self, order: list):
        """ Deletes an order from the price level and removes the size.

        Parameters
        ----------
        order: list
            The order to be added.

        """
        self._remove(order)
        self.size -= order[O_SIZE]

    @abc.abstractmethod
    def _remove(self, order: list):
        """ Removes an order from the price level and removes the size.

        Parameters
        ----------
        order: list
            The order to be removed.

        """

    def update(self, order, diff: float):
        """ Updates an order from the price level with an added difference.

        Parameters
        ----------
        order: list
            The order to be added.

        """
        self.size += diff
        order[O_SIZE] += diff

    @abc.abstractmethod
    def get_first(self):
        """ Returns the first order of the price level

        Returns
        -------
        order
            The first order of the price level.

        """

    def delete_first(self, order: list):
        """ Deletes the first order from the price level and removes the size.

        Parameters
        ----------
        order: list
            The order to be removed.

        """
        self._remove_first()
        self.size -= order[O_SIZE]

    @abc.abstractmethod
    def _remove_first(self):
        """ Removes the first order from the price level.

        Parameters
        ----------
        order: list
            The order to be removed.

        """

    @abc.abstractmethod
    def is_not_empty(self) -> bool:
        """ Returns true if the price level is not empty

        Returns
        -------
        bool
            True if successful, False otherwise.

        """

    @abc.abstractmethod
    def get_last(self):
        """ Returns the last order of the price level

        Returns
        -------
        order
            The last order of the price level.

        """

    def delete_last(self, order: list):
        """ Deletes the last order from the price level and removes the size.

        Parameters
        ----------
        order: list
            The order to be removed.

        """
        self._remove_last()
        self.size -= order[O_SIZE]

    @abc.abstractmethod
    def _remove_last(self):
        """ Removes the last order from the price level.

        Parameters
        ----------
        order: list
            The order to be removed.

        """

    @abc.abstractmethod
    def is_empty(self):
        """ Returns true if the price level is empty

        Returns
        -------
        bool
            True if successful, False otherwise.

        """


class OrderedDictLevel(PriceLevel):
    def is_empty(self):
        return len(self.orders) == 0

    def __init__(self):
        PriceLevel.__init__(self)
        self.orders = OrderedDict()

    def _add(self, order):
        self.orders[order[O_ID]] = order

    def _remove(self, order: tuple) -> list:
        return self.orders.pop(order[O_ID])

    def is_not_empty(self) -> bool:
        return len(self.orders) > 0

    def __len__(self):
        return len(self.orders)

    def get_first(self) -> list:
        for order in self.orders.values():
            return order

    def _remove_first(self):
        self.orders.popitem(last=False)

    def get_last(self):
        for order in self.orders.values().__reversed__():
            return order

    def _remove_last(self):
        self.orders.popitem(last=True)


class DequeLevel(OrderedDictLevel):
    def __init__(self):
        PriceLevel.__init__(self)
        self.orders = deque()

    def _add(self, order: list):
        self.orders.append(order)

    def _remove(self, order: tuple):
        self.orders.remove(order)

    def get_first(self):
        return self.orders[0]

    def _remove_first(self):
        self.orders.popleft()

    def get_last(self):
        return self.orders[-1]

    def _remove_last(self):
        self.orders.pop()


class SortedTradesLevel(DequeLevel):
    def __init__(self):
        super(SortedTradesLevel, self).__init__()
        self.orders = SortedList(key=lambda trade: trade[T_PRICE])

    def _add(self, order: list):
        self.orders.add(order)

    def _remove_first(self):
        self.orders.pop()
