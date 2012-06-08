import enaml
from ml_data import WeatherStore


def main():
    ws = WeatherStore('weather.h5')
    with enaml.imports():
        from scatter_matrix import MLView, ScatterTableModel
    model = ScatterTableModel(thumb_size=400,
        weather_store=ws, field='TEMP')
    view = MLView(model=model)
    view.show()

if __name__ == '__main__':
    main()
