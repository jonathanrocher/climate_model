from gsod_collect import GSODDataReader
from pandas import HDFStore
from pandas.core.panel import Panel, DataFrame
import numpy as np
from sklearn.svm import SVR
from sklearn import linear_model
from abc import ABCMeta, abstractmethod
from traits.api import HasTraits, Instance, on_trait_change, List
from chaco.api import Base2DPlot
from ml_data import WeatherStore

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

if __name__ == '__main__':
	