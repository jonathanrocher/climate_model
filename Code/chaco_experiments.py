from chaco.api import ArrayPlotData, Plot
from chaco.tools.api import RegressionOverlay, RegressionLasso, PanTool, ZoomTool
from numpy.random import random
import enaml


def gen_regression_plot(series_one, series_two):
	pd = ArrayPlotData(x=series_one, y=series_two)
	plot = Plot(pd)
	scatterplot = plot.plot(('x','y'), color='lightblue',
		type='scatter', marker='circle')[0]
	plot.tools.append(PanTool(plot, drag_button="right"))
	plot.overlays.append(ZoomTool(plot))
	regression = RegressionLasso(scatterplot,
		selection_datasource=scatterplot.index)
	scatterplot.tools.append(regression)
	scatterplot.overlays.append(RegressionOverlay(scatterplot,
		lasso_selection=regression))
	return plot


def gen_scatter_plot(series_one, series_two):
	pd = ArrayPlotData(x=series_one, y=series_two)
	plot = Plot(pd)
	scatterplot = plot.plot(('x','y'), color='lightblue',
		type='scatter', marker='circle')[0]
	return plot


if __name__ == '__main__':
	plot = gen_scatter_plot(random(100), random(100))
	plot2 = gen_scatter_plot(random(100), random(100))
	with enaml.imports():
		from chaco_experiments import PltView
	view = PltView(plot=plot, plot2=plot2)
	view.show()
