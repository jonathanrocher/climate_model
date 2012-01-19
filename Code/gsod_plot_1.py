""" Implement a Chaco data plotter that loads pandas data from an hdf5 file.
A few tools are added to the plotter: zoom, pan, and legend highlighter.

WARNING: This is an simple implementation that simply uses the API for pytables
and Chaco. A deeper integration is possible to improve efficiency. In particular,
pytables can be plotter without loading the entire arrays into memory beforehand. 
"""
# Major library imports
import numpy as np
from numpy.random import randn
import pandas

# Enthought imports
from enable.api import ComponentEditor
from traits.api import HasTraits, Instance, Dict, File
from traitsui.api import View, Item, VGroup

# Chaco imports
from chaco.api import ArrayPlotData, ToolbarPlot, Legend
from chaco.tools.api import PanTool, ZoomTool, LegendTool, LegendHighlighter

colors = ["black", "green", "lightgreen", "blue", "lightblue", "red",
          "pink", "yellow", "darkgray", "silver"]

def pandas_hdf_to_data_dict(filename):
    """ Explore the content of the pandas store (HDF5) and create a dictionary
    of timeseries (numpy arrays) found in it. The key will be used as names
    for the curves. All indexes must be the same and stored once with key
    "index".

    2 possible approches here: dealing with v objects which are pytables
    groups containing directly the numpy arrays used for plotting, or
    reconstructing the pandas for the simplicity of the code. 

    FIXME: Add check that index is always the same. 
    """
    store = pandas.HDFStore(filename)
    pandas_list = [(key, store[key]) for key in store.handle.root._v_children.keys()]
    
    return pandas2array_dict(pandas_list, names = names)
    
def pandas2array_dict(pandas_list, names = []):
    """ Convert a list of pandas into a dict of arrays for plotting.
    They must have the same index. One of the entries in the output dict is one
    of these indexes with key "index". The arrays will be stored with the name
    of the pandas (.name attr), and if applicable the name of the column and of
    the item. Optionally a list of names to use can be passed to override the
    .name attribute. 
    """
    array_dict = {}
    # If there is only 1 pandas, make up a name
    if len(pandas_list) == 1 and not pandas_list[0].name and not names:
        names = ["pandas"]
    array_dict["index"] = np.array(pandas_list[0].index)
    for i, pandas_ds in enumerate(pandas_list):
        if names:
            name = names[i]
        elif pandas_ds.name:
            name = pandas_ds.name
        else:
            raise ValueError("The pandas number %s in the list doesn't have a "
                             "name." % i)
            
        if isinstance(pandas_ds, pandas.core.series.Series):
            entry = name
            array_dict[entry] = pandas_ds.values
        elif isinstance(pandas_ds, pandas.core.frame.DataFrame):
            for col_name,series in pandas_ds.iteritems():
                entry = name+"-"+col_name
                array_dict[entry] = pandas_ds[col_name].values
        else:
            for item, df in pandas_ds.iteritems():
                for col_name,series in df.iteritems():
                    entry = name+"-"+item+"-"+col_name
                    array_dict[entry] = df[col_name].values
    assert("index" in array_dict)
    return array_dict

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

    def __init__(self, pandas_list = [], array_dict = {}, *args, **kw):
        """ If a (list of) pandas or a dict of arrays is passed, load them up. 
        """
        super(GSODDataPlotterView, self).__init__(*args, **kw)
        if not isinstance(pandas_list, list):
            pandas_list = [pandas_list]
        if pandas_list:
            self.ts_data.update(pandas2array_dict(pandas_list))
        if array_dict:
            self.ts_data.update(ts_dict)

    def _data_file_changed(self):
       """ Update the data from the HDF5 file.
       """
       self.ts_data = pandas_hdf_to_data_dict(self.data_file)
       assert("index" in self.ts_data)
    
    def _ts_data_changed(self):
        """ Dataset has changed: update the plot.
        ENH: add the possibility to pass a dict to ArrayPlotData.
        """
        arr_data = ArrayPlotData()
        for k,v in self.ts_data.items():
            arr_data.set_data(k,v)
        self.ts_plot = ToolbarPlot(arr_data)
        for i, k in enumerate([k for k in self.ts_data.keys() if k != "index"]):
            self.ts_plot.plot(("index", k), name = k, color = colors[i % len(colors)])
        self.ts_plot.title = "Time series visualization from %s" % self.data_file
        attach_tools(self.ts_plot)
    
    traits_view = View(
            VGroup(Item('data_file', style = 'simple', label="HDF file to load"), 
                   Item('ts_plot', editor=ComponentEditor(size=(800, 600)), 
                        show_label=False),), 
            title='Chaco Plot with file loader and legend highlighter',
            width=900, height=800, resizable=True)

if __name__ == "__main__":
    viewer = GSODDataPlotterView()
    viewer.configure_traits()



    
