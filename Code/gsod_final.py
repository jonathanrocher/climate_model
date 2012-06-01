
import numpy
from pandas import DataFrame, Panel
from datetime import datetime

# Enthought imports
import enaml
from enaml.item_models.abstract_item_model import AbstractTableModel
from traits.api import HasTraits, Instance, on_trait_change

# Local imports
from gsod_collect import GSODDataReader
from station_map import WeatherStationMap
from timeseries import WeatherTimeseries

class StationTable(AbstractTableModel):

    def __init__(self, adapter):
        super(StationTable, self).__init__()
        self.adapter = adapter
        self.columns = ['STATION_NAME', 'BEGIN', 'END', 'CTRY_FIPS'] #, 'USAF', 'WBAN']
        adapter.on_trait_change(self.refresh_table, 'selected_stations')

    def refresh_table(self):
        self.begin_reset_model()
        self.end_reset_model()

    def column_count(self, parent=None):
        if parent is None:
            return len(self.columns)
        return 0

    def row_count(self, parent=None):
        if parent is None:
            return len(self.adapter.selected_stations)
        return 0

    def data(self, index):
        df = self.adapter.selected_stations
        colname = self.columns[index.column]
        val = df[colname].view(numpy.ndarray)[index.row]
        if isinstance(val, basestring): return val
        elif isinstance(val, datetime): 
            return "%02d/%02d/%d"%(val.month, val.day, val.year)
        elif numpy.isnan(val): return ''
        else: return str(val)

    def horizontal_header_data(self, section):
        return self.columns[section]


class GSODBrowser(HasTraits):

    data = Instance(GSODDataReader)

    stations = Instance(DataFrame)
    selected_stations = Instance(DataFrame)
    
    map = Instance(WeatherStationMap)
    station_table = Instance(StationTable)

    timeseries = Instance(WeatherTimeseries)

    def _map_default(self):
        return WeatherStationMap(stations=self.stations)

    def _station_table_default(self):
        return StationTable(self)

    @on_trait_change('map:selected')
    def _sel_changed(self, new):
        if len(new):
            idx = self.stations.index[new]
            self.selected_stations = stations = self.stations.ix[idx]

            name = stations['STATION_NAME'][0]
            wmo, wban = stations.index[0]
            #ts = self.data.collect_data(range(2000, 2005), location_WMO=wmo, location_WBAN=wban)
            # This is suboptimal - need to change collect_data to use the pandas index
            ts = self.data.collect_data(range(2000, 2012), station_name=name, exact_station=True)
            if ts is not None:
                if isinstance(ts, Panel): ts = ts[0]
                self.timeseries.timeseries = ts

        else:
            self.selected_stations = self.stations

    def _selected_stations_default(self):
        return self.stations

    def _timeseries_default(self):
        return WeatherTimeseries()


if __name__ == '__main__':

    dr = GSODDataReader()

    stations = dr.location_db
    start = datetime(2000, 01, 01)
    # Filter stations that can't be shown on the map or that don't have any
    # data after 2000
    stations = stations[(stations['LAT'] > -85.) & (stations['LAT'] < 85.) &
                        (stations['END'] > start)][::4]

    model = GSODBrowser(data = dr, stations = stations)
    
    with enaml.imports():
        from gsod_final_view import GSODView

    view = GSODView(model=model)
    view.show()
