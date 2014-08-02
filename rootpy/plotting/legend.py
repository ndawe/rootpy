# Copyright 2012 the rootpy developers
# distributed under the terms of the GNU General Public License
from __future__ import absolute_import

import numbers

import ROOT

from .. import QROOT, asrootpy
from ..base import Object
from .hist import HistStack
from .box import _Positionable, ANCHORS
from ..memory.keepalive import keepalive

__all__ = [
    'Legend',
]


class Legend(_Positionable, Object, QROOT.TLegend):
    _ROOT = QROOT.TLegend

    def __init__(self, entries,
                 x=0.05, y=0.05, width=0.4,
                 pixels=False,
                 anchor='upper right',
                 reference='upper right',
                 pad=None,
                 entryheight=0.06,
                 entrysep=0.02,
                 margin=0.3,
                 textfont=None,
                 textsize=None,
                 columns=1,
                 columnsep=0.02,
                 header=None):
        if pad is None:
            pad = asrootpy(ROOT.gPad.func())
        if not pad:
            raise RuntimeError("create a Pad before creating a Legend")

        if reference not in ANCHORS:
            raise ValueError(
                "'{0}' is not a valid reference. Use one of {1}".format(
                    reference, ', '.join(ANCHORS)))

        entries_is_list = False
        if isinstance(entries, numbers.Integral):
            # entries is the expected number of entries that will be included
            # in the legend
            nentries = entries
        else:
            # entries is a list of objects to become entries in the legend
            entries_is_list = True
            nentries = len(entries)

        if header is not None:
            nentries += 1

        if pixels:
            left, right, bottom, top = pad.margin_pixels
        else:
            left, right, bottom, top = pad.margin

        # x and y are relative to the axes frame corner defined by reference
        if 'left' in anchor:
            x += left
        elif pixels:
            x = pad.width_pixels - right - x
        else:
            x = 1. - x

        if 'lower' in anchor:
            y += bottom
        elif pixels:
            y = pad.height_pixels - top - y
        else:
            y = 1. - y

        if pixels:
            x /= float(pad.width_pixels)
            y /= float(pad.height_pixels)

        super(Legend, self).__init__(x, y, x, y, anchor=anchor)

        if pixels:
            pad_height_pixels = pad.height_pixels
            if entryheight <= 1:
                _entryheight = entryheight * pad_height_pixels
            else:
                _entryheight = entryheight
                entryheight /= pad_height_pixels
            if entrysep <= 1:
                _entrysep = entrysep * pad_height_pixels
            else:
                _entrysep = entrysep
                entrysep /= pad_height_pixels
            height = (_entryheight + _entrysep) * nentries - _entrysep
            if width <= 1:
                width *= pad.width_pixels - left - right
            self.width_pixels = width
            self.height_pixels = height
            if margin > 1:
                margin /= float(width)
            if columnsep > 1:
                columnsep /= float(width)
        else:
            width *= (1. - left - right)
            height = (entryheight + entrysep) * nentries - entrysep
            self.width = width
            self.height = height

        self.SetEntrySeparation(entrysep)
        self.SetMargin(margin)
        self.SetNColumns(columns)
        self.SetColumnSeparation(columnsep)
        if header is not None:
            self.SetHeader(header)

        # ROOT, why are you filling my legend with a
        # grey background by default?
        self.SetFillStyle(0)
        self.SetFillColor(0)

        if textfont is None:
            textfont = ROOT.gStyle.GetLegendFont()
        if textsize is None:
            textsize = ROOT.gStyle.GetTextSize()

        self.SetTextFont(textfont)
        self.SetTextSize(textsize)

        if entries_is_list:
            for thing in entries:
                self.AddEntry(thing)

    def Draw(self, *args, **kwargs):
        self.UseCurrentStyle()
        super(Legend, self).Draw(*args, **kwargs)

    def AddEntry(self, thing, label=None, style=None):
        """
        Add an entry to the legend.

        If `label` is None, `thing.GetTitle()` will be used as the label.

        If `style` is None, `thing.legendstyle` is used if present,
        otherwise `P`.
        """
        if isinstance(thing, HistStack):
            things = thing
        else:
            things = [thing]
        for thing in things:
            if getattr(thing, 'inlegend', True):
                if label is None:
                    label = thing.GetTitle()
                if style is None:
                    style = getattr(thing, 'legendstyle', 'P')
                super(Legend, self).AddEntry(thing, label, style)
                keepalive(self, thing)

    @property
    def primitives(self):
        return asrootpy(self.GetListOfPrimitives())
