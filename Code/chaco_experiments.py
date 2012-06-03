from chaco.api import ArrayPlotData, Plot
from chaco.tools.api import RegressionOverlay, RegressionLasso, PanTool, ZoomTool
from numpy.random import random
import enaml
from util import DataSeries




if __name__ == '__main__':
	plot = gen_scatter_plot(DataSeries('one', random(100)), 
		DataSeries('two', random(100)))
	plot2 = gen_scatter_plot(DataSeries('three', random(100)), 
		DataSeries('four', random(100)))
	with enaml.imports():
		from chaco_experiments import PltView
	view = PltView(plot=plot, plot2=plot2, thumbnail_size=256)
	view.show()
