from orderbookmdp import longest


def test_main():
    pass


def test_longest():
    assert longest([b'a', b'bc', b'abc']) == b'abc'
