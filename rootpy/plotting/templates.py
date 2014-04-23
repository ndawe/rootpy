# Copyright 2012 the rootpy developers
# distributed under the terms of the GNU General Public License
from __future__ import absolute_import

import ROOT

from ..context import preserve_current_style
from .canvas import Canvas, Pad
from .hist import Hist
from .utils import draw


__all__ = [
    'RatioPlot',
]


class RatioPlot(Canvas):

    def __init__(self, width=None, height=None,
                 ratio_height=0.2, ratio_margin=0.05,
                 ratio_range=(0, 2), ratio_divisions=4,
                 xtitle=None, ytitle=None, ratio_title=None):

        style = ROOT.gStyle

        # plot dimensions in pixels
        if height is not None:
            figheight = baseheight = height
        else:
            figheight = baseheight = style.GetCanvasDefH()
        if width is not None:
            figwidth = basewidth = width
        else:
            figwidth = basewidth = style.GetCanvasDefW()

        # margins
        left_margin = style.GetPadLeftMargin()
        bottom_margin = style.GetPadBottomMargin()
        top_margin = style.GetPadTopMargin()
        right_margin = style.GetPadRightMargin()

        figheight += (ratio_height + ratio_margin) * figheight
        ratio_height += bottom_margin + ratio_margin / 2.

        super(RatioPlot, self).__init__(
            width=int(figwidth), height=int(figheight))
        self.SetMargin(0, 0, 0, 0)

        # top pad for histograms
        with self:
            main = Pad(0., ratio_height, 1., 1.)
            main.SetBottomMargin(ratio_margin / 2.)
            main.SetTopMargin(top_margin)
            main.SetLeftMargin(left_margin)
            main.SetRightMargin(right_margin)
            main.Draw()

        # bottom pad for ratio plot
        with self:
            ratio = Pad(0, 0, 1, ratio_height)
            ratio.SetBottomMargin(bottom_margin / ratio_height)
            ratio.SetTopMargin(ratio_margin / (2. * ratio_height))
            ratio.SetLeftMargin(left_margin)
            ratio.SetRightMargin(right_margin)
            ratio.Draw()

        # draw main axes
        with main:
            main_hist = Hist(1, 0, 1)
            main_hist.Draw('AXIS')

        # hide x-axis labels and title on main pad
        xaxis, yaxis = main_hist.xaxis, main_hist.yaxis
        xaxis.SetLabelOffset(1000)
        xaxis.SetTitleOffset(1000)
        # adjust y-axis title spacing
        yaxis.SetTitleOffset(
            yaxis.GetTitleOffset() * figheight / baseheight)

        # draw ratio axes
        with ratio:
            ratio_hist = Hist(1, 0, 1)
            ratio_hist.Draw('AXIS')

        # adjust x-axis label and title spacing
        xaxis, yaxis = ratio_hist.xaxis, ratio_hist.yaxis
        xaxis.SetLabelOffset(
            xaxis.GetLabelOffset() / ratio_height)
        xaxis.SetTitleOffset(
            xaxis.GetTitleOffset() / ratio_height)
        # adjust y-axis title spacing
        yaxis.SetTitleOffset(
            yaxis.GetTitleOffset() * figheight / baseheight)

        if ratio_range is not None:
            yaxis.SetLimits(*ratio_range)
            yaxis.SetRangeUser(*ratio_range)
            yaxis.SetNdivisions(ratio_divisions)

        if xtitle is not None:
            ratio_hist.xaxis.title = xtitle
        if ytitle is not None:
            main_hist.yaxis.title = ytitle
        if ratio_title is not None:
            ratio_hist.yaxis.title = ratio_title

        self.main = main
        self.main_hist = main_hist
        self.ratio = ratio
        self.ratio_hist = ratio_hist
        self.ratio_range = ratio_range

    def pad(self, region):
        if region == 'main':
            return self.main
        elif region == 'ratio':
            return self.ratio
        raise ValueError("RatioPlot region {0} does not exist".format(region))

    def cd(self, region=None):
        if region is not None:
            self.pad(region).cd()
        else:
            super(RatioPlot, self).cd()

    def axes(self, region):
        if region == 'main':
            return self.main_hist.xaxis, self.main_hist.yaxis
        elif region == 'ratio':
            return self.ratio_hist.xaxis, self.ratio_hist.yaxis
        raise ValueError("RatioPlot region {0} does not exist".format(region))

    def draw(self, region, objects, **kwargs):
        pad = self.pad(region)
        x, y = self.axes(region)
        if region == 'ratio' and self.ratio_range is not None:
            y = None
        draw(objects, pad=pad, xaxis=x, yaxis=y, same=True, **kwargs)
