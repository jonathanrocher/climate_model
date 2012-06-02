from gsod_collect import GSODDataReader
from pandas import HDFStore
from pandas.core.panel import Panel, DataFrame
import numpy as np
from sklearn.svm import SVR
from sklearn import linear_model

def download():
	reader = GSODDataReader()
	year_list = range(2005, 2012)
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
	store['central_park'] = central_park
	store['new_haven'] = new_haven
	store.close()

def dframe(hdfs_store, city_key):
	val = hdfs_store[city_key]
	if isinstance(val, Panel):
		key = val.items[0]
		val = val[key]
	return val

def learn(df, attrib_name):
	df['month'] = df.index.month
	df['day'] = df.index.day
	X = np.empty((df.shape[0], 2), dtype=np.float64)
	y = np.empty((df.shape[0], ), dtype=np.float64)
	X[:, 0] = df['month']
	X[:, 1] = df['day']
	y[:] = df[attrib_name]
	return X, y

def regression(X, y):
	regr = linear_model.LinearRegression()
	regr.fit(X, y)
	return regr

def svr(X, y):
	clf = SVR(C=1.0, epsilon=0.2)
	clf.fit(X, y)
	return clf

