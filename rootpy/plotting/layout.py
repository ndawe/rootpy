# Copyright 2012 the rootpy developers
# distributed under the terms of the GNU General Public License
"""
This module implements various canvas layouts
"""
from __future__ import absolute_import

import ROOT

from .canvas import Canvas, Pad

__all__ = [
    'RatioPlot',
]


class RatioPlot(Canvas):

    def __init__(width=600,
                 top_height=600,
                 bottom_height=200,
                 left_margin=100,
                 right_margin=30,
                 bottom_margin=100,
                 top_margin=30):
        super(RatioPlot, self).__init__(
            width=width, height=top_height + bottom_height)
        self.SetMargin(0., 0., 0., 0.)
        top_pad = Pad(0., rect_hist[1] * 0.9, 1., 1., name='top', title='top')
        self.top = top_pad
