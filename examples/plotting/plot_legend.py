#!/usr/bin/env python
"""
==================
Legend Positioning
==================

This example demonstrates how to easily position and size a legend using
rootpy.
"""
print __doc__
from rootpy.plotting import Hist, Canvas, Legend, get_style, set_style
from rootpy.plotting.utils import draw
from rootpy.interactive import wait
from itertools import product

style = get_style('ATLAS')
style.SetLegendBorderSize(1)
set_style(style)


hists = [
    Hist(1, 0, 1, color='red', legendstyle='F', title='Red'),
    Hist(1, 0, 1, color='blue', legendstyle='F', title='Blue'),
]

# coordinates in NDC
canvas = Canvas()
xaxis, yaxis = canvas.axes()
xaxis.title = 'X'
yaxis.title = 'Y'

for xloc, yloc in product(('left', 'right'), ('upper', 'lower')):
    location = '{0} {1}'.format(yloc, xloc)
    legend = Legend(hists, x=0.02, y=0.02, width=0.45,
                    anchor=location,
                    reference=location,
                    header=location)
    legend.Draw()

# absolute pixel coordinates
canvas_pixels = Canvas()
left, right, bottom, top = canvas.margin_pixels
xaxis, yaxis = canvas_pixels.axes()
xaxis.title = 'X'
yaxis.title = 'Y'

legend = Legend(hists, x=20, y=20, width=300, margin=100,
                anchor='lower left',
                reference='lower left',
                pixels=True)
legend.Draw()

legend = Legend(hists, x=20, y=20, width=300, margin=50, entryheight=50,
                anchor='upper right',
                reference='upper right',
                pixels=True)
legend.Draw()

canvas_sidelegend = Canvas()
left, right, bottom, top = canvas_sidelegend.margin_pixels
xaxis, yaxis = canvas_sidelegend.axes()
xaxis.title = 'X'
yaxis.title = 'Y'

canvas_sidelegend.margin = (0.15, 0.3, 0.15, 0.05)
legend = Legend(hists, x=20, y=20, width=200, margin=80,
                anchor='upper left',
                reference='upper right',
                pixels=True)
legend.Draw()

wait()
