# Copyright 2012 the rootpy developers
# distributed under the terms of the GNU General Public License
from .. import QROOT
from ..pythonized import pythonized
from .core import Plottable


class Line(Plottable, pythonized(QROOT.TLine)):

    def __init__(self, *args, **kwargs):

        super(Line, self).__init__(*args)
        self._post_init(**kwargs)


class Ellipse(Plottable, pythonized(QROOT.TEllipse)):

    def __init__(self, *args, **kwargs):

        super(Ellipse, self).__init__(*args)
        self._post_init(**kwargs)

#TODO: add more shapes here
