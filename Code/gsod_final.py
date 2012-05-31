
import numpy
from pandas import DataFrame
from datetime import datetime

# Enthought imports
import enaml
from enaml.item_models.abstract_item_model import AbstractTableModel
from traits.api import HasTraits, Instance, on_trait_change

# Local imports
from station_map import WeatherStationMap


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
        elif isinstance(val, datetime): return val.strftime('%x')
        elif numpy.isnan(val): return ''
        else: return str(val)

    def horizontal_header_data(self, section):
        return self.columns[section]


class GSODBrowser(HasTraits):

    stations = Instance(DataFrame)
    selected_stations = Instance(DataFrame)
    
    map = Instance(WeatherStationMap)
    station_table = Instance(StationTable)

    def _map_default(self):
        return WeatherStationMap(stations=self.stations)

    def _station_table_default(self):
        return StationTable(self)

    @on_trait_change('map:selected')
    def _sel_changed(self, new):
        if len(new):
            idx = self.stations.index[new]
            self.selected_stations = self.stations.ix[idx]
        else:
            self.selected_stations = self.stations

    def _selected_stations_default(self):
        return self.stations


if __name__ == '__main__':
    from gsod_collect import GSODDataReader

    dr = GSODDataReader()

    stations = dr.location_db
    stations = stations[(stations['LAT'] > -85.) & (stations['LAT'] < 85.)][::10]

    model = GSODBrowser(stations = stations)
    
    with enaml.imports():
        from gsod_final_view import GSODView

    view = GSODView(model=model)
    view.show()
