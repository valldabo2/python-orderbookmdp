========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - | |travis| |appveyor| |requires|
        | |codecov|
    * - package
      - | |version| |supported-versions| |supported-implementations|

.. |docs| image:: https://python-orderbookmdp.readthedocs.io/en/latest/?badge=latest
    :target: https://python-orderbookmdp.readthedocs.io/en/latest/
    :alt: Documentation Status

.. |travis| image:: https://travis-ci.org/valldabo2/python-orderbookmdp.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/valldabo2/python-orderbookmdp

.. |appveyor| image:: https://ci.appveyor.com/api/projects/status/github/valldabo2/python-orderbookmdp?branch=master&svg=true
    :alt: AppVeyor Build Status
    :target: https://ci.appveyor.com/project/valldabo2/python-orderbookmdp

.. |requires| image:: https://requires.io/github/valldabo2/python-orderbookmdp/requirements.svg?branch=master
    :alt: Requirements Status
    :target: https://requires.io/github/valldabo2/python-orderbookmdp/requirements/?branch=master

.. |codecov| image:: https://codecov.io/github/valldabo2/python-orderbookmdp/coverage.svg?branch=master
    :alt: Coverage Status
    :target: https://codecov.io/github/valldabo2/python-orderbookmdp

.. |version| image:: https://img.shields.io/pypi/v/orderbookmdp.svg
    :alt: PyPI Package latest release
    :target: https://pypi.python.org/pypi/orderbookmdp/

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/orderbookmdp.svg
    :alt: Supported versions
    :target: https://pypi.python.org/pypi/orderbookmdp

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/orderbookmdp.svg
    :alt: Supported implementations
    :target: https://pypi.python.org/pypi/orderbookmdp


.. end-badges

A package for simulating a limit order market as an OpenAI env.

* Free software: MIT license

Installation
============

::

    pip install orderbookmdp

Documentation
=============

https://python-orderbookmdp.readthedocs.io/

Development
===========

To run the all tests run::

    tox

Note, to combine the coverage data from all the tox environments run:

.. list-table::
    :widths: 10 90
    :stub-columns: 1

    - - Windows
      - ::

            set PYTEST_ADDOPTS=--cov-append
            tox

    - - Other
      - ::

            PYTEST_ADDOPTS=--cov-append tox
