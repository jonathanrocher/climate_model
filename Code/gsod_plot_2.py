""" Implement a Chaco data plotter that loads pandas data from an hdf5 file.
The plotter contains zoom, pan, and legend highlighter tools and preserve
the tick labels.
"""

# Major library imports
import numpy as np
from numpy.random import randn
import pandas
import time

# Enthought imports
from enable.api import ComponentEditor
from traits.api import HasTraits, Instance, Dict, File, Bool
from traitsui.api import View, Item, VGroup

# Chaco imports
from chaco.api import ArrayPlotData, ToolbarPlot, Legend, PlotAxis
from chaco.tools.api import PanTool, ZoomTool, LegendTool, LegendHighlighter
# for datetime tick labels
from chaco.scales.api import CalendarScaleSystem
from chaco.scales_tick_generator import ScalesTickGenerator

import chaco_pandas
reload(chaco_pandas)
from chaco_pandas import pandas_hdf_to_data_dict2, pandas2array_dict

colors = ["black", "green", "lightgreen", "blue", "lightblue", "red",
          "pink", "yellow", "darkgray", "silver"]

def attach_tools(plot):
    """ Little utility function to attach plot tools: zoom, pan and legend tools
"""
    plot.tools.append(PanTool(plot))
    zoom = ZoomTool(component=plot, tool_mode="range", axis = "index", always_on=False)
    plot.overlays.append(zoom)
    # Show legend
    plot.legend.visible = True
    plot.legend.align = "lr"
    # Legend Highlighter: allows to click on the line in the legend to show that one
    highlight_tool = LegendHighlighter(plot.legend)
    plot.tools.append(highlight_tool)

class GSODDataPlotterView(HasTraits):
    """ Application of the zoom tool to the GSOD plotting tool.
Load a HDF file containing one or more timeseries and plot the entire data inside.
The zoom tool allows to explore a subset of it. The legend allows to (de)select some
timeseries.
"""
    data_file = File()
    ts_data = Dict()
    ts_plot = Instance(ToolbarPlot)
    index_is_dates = Bool()
    
    traits_view = View(
            VGroup(Item('data_file', style = 'simple', label="HDF file to load"),
                   Item('ts_plot', editor=ComponentEditor(size=(800, 600)),
                        show_label=False),),
            title='Chaco Plot with file loader and legend highlighter',
            width=900, height=800, resizable=True)

    def __init__(self, pandas_list = [], array_dict = {}, *args, **kw):
        """ If a (list of) pandas or a dict of arrays is passed, load them up.
        """
        ts_data = {}
        super(GSODDataPlotterView, self).__init__(*args, **kw)
        if not isinstance(pandas_list, list):
            pandas_list = [pandas_list]
        if pandas_list:
            array_dict, self.index_is_dates = pandas2array_dict(pandas_list)
            ts_data.update(array_dict)
        if array_dict:
            ts_data.update(ts_dict)
        self.ts_data = ts_data # Now trigger the plot redraw

    def _data_file_changed(self):
       """ Update the data from the HDF5 file.
       """
       self.ts_data, self.index_is_dates = pandas_hdf_to_data_dict2(self.data_file)
       assert("index" in self.ts_data)

    def _ts_data_changed(self):
        """ Dataset has changed: update the plot.
        ENH: add the possibility to pass a dict to ArrayPlotData.
        """
        print "data changed: updating the plot..."
        arr_data = ArrayPlotData()
        for k,v in self.ts_data.items():
            arr_data.set_data(k,v)
        self.ts_plot = ToolbarPlot(arr_data)
        for i, k in enumerate([k for k in self.ts_data.keys() if k != "index"]):
            self.ts_plot.plot(("index", k), name = k, color = colors[i % len(colors)])
            break
        if self.index_is_dates:
            # Index was an array of datetime: overwrite the x axis
            self.ts_plot.x_axis = None
            x_axis = PlotAxis(self.ts_plot, orientation="bottom",
                              tick_generator=ScalesTickGenerator(scale=CalendarScaleSystem()))
            self.ts_plot.overlays.append(x_axis)
            self.ts_plot.x_grid.tick_generator = x_axis.tick_generator
            
        if self.data_file:
            self.ts_plot.title = "Time series visualization from %s" % self.data_file
        else:
            self.ts_plot.title = "Time series visualization"
        attach_tools(self.ts_plot)
    
if __name__ == "__main__":
    viewer = GSODDataPlotterView()
    viewer.configure_traits()



    
