from chaco.api import ArrayPlotData, Plot
from ml_data import DataSeries

def gen_scatter_plot(series_one, series_two):
	"""
	Parameters
	----------
	series_one : AbstractSeries
		First series to compare
	series_two : AbstractSeries
		Second series to compare

	"""
	pd = ArrayPlotData(x=series_one.data(),
		y=series_two.data())
	plot = Plot(pd)
	scatterplot = plot.plot(('x','y'), color='lightblue',
		type='scatter', marker='circle', marker_size=2)[0]

	plot.x_axis.title = series_one.label()
	plot.x_axis.tick_visible = False
	plot.x_axis._draw_labels = lambda x: 1
	plot.x_axis.title_spacing = 0.25

	plot.y_axis.title = series_two.label()
	plot.y_axis.tick_visible = False
	plot.y_axis._draw_labels = lambda x: 1
	plot.y_axis.title_spacing = 0.25
	plot.padding = [18, 18, 18, 18]
	return plot