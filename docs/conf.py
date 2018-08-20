# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import inspect
import os
import shutil
import sys

__location__ = os.path.join(os.getcwd(), os.path.dirname(
    inspect.getfile(inspect.currentframe())))

sys.path.insert(0, os.path.join(__location__, '../src'))

# -- Run sphinx-apidoc ------------------------------------------------------
# This hack is necessary since RTD does not issue `sphinx-apidoc` before running
# `sphinx-build -b html . _build/html`. See Issue:
# https://github.com/rtfd/readthedocs.org/issues/1139
# DON'T FORGET: Check the box "Install your project inside a virtualenv using
# setup.py install" in the RTD Advanced Settings.
# Additionally it helps us to avoid running apidoc manually

try:  # for Sphinx >= 1.7
    from sphinx.ext import apidoc
except ImportError:
    from sphinx import apidoc

output_dir = __location__
module_dir = os.path.join(__location__[:-5], "src/orderbookmdp")

try:
    import sphinx
    from distutils.version import LooseVersion

    cmd_line_template = "sphinx-apidoc -f -o {outputdir} {moduledir}"
    cmd_line = cmd_line_template.format(outputdir=output_dir, moduledir=module_dir)

    args = cmd_line.split(" ")
    if LooseVersion(sphinx.__version__) >= LooseVersion('1.7'):
        args = args[1:]

    apidoc.main(args)
except Exception as e:
    print("Running `sphinx-apidoc` failed!\n{}".format(e))

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.coverage',
    'sphinx.ext.doctest',
    'sphinx.ext.extlinks',
    'sphinx.ext.ifconfig',
    'sphinx.ext.napoleon',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
    'sphinx.ext.mathjax'
]
if os.getenv('SPELLCHECK'):
    extensions += 'sphinxcontrib.spelling',
    spelling_show_suggestions = True
    spelling_lang = 'en_US'

source_suffix = '.rst'
master_doc = 'index'
project = 'OrderBookMDP'
year = '2018'
author = 'Olle Dahlen'
copyright = '{0}, {1}'.format(year, author)
version = release = '0.1.2'

pygments_style = 'trac'
templates_path = ['.']
extlinks = {
    'issue': ('https://github.com/valldabo2/python-orderbookmdp/issues/%s', '#'),
    'pr': ('https://github.com/valldabo2/python-orderbookmdp/pull/%s', 'PR #'),
}
# on_rtd is whether we are on readthedocs.org
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

if not on_rtd:  # only set the theme if we're building docs locally
    html_theme = 'sphinx_rtd_theme'

html_use_smartypants = True
html_last_updated_fmt = '%b %d, %Y'
html_split_index = False
html_sidebars = {
   '**': ['searchbox.html', 'globaltoc.html', 'sourcelink.html'],
}
html_short_title = '%s-%s' % (project, version)

# napoleon_use_ivar = True
# napoleon_use_rtype = False
# napoleon_use_param = False

# -- Extension configuration -------------------------------------------------


def skip(app, what, name, obj, skip, options):
    if name == "__init__":
        return False
    return skip

def setup(app):
    app.connect("autodoc-skip-member", skip)

autodoc_member_order = 'bysource'
