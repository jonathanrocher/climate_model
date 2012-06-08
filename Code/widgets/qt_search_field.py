from __future__ import absolute_import

from os.path import join, dirname

from enaml.backends.qt.qt import QtGui, QtCore
from enaml.backends.qt.qt_control import QtControl

from .search_field import AbstractTkSearchField

class QtSearchField(QtControl, AbstractTkSearchField):
    """ Qt implementation of the spinner control
    """

    #--------------------------------------------------------------------------
    # Setup methods
    #--------------------------------------------------------------------------

    def create(self, parent):
        """ Create the underlying control.
        """
        self.widget = _SearchEdit(parent)

    def initialize(self):
        """ Initializes the attributes on the underlying control
        """
        super(QtSearchField, self).initialize()
        
    def bind(self):
        """ Binds the event handlers for the SearchEdit
        """
        super(QtSearchField, self).bind()
        widget = self.widget

    #--------------------------------------------------------------------------
    # Implementation
    #-------------------------------------------------------------------------- 

class _ToolButton(QtGui.QToolButton):
    def paintEvent(self, event):
        painter = QtGui.QStylePainter(self)
        opt = QtGui.QStyleOptionToolButton()
        self.initStyleOption(opt)
        opt.features &= (not QtGui.QStyleOptionToolButton.HasMenu)
        painter.drawComplexControl(QtGui.QStyle.CC_ToolButton, opt)

class _SearchEdit(QtGui.QLineEdit):
    """ This line edit provides an info box that can be used to show
        search information and 2 signals that can be used to move the
        the search forward or backward.
    """
    next = QtCore.Signal()
    previous = QtCore.Signal()

    def __init__(self, *args):
        super(_SearchEdit, self).__init__(*args)
        self.horizontalMargin, self.verticalMargin = 2, 1
        left, top, right, bottom = self.getTextMargins()
        self._right = right
        self._info_width = 0 
        self.clearInfo()

        button = _ToolButton(self)
        pixmap = QtGui.QPixmap(join(dirname(__file__),"search.png"))
        button.setIcon(QtGui.QIcon(pixmap))
        button.setIconSize(pixmap.size())
        button.setCursor(QtCore.Qt.ArrowCursor)
        button.setPopupMode(QtGui.QToolButton.InstantPopup)
        button.setArrowType(QtCore.Qt.NoArrow)
        button.setStyleSheet("QToolButton { border: none; padding: 0px; }")

        frameWidth = self.style().pixelMetric(QtGui.QStyle.PM_DefaultFrameWidth)
        self.setStyleSheet("QLineEdit { padding-left: %dpx }"
                            %(button.sizeHint().width()+frameWidth))

        msz = self.minimumSizeHint()
        self.setMinimumSize(
            max(msz.width(), button.sizeHint().width() + frameWidth * 2 + 2), 
            max(msz.height(), button.sizeHint().height() + frameWidth * 2 + 2)) 

        self._button = button

    def setInfo(self, text):
        self._info_text = text
        width = self.fontMetrics().width(self._info_text)+2*self.horizontalMargin
        if width != self._info_width:
            # Update the text margin to give the info text enough room
            self._info_width = width
            left, top, right, bottom = self.getTextMargins()
            self.setTextMargins(left, top,
                self._right + width, bottom)
        self.update()

    def clearInfo(self):
        self.setInfo('')

    def sizeHint(self):
        size = super(_SearchEdit, self).sizeHint()
        # Add some info character width to compensate
        # greyed text
        extra = self.fontMetrics().maxWidth()*4
        size.setWidth(size.width()+extra-self._info_width)
        return size

    def paintEvent(self, event):
        # paint original widget
        super(_SearchEdit, self).paintEvent(event)

        if self._info_text:
            painter = QtGui.QPainter(self)
            style = self.style()

            panel = QtGui.QStyleOptionFrameV2()
            self.initStyleOption(panel)
            fm = self.fontMetrics()
            left, top, right, bottom = self.getTextMargins()
            r = style.subElementRect(QtGui.QStyle.SE_LineEditContents, panel, self)
            r.setX(r.x() + left)
            r.setY(r.y() + top)
            r.setRight(r.right() - right)
            r.setBottom(r.bottom() - bottom)

            align = style.visualAlignment(self.layoutDirection(), self.alignment())
            va = align & QtCore.Qt.AlignVertical_Mask
            if va == QtCore.Qt.AlignBottom:
                vscroll = r.y() + r.height() - fm.height() - self.verticalMargin
            elif va == QtCore.Qt.AlignTop:
                vscroll = r.y() + self.verticalMargin
            else:
                vscroll = r.y() + (r.height() - fm.height() + 1) / 2

            lineRect = QtCore.QRect(r.right() + self.horizontalMargin,
                vscroll, self._info_width - self.horizontalMargin*2, fm.height())
            lineRect.adjust(max(0, -fm.minLeftBearing()), 0, 0, 0)

            col = self.palette().text().color()
            col.setAlpha(128)

            painter.setPen(col)
            painter.drawText(lineRect, 
                align | QtCore.Qt.AlignRight, self._info_text)

    def keyPressEvent(self, event):
        if (event.key() in [QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return]):
            if (event.modifiers() & QtCore.Qt.ShiftModifier):
                self.previous.emit()
            else:
                self.next.emit()
        super(_SearchEdit, self).keyPressEvent(event)

    def resizeEvent(self, event):
        sz = self._button.sizeHint()
        frameWidth = self.style().pixelMetric(QtGui.QStyle.PM_DefaultFrameWidth)
        rect = self.rect()
        self._button.move(frameWidth*2, 
                          (rect.bottom() - sz.height())/2 + frameWidth)

    def setMenu(self, shortcut, menu):
        self._button.setMenu(menu)
        self.shortcut = QtGui.QShortcut(
                QtGui.QKeySequence.mnemonic(shortcut), self)
        self.shortcut.activated.connect(self._button.showMenu)

if __name__ == "__main__":
    import sys

    app = QtGui.QApplication(sys.argv)
    window = _SearchEdit(None)

    window.show()
    sys.exit(app.exec_())
