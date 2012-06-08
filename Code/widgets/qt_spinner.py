from __future__ import absolute_import

from os import path

from enaml.backends.qt.qt import QtCore, QtGui
from enaml.backends.qt.qt_control import QtControl

from .spinner import AbstractTkSpinner

class QtSpinner(QtControl, AbstractTkSpinner):
    """ Qt implementation of the spinner control
    """

    #--------------------------------------------------------------------------
    # Setup methods
    #--------------------------------------------------------------------------

    def create(self, parent):
        """ Create the underlying control.
        """
        self.widget = QtGui.QLabel(parent)
        spinner_file = path.join(path.dirname(__file__),'spinner.gif')
        self._movie = movie = QtGui.QMovie(spinner_file, parent=self.widget)
        movie.setCacheMode(QtGui.QMovie.CacheAll)
        movie.setScaledSize(QtCore.QSize(16, 16))

    def initialize(self):
        """ Initializes the attributes on the underlying control
        """
        super(QtSpinner, self).initialize()
        shell = self.shell_obj
        if shell.spinning:
            self._start_movie()

    #--------------------------------------------------------------------------
    # Implementation
    #-------------------------------------------------------------------------- 
    def shell_spinning_changed(self, val):
        """ The change handler for the 'spinning' attribute
        """
        if val:
            self._start_movie()
        else:
            self._stop_movie()

    def _start_movie(self):
        self.shell_obj.visible = True
        self.widget.setMovie(self._movie)
        self._movie.start()

    def _stop_movie(self):
        self.shell_obj.visible = False
        self.widget.setMovie(None)
        self._movie.stop()

