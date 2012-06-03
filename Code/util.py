from gsod_collect import GSODDataReader
from pandas import HDFStore
from pandas.core.panel import Panel, DataFrame
import numpy as np
from sklearn.svm import SVR
from sklearn import linear_model

from traits.api import HasTraits, Instance, on_trait_change, List

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

def download():
	reader = GSODDataReader()
	year_list = range(2001, 2012)
	austin = reader.collect_data(year_list, exact_station=True,
		station_name='AUSTIN CAMP MABRY', state='TX', country='US')
	houston = reader.collect_data(year_list, exact_station=True,
		station_name='HOUSTON/D.W. HOOKS', state='TX', country='US')
	central_park = reader.collect_data(year_list, exact_station=True,
		station_name='NEW YORK/LA GUARDIA', state='NY', country='US')
	new_haven = reader.collect_data(year_list, exact_station=True,
		station_name='NEW HAVEN', state='CT', country='US')
	store = HDFStore('weather.h5')
	store['austin'] = austin
	store['houston'] = houston
	store['new_york'] = central_park
	store['new_haven'] = new_haven
	store.close()

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

	def attrib(self, city, attrib):
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
		y = self.attrib(city, attrib)
		return X, y
		



# Learning models
#----------------------------------------------------------

class WeatherPredictor(HasTraits):
	def __init__(self, weather_store):
		self._ws = weather_store
		self._learner_map = {
		'regression' : self.regression,
		'svr' : self.svr
		}

	def regression(self, X, y):
		regr = linear_model.LinearRegression()
		regr.fit(X, y)
		return regr

	def svr(self, X, y):
		clf = SVR(C=1.0, epsilon=0.2)
		clf.fit(X, y)
		return clf

	def test_learning(self, learning_method, city,
		attrib, learn_idx=1600):
		X, y = self._ws.learning_data(city, attrib)
		learning_fn = self._learner_map[learning_method]
		model = learning_fn(X[:learn_idx], y[:learn_idx])
		pred = model.predict(X[learn_idx:])
		return pred, y[learn_idx:]

ws = WeatherStore('weather.h5')
wp = WeatherPredictor(ws)

class WeatherModel(HasTraits):
	ws = Instance(WeatherStore)
	wp = Instance(WeatherPredictor)
	plot = Instance(Base2DPlot)
	cities = List()

	@on_trait_change('ws, wp, cities')
	def update_plot(self):
		pass