import enaml
from numpy.random import random
from ml_data import DataSeries

def main():
	with enaml.imports():
		from learner import MLView, ScatterTableModel
	model = ScatterTableModel(thumb_size=150)
	view = MLView(model=model)
	series1 = DataSeries('one', random(100), None)
	series2 = DataSeries('two', random(100), None)
	series3 = DataSeries('three', random(100), None)
	series4 = DataSeries('four', random(100), None)
	series5 = DataSeries('five', random(100), None)
	model.items = [series1, series2, series3, series4, series5]
	view.show()
if __name__ == '__main__':
	main()