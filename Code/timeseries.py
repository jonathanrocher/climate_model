import pandas, time, numpy
import enaml
from traits.api import HasTraits, Instance, List, Any
from enable.api import Component
from chaco.api import ArrayDataSource, LinearMapper, DataRange1D, VPlotContainer, \
                      FilledLinePlot, PlotGrid, PlotAxis, PlotLabel, \
                      Blues as cmap
from chaco.tools.api import PanTool
from chaco.scales.api import CalendarScaleSystem
from chaco.scales_tick_generator import ScalesTickGenerator

from chaco.horizon_plot import HorizonPlot, BandedMapper

class WeatherTimeseries(HasTraits):

    plot = Instance(Component)

    timeseries = Instance(pandas.DataFrame)

    index_ds = Instance(ArrayDataSource, dict(sort_order='none'))
    value_ds = List(ArrayDataSource)

    rows = List

    def _timeseries_changed(self, new):
        # Filter down to days
        cols = new.columns
        idx = [time.mktime(d.utctimetuple()) for d in new.index]
        self.index_ds.set_data(idx)
        vals = []
        self.rows = list(reversed(cols[2:-6:2]))
        for col in self.rows:
            data = new[col]
            vals.append(ArrayDataSource(data.view(numpy.ndarray)))
        
        self.value_ds = vals
        self._rebuild_plot()

    def _rebuild_plot(self):
        container = self.plot
        
        value_range = DataRange1D(low=-1, high=1.)
        index_range = DataRange1D(self.index_ds, high='track', tracking_amount=24*3600*365)

        color_mapper = cmap(range=value_range)
    
        # Remove old plots
        container.remove(*container.components)
        for val, row in zip(self.value_ds, self.rows):
            horizon = HorizonPlot(
                index = self.index_ds,
                value = val,
                index_mapper = LinearMapper(range=index_range, stretch_data=False),
                value_mapper = BandedMapper(range=DataRange1D(val)),
                color_mapper = cmap(range=DataRange1D(val)), #color_mapper,
                negative_bands = False,
                )   
            horizon.tools.append(PanTool(horizon, constrain=True, constrain_direction="x"))
            horizon.overlays.append(PlotLabel(component=horizon, hjustify='right', text=row, overlay_position='outside left'))
            container.add(horizon)
        bottom_axis = PlotAxis(horizon, orientation="bottom",
                    tick_generator=ScalesTickGenerator(scale=CalendarScaleSystem()))
        container.overlays = [bottom_axis]

        container.request_redraw()

    def _plot_default(self):
        container = VPlotContainer(padding=(40, 0, 0, 20))
        return container

