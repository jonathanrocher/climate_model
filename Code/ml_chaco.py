from chaco.api import (ArrayPlotData, Plot, LinePlot,
    OverlayPlotContainer, PlotAxis, LinearMapper, DataRange1D,
    ArrayDataSource, Legend)
from numpy import arange


def gen_scatter_plot(series_one, series_two):
    """
    Parameters
    ----------
    series_one : AbstractSeries
        First series to compare
    series_two : AbstractSeries
        Second series to compare

    """
    series_one_data = series_one.data()
    series_two_data = series_two.data()

    size = min(series_one_data.shape[0],
        series_two_data.shape[0])

    pd = ArrayPlotData(x=series_one_data[:size],
        y=series_two_data[:size])
    plot = Plot(pd)
    scatterplot = plot.plot(('x', 'y'),
                            color='lightblue',
                            type='scatter', 
                            marker='circle',
                            line_width=0.5,
                            marker_size=7)[0]

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


def gen_line_plot(series_one, series_two, y_axis_name=''):
    """
    Parameters
    ----------
    series_one : nd array
    series_two : nd array

    """

    size = min(series_one.shape[0],
        series_two.shape[0])

    idx = ArrayDataSource(arange(size))

    series_one_data = ArrayDataSource(series_one[:size])
    series_two_data = ArrayDataSource(series_two[:size])

    y_range = DataRange1D(series_one_data)
    y_range.tight_bounds = False
    y_range.margin = 50
    x_mapper = LinearMapper(range=DataRange1D(idx))
    y_mapper = LinearMapper(range=y_range)

    series_one_plot = LinePlot(index=idx,
        value=series_one_data, index_mapper=x_mapper,
        value_mapper=y_mapper, color='blue')

    series_two_plot = LinePlot(index=idx,
        value=series_two_data, index_mapper=x_mapper,
        value_mapper=y_mapper, color='red')

    container = OverlayPlotContainer(bgcolor='white',
        padding=25, fill_padding=False, border_visible=True)

    y_axis = PlotAxis(mapper=y_mapper, component=container,
        orientation='left')

    x_axis = PlotAxis(mapper=x_mapper, component=container,
        orientation='bottom')

    x_axis.title = 'Time'
    y_axis.title = y_axis_name

    legend = Legend(component=container, padding=10, align='ur')
    legend.plots = {
        'Predicted': series_one_plot,
        'Actual': series_two_plot,
    }

    container.add(series_one_plot)
    container.add(series_two_plot)
    container.overlays.append(y_axis)
    container.overlays.append(legend)
    return container
