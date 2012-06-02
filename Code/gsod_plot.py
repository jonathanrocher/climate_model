""" ENAML VERSION
Implement a Chaco data plotter that loads pandas data from an hdf5 file
or directly from the object.
The plotter contains zoom, pan, and legend highlighter tools and preserve
the datetime tick labels.

TODO list:
- Catch the closing of the window and close the hdf file
- Rethink the layout of the window.
- Add more commonly used tools on these timeseries.
- support netCDF and other self describing files in addition to HDF
- Embed into a general application which contains the gsod_collect script to 
make a end-to-end mini-application with an ipython prompt. Use envisage task (or 
canopy?).
"""

# Major library imports
import os
import json
import pandas
import time
import numpy as np

# Enthought imports
from enable.api import ComponentEditor
from traits.api import HasTraits, Instance, Dict, File, Bool, Enum, List, \
    on_trait_change, Int, Str, Any
from traitsui.api import View, Item, VGroup, HSplit

# Chaco imports
from chaco.api import ArrayPlotData, ToolbarPlot, PlotAxis
from chaco.tools.api import PanTool, ZoomTool, LegendHighlighter, \
    RangeSelection, RangeSelectionOverlay
# for datetime tick labels
from chaco.scales.api import CalendarScaleSystem
from chaco.scales_tick_generator import ScalesTickGenerator

# Use of Pandas in Chaco
from chaco_pandas import pandas_hdf_to_data_dict, pandas2array_dict

colors = ["black", "green", "red", "blue", "lightblue", "lightgreen", 
          "pink", "yellow", "darkgray", "silver"]

