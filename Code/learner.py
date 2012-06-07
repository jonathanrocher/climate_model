import enaml
from numpy.random import random
from ml_data import DataSeries, WeatherStore

def main():
	ws = WeatherStore('weather.h5')
	with enaml.imports():
		from learner import MLView, ScatterTableModel
	model = ScatterTableModel(thumb_size=200, weather_store=ws, field='TEMP')
	view = MLView(model=model)
	view.show()

if __name__ == '__main__':
	main()