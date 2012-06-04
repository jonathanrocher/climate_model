import enaml
from numpy.random import random
from ml_data import DataSeries, WeatherStore

def main():
	ws = WeatherStore('weather.h5')
	austin = ws.attrib_dataseries('austin','TEMP')
	houston = ws.attrib_dataseries('houston','TEMP')
	nyc = ws.attrib_dataseries('nyc','TEMP')
	newark = ws.attrib_dataseries('newark','TEMP')
	punta_arenas = ws.attrib_dataseries('punta_arenas','TEMP')
	wellington = ws.attrib_dataseries('wellington','TEMP')
	
	with enaml.imports():
		from learner import MLView, ScatterTableModel
	model = ScatterTableModel(thumb_size=200)
	view = MLView(model=model)
	model.items = [austin, houston, nyc, newark, punta_arenas, wellington]
	view.show()
if __name__ == '__main__':
	main()