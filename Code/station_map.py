
import os
import numpy
import pyproj
import pandas

from traits.api import (HasTraits, Any, Instance, Array, Float,
                        Property, cached_property)

from enable.api import Component
from mapping.enable.api import HTTPTileManager, MBTileManager

from chaco.api import (ArrayPlotData, Plot, OverlayPlotContainer, LinearMapper,
                       LassoOverlay, ScatterInspectorOverlay)
from chaco.tools.api import PanTool, ZoomTool, LassoSelection, ScatterInspector
from mapping.chaco.map import Map

class WeatherStationMap(HasTraits):

    stations = Instance(pandas.DataFrame)
    
    plot = Instance(Component)
    
    # Circumference at the equator in meters
    circum = Float(6378137.0)

    # Selected stations
    selected_stations = Property(Instance(pandas.DataFrame), 
                                 depends_on='stations, selected')

    # Private traits
    
    # array of selection indices into stations
    selected = Array
    
    # Projection used (Google maps)
    _proj = Instance(pyproj.Proj, dict(init='epsg:3857'))
    
    # Origin shift to lower left corner
    _shift = Property(Float, depends_on='_circum')
    
    # TraitsUI view
    def traits_view(self):
        from enable.api import ComponentEditor
        from traitsui.api import View, UItem
        size = (800, 800)
        return View(UItem('plot', editor=ComponentEditor()),
                       width=size[0], height=size[1], resizable=True,
                       )

    def _plot_default(self):
        stations = self.stations
        lon, lat = self._proj(stations['LON'].view(numpy.ndarray), 
                             stations['LAT'].view(numpy.ndarray))

        shift = self._shift
        lon = (lon + shift/2.)/(shift)
        lat = (lat + shift/2.)/(shift)

        plot = Plot(ArrayPlotData(index = lon, value=lat))
        plot.plot(("index", "value"),
                  type = "scatter",
                  name = "stations",
                  marker = "dot",
                  outline_color = 'black',
                  color = (1., 0., 0., 0.2),
                  line_width = 1.,
                  marker_size = 1,
                  )

        mbtiles_fname = os.path.join('Data', 'tiles.mbtiles')
        if os.path.exists(mbtiles_fname):
            tile_cache = MBTileManager(filename=mbtiles_fname,
                                       min_level=0, max_level=7)
        else:
            tile_cache = HTTPTileManager(min_level=0, max_level=6,
                                     server='oatile1.mqcdn.com',
                                     url='/tiles/1.0.0/sat/%(zoom)d/%(row)d/%(col)d.jpg',
                                     )

        # Right now, some of the tools are a little invasive, and we need the
        # actual ScatterPlot object to give to them
        scatter = plot.plots['stations'][0]

        map = Map(scatter, tile_cache=tile_cache, alpha=0.8, zoom_level=2)
        scatter.underlays.append(map)

        map.on_trait_change(lambda new: self._update_scatter(scatter, new),'zoom_level')
        self._update_scatter(scatter, map.zoom_level)

        lasso_selection = LassoSelection(component=scatter,
                                         selection_datasource=scatter.index)

        scatter.tools.append(lasso_selection)
        scatter.overlays.append(LassoOverlay(component=scatter,
                                          selection_fill_color='lawngreen',
                                          selection_border_color='lightgreen',
                                          selection_alpha = 0.5,
                                          selection_border_width=2.0,
                                          lasso_selection=lasso_selection))

        scatter.overlays.append(
            ScatterInspectorOverlay(scatter,
                selection_metadata_name = 'selection',
                selection_marker_size = 4,
                selection_color = "lawngreen")
            )
        scatter.index.on_trait_change(self._metadata_handler,
                                     "metadata_changed")
        
        scatter.tools.append(PanTool(scatter, drag_button='right'))
        scatter.tools.append(ZoomTool(scatter))

        plot.index_axis.title = "Longitude"
        plot.index_axis.tick_label_formatter = self._convert_lon
        plot.value_axis.title = "Latitude"
        plot.value_axis.tick_label_formatter = self._convert_lat

        plot.padding_right = plot.padding_top = 2

        container = OverlayPlotContainer(
            use_backbuffer=True,
            bgcolor = "sys_window"
            )
        container.add(plot)
        container.bgcolor = "sys_window"

        return container

    def _update_scatter(self, scatter, zoom):
        if zoom < 3:
            scatter.trait_set(marker='dot', color=(1.,0.,0.,0.4), marker_size=1.0)
        elif zoom < 7:
            scatter.trait_set(marker='dot', color=(1.,0.,0.,0.6), marker_size=2.0)
        else:
            scatter.trait_set(marker='circle', color=(1.,0.,0.,1), marker_size=3.0)

    def _convert_lat(self, y):
        s = self._shift
        return "%.0f"%self._proj(0, (y*s)-(s/2.), inverse=True)[1]
        
    def _convert_lon(self, x):
        s = self._shift
        return "%.0f"%self._proj((x*s)-(s/2.), 0, inverse=True)[0]
    
    def _get__shift(self):
        return 2*numpy.pi * self.circum

    def _metadata_handler(self, obj, name, new):
        mask = obj.metadata.get('selection', [])
        sel = numpy.compress(mask, numpy.arange(len(mask)))
        if (len(sel) != len(self.selected) or not numpy.all(self.selected == sel)):
            self.selected = sel

    @cached_property
    def _get_selected_stations(self):
        return self.stations.ix[self.selected]

if __name__ == "__main__":
    from gsod_collect import GSODDataReader

    dr = GSODDataReader()
    
    stations = dr.location_db
    stations = stations[(stations['LAT'] > -85.) & (stations['LAT'] < 85.)]

    demo = WeatherStationMap(stations=stations)
    demo.configure_traits()