# Tool names:
CORRELATION = "Correlation"
MA = "Plot vs Moving averages"

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
    # UI controls
    data_file = File()

    # Tool controls
    tool_list = List([MA, CORRELATION])
    tool_chooser = Enum(values="tool_list")
    ts_list = List()
    ts1_chooser = Enum(values="ts_list")
    ts2_chooser = Enum(values="ts_list")
    # Moving average window size (in number of observations)
    ma_window_size = Int(0) 
    # Analysis details
    ts_analysis_details = Str("No details available")
    
    # Data
    ts_data = Dict()
    arr_plot_data = Instance(ArrayPlotData, ())
    times_ds = Any()   # arraydatasource for the time axis data
    index_is_dates = Bool()

    # Plots
    ts_plot = Instance(ToolbarPlot, ())
    ts_analysis_plot = Instance(ToolbarPlot, ())

    def trait_view(self, view):
        """ Build the view. The local namespace is 
        """
        return View(
            VGroup(Item('data_file', style='simple', label="HDF file to load"), 
                   HSplit(Item('ts_plot', editor=ComponentEditor(size=(400, 600)), 
                               show_label=False),
                          VGroup(Item('tool_chooser', show_label = True, label="Choose tool"),
                                 Item('ts1_chooser', label="TS 1"),
                                 Item('ts2_chooser', label="TS 2",
                                      visible_when="tool_chooser in ['%s']" % CORRELATION),
                                 Item('ma_window_size', label="MA window size",
                                      visible_when="tool_chooser in ['%s']" % MA),
                                 Item('ts_analysis_plot', editor=ComponentEditor(size=(400, 600)), 
                                      show_label=False),
                                 Item('ts_analysis_details', show_label = False, style = 'readonly', 
                                      visible_when=("tool_chooser in ['%s']" % CORRELATION))),),
                            ),
            title='Time-series plotter and analyzer',
            width=1300, height=800, resizable=True)

    def __init__(self, pandas_list = [], array_dict = {}, *args, **kw):
        """ If a (list of) pandas or a dict of arrays is passed, load them up. 
        """
        # Initialize the data content of the analysis tool
        ts_data = {}
        super(GSODDataPlotterView, self).__init__(*args, **kw)
        if not isinstance(pandas_list, list):
            pandas_list = [pandas_list]
        if pandas_list:
            array_dict_from_pandas, self.index_is_dates = pandas2array_dict(pandas_list)
            ts_data.update(array_dict_from_pandas)
        if array_dict:
            ts_data.update(array_dict)

        if ts_data:
            # Now trigger the plot redraw
            self.ts_data = ts_data 
        

    def _data_file_changed(self):
       """ Update the data from the HDF5 file.
       """
       ts_data, self.index_is_dates = pandas_hdf_to_data_dict(self.data_file)
       assert("index" in ts_data)
       self.ts_data = ts_data

    def _ts_data_changed(self):
        """ Dataset has changed: update the plots.
        ENH: add the possibility to pass a dict to ArrayPlotData constructor.
        """
        for k,v in self.ts_data.items():
            self.arr_plot_data.set_data(k,v)
        self.ts_list = self.ts_data.keys()
        self.update_main_plot()
        self.update_analysis_plot()
    
    def update_main_plot(self):
        """ Build main plot
        """
        self.ts_plot = ToolbarPlot(self.arr_plot_data)
        for i, k in enumerate([k for k in self.ts_data.keys() if k != "index"]):
            renderer = self.ts_plot.plot(("index", k), name = k, color = colors[i % len(colors)])[0]
        if self.index_is_dates:
            # Index was an array of datetime: overwrite the x axis
            self.ts_plot.x_axis = None
            x_axis = PlotAxis(self.ts_plot, orientation="bottom",
                              tick_generator=ScalesTickGenerator(scale=CalendarScaleSystem()))
            self.ts_plot.overlays.append(x_axis)
            self.ts_plot.x_grid.tick_generator = x_axis.tick_generator
            
        if self.data_file:
            self.ts_plot.title = ("Time series visualization from %s" 
                                  % (os.path.split(self.data_file)[1]))
        else:
            self.ts_plot.title = "Time series visualization"
        attach_tools(self.ts_plot)

        # Attach the range selection to the last renderer; any one will do
        self.ts_plot.tools.append(RangeSelection(renderer, left_button_selects = False,
            auto_handle_event = False))
        # Attach the corresponding overlay
        self._range_selection_overlay = RangeSelectionOverlay(renderer,
                                    metadata_name="selections")
        self.ts_plot.overlays.append(self._range_selection_overlay)
        # Grab a reference to the Time axis datasource and add a listener to its
        # selections metadata
        self.times_ds = renderer.index
        self.times_ds.on_trait_change(self._selections_changed)

    def _selections_changed(self, event):
        """ Selection of a time range on the first plot will triger a redraw of 
        the correlation plot if present.
        """
        if self.tool_chooser != CORRELATION:
            return
        if not isinstance(event, dict) or "selections" not in event:
            return
        corr_index = self.corr_renderer.index
        selections = event["selections"]
        if selections is None:
            corr_index.metadata.pop("selections", None)
            return
        else:
            low, high = selections
            data = self.times_ds.get_data()
            low_ndx = data.searchsorted(low)
            high_ndx = data.searchsorted(high)
            corr_index.metadata["selections"] = np.arange(low_ndx, high_ndx+1, 1, dtype=int)
            self.ts_analysis_plot.request_redraw()

    @on_trait_change("tool_chooser, ts1_chooser, ts2_chooser, ma_window_size")
    def update_analysis_plot(self):
        """ Build analysis plot
        """
        self.ts_analysis_plot = ToolbarPlot(self.arr_plot_data)
        if self.tool_chooser == CORRELATION:
            self.corr_renderer = self.ts_analysis_plot.plot((self.ts1_chooser, 
                            self.ts2_chooser), type = "scatter", color = "blue")[0]
            self.ts_analysis_plot.title = "%s plotted against %s" % (self.ts1_chooser, self.ts2_chooser)
            self.ts_analysis_plot.index_axis.title = self.ts1_chooser
            self.ts_analysis_plot.value_axis.title = self.ts2_chooser
        elif self.tool_chooser == MA and self.ma_window_size > 0:
            ts1_ma = pandas.rolling_mean(self.arr_plot_data.get_data(self.ts1_chooser),
                                         self.ma_window_size)
            self.arr_plot_data.set_data("ts1_ma", ts1_ma)
            self.ts_analysis_plot.plot(("index", self.ts1_chooser), type = "scatter", color = "blue")
            self.ts_analysis_plot.plot(("index", "ts1_ma"), type = "line", color = "blue")
        
    @on_trait_change("tool_chooser, ts1_chooser, ts2_chooser")
    def update_analysis_details(self):
        if self.tool_chooser == CORRELATION:
            # Compute the correlation coefficients between the chosen TS
            ts1 = pandas.Series(self.ts_data[self.ts1_chooser])
            ts2 = pandas.Series(self.ts_data[self.ts2_chooser])
            import pdb
            pdb.set_trace()
            corr_coefs = ts1.corr(ts2), ts1.corr(ts2, method = 'spearman'), ts1.corr(ts2, method = 'kendall')    
            self.ts_analysis_details = ("Coefficients of correlation: Std = %5.3f, Spearman = %5.3f, Kendall = %5.3f." % corr_coefs)
            return 
        
if __name__ == "__main__":
    model = GSODDataPlotterView()
    import enaml
    with enaml.imports():
        from gsod_plot_view import StatsView
    view = StatsView(model=model)
    view.show()



    
