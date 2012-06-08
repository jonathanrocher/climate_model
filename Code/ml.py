from sklearn.svm import SVR
from sklearn import linear_model
from traits.api import HasTraits


LEARNING_METHODS = ['regression', 'svr']

# Learning models
#----------------------------------------------------------


class WeatherPredictor(HasTraits):
    def __init__(self, wstore):
        self._ws = wstore
        self._learner_map = {
        'regression': self.regression,
        'svr': self.svr
        }

    def regression(self, X, y):
        """ Train linear regression model

        """
        regr = linear_model.LinearRegression()
        regr.fit(X, y)
        return regr

    def svr(self, X, y):
        """ Train support vector regression model
        """
        clf = SVR(C=1.0, epsilon=0.2)
        clf.fit(X, y)
        return clf

    def test_learning(self, learning_method, city,
        attrib, learn_idx=1600):
        X, y = self._ws.learning_data(city, attrib)
        learning_fn = self._learner_map[learning_method]
        model = learning_fn(X[:learn_idx], y[:learn_idx])
        pred = model.predict(X[learn_idx:])
        return pred, y[learn_idx:]

    def cross_learn(self, learning_method, city_one,
        city_two, attrib):
        X, y = self._ws.learning_data(city_one, attrib)
        learning_fn = self._learner_map[learning_method]
        model = learning_fn(X, y)
        X, y = self._ws.learning_data(city_two, attrib)
        pred = model.predict(X)
        return pred, y
