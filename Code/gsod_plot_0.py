"""
"""
# Major library imports
from numpy import arange
from numpy.random import randn

# Enthought imports
from enable.api import ComponentEditor
from traits.api import HasTraits, Instance, Dict, File
from traitsui.api import View, Item

# Chaco imports
from chaco.api import ArrayPlotData, ToolbarPlot
    
class GSODDataPlotterView(HasTraits):
    """ Application of the zoom tool to the GSOD plotting tool.
    Load a HDF file containing one or more timeseries and plot the entire data inside.
    The zoom tool allows to explore a subset of it. The legend allows to (de)select some
    timeseries.
    """
    ts_data = Dict()
    ts_plot = Instance(ToolbarPlot, ())

    def _ts_data_default(self):
        """ Extract data from the HDF file. Return a dict containing 
        """
        return {"index" : arange(100), "ts1" : randn(100), "ts2" : randn(100)}

    def _ts_plot_default(self):
        """ Initialize the plot.
        """
        # Store the data
        arr_data = ArrayPlotData(x = self.ts_data["index"],
                                 y1 = self.ts_data["ts1"],
                                 y2 = self.ts_data["ts2"])
        # Plot container
        plot = ToolbarPlot(arr_data)
        # Plot curves
        plot.plot(("x", "y1"), name = "ts 1", color = "red")
        plot.plot(("x", "y2"), name = "ts 2", color = "blue")
        plot.title = "Multi timeseries plotter"
        return plot
    
    traits_view = View(
                Item('ts_plot', editor=ComponentEditor(size=(800, 600)), 
                show_label=False),
        resizable=True, title='Chaco Plot 101', width=800, height=600 )



if __name__ == "__main__":
    
    viewer = GSODDataPlotterView()
    viewer.configure_traits()



    
