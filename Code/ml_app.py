
from gsod_collect import GSODDataReader
from chaco.api import Base2DPlot
from ml_data import WeatherStore
from ml import WeatherPredictor
import enaml


if __name__ == '__main__':
    ws = WeatherStore('weather.h5')
    wp = WeatherPredictor(ws)

    with enaml.imports():
        from ml_app import MLViewModel, MLView

    model = MLViewModel(wstore=ws, predictor=wp)
    view = MLView(model=model, wstore=ws)

    view.show()