from gsod_collect import GSODDataReader
from pandas import HDFStore
from pandas.core.panel import Panel
import numpy as np
from abc import ABCMeta, abstractmethod

# Available fields
"""
STN---
WBAN
TEMP
TEMP-count
DEWP
DEWP-count
SLP
SLP-count
STP
STP-count
VISIB
VISIB-count
WDSP
WDSP-count
MXSPD
GUST
MAX
MIN
PRCP
SNDP
FRSHTT
"""
WEATHER_FIELDS = ['TEMP', 'DEWP', 'VISIB', 'WDSP', 'MXSPD']


def download():
    """ Convenience method that downloads all the weather data required
    for the machine learning examples.
    """
    reader = GSODDataReader()
    year_list = range(2001, 2012)
    austin = reader.collect_data(year_list, exact_station=True,
        station_name='AUSTIN CAMP MABRY', state='TX', country='US')
    houston = reader.collect_data(year_list, exact_station=True,
        station_name='HOUSTON/D.W. HOOKS', state='TX', country='US')
    new_york = reader.collect_data(year_list, exact_station=True,
        station_name='NEW YORK/LA GUARDIA', state='NY', country='US')
    newark = reader.collect_data(year_list, exact_station=True,
        station_name='NEWARK INTL AIRPORT', state='NJ', country='US')
    punta_arenas = reader.collect_data(year_list, exact_station=True,
        station_name='PUNTA ARENAS', country='CH')
    wellington = reader.collect_data(year_list, exact_station=True,
        station_name='WELLINGTON AIRPORT', country='NZ')
    store = HDFStore('weather.h5')
    store['austin'] = austin
    store['houston'] = houston
    store['nyc'] = new_york
    store['newark'] = newark
    store['punta_arenas'] = punta_arenas
    store['wellington'] = wellington
    store.close()


class AbstractSeries(object):
    """ Abstract class for weather time series.

    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def label(self):
        """ Return name of this time series

        Returns
        -------
        result : string
            name of this time series
        """
        raise NotImplementedError

    @abstractmethod
    def data(self):
        """ Return data corresponding to this time series

        Returns
        -------
        result : numpy.ndarray of shape (n, 1) and dtype float64
        """
        raise NotImplementedError

    @abstractmethod
    def time(self):
        """ Return time index for the data in this time series

        Returns
        -------
        result : numpy.ndarray of shape(n,3) and type int64
            Columns are year, month, day

        """
        raise NotImplementedError


class DataSeries(AbstractSeries):
    def __init__(self, name, data, time):
        self._name = name
        self._data = data
        self._idx = time

    def label(self):
        return self._name

    def data(self):
        return self._data

    def time(self):
        return self._idx


class WeatherStore(object):

    def __init__(self, filename):
        """
        Parameters
        ----------
        filename : filename pointing to an existing HDFStore with
            valid data in it.

        """
        self._store = HDFStore(filename)

    def dframe(self, city):
        val = self._store[city]
        if isinstance(val, Panel):
            key = val.items[0]
            val = val[key]
        return val

    def attrib_numpy(self, city, attrib):
        df = self.dframe(city)
        y = np.empty((df.shape[0], ), dtype=np.float64)
        y[:] = df[attrib]
        return y

    def time_indices(self, df):
        X = np.empty((df.shape[0], 3), dtype=np.float64)
        X[:, 0] = df.index.year
        X[:, 1] = df.index.month
        X[:, 2] = df.index.day
        return X

    def learning_data(self, city, attrib):
        """
        Returns
        -------
        X : numpy array of shape (n,2).
            Columns are month and day
        y : numpy array of shape (n,).
            value of attrib being requested

        """
        df = self.dframe(city)
        X = self.time_indices(df)[:, 1:]
        y = self.attrib_numpy(city, attrib)
        return X, y

    def attrib_dataseries(self, city, attrib):
        """
        Returns
        -------
        result : DataSeries
            get the specified attribute for city as a DataSeries
        """
        df = self.dframe(city)
        indices = self.time_indices(df)
        data = self.attrib_numpy(city, attrib)
        return DataSeries(city, data, indices)

    def cities(self):
        return self._store.keys()
