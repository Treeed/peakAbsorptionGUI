#altered from github YannLePoul/pyqtgraphutils
from PyQt5 import QtGui
from PyQt5 import QtCore
import pyqtgraph as pg
from pyqtgraph.Point import Point


class AbsorberGraphicsObject(QtGui.QGraphicsObject):
    def __init__(self):
        super().__init__()

    def boundingRect(self):
        return QtCore.QRectF(self.picture.boundingRect())

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def setPos(self, pos):
        QtGui.QGraphicsObject.setPos(self, pos[0], pos[1])


class LineSegmentItem(AbsorberGraphicsObject):
    def __init__(self, p1, p2, color='w'):
        super().__init__()
        self.p1 = p1
        self.p2 = p2
        self.color = color
        self.generatePicture()

    def generatePicture(self):
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)
        p.setPen(pg.mkPen(self.color))
        p.drawLine(QtCore.QPointF(self.p1[0], self.p1[1]), QtCore.QPointF(self.p2[0], self.p2[1]))
        p.end()


class PolyLineItem(AbsorberGraphicsObject):
    def __init__(self, points, color='w'):
        super().__init__()
        self.points = points
        self.color = color
        self.generatePicture()

    def generatePicture(self):
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)
        p.setPen(pg.mkPen(self.color))
        p.drawPolyline(*[QtCore.QPointF(point[0], point[1]) for point in self.points])
        p.end()


class CircleItem(AbsorberGraphicsObject):
    def __init__(self, center, radius, color = 'w'):
        super().__init__()
        self.radius = radius
        self.color = color
        self.setCenter(center)
        self.generatePicture()

    def generatePicture(self):
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)
        p.setPen(pg.mkPen(self.color))
        p.drawEllipse(QtCore.QRectF(0, 0, self.radius * 2, self.radius * 2))
        p.end()

    def setCenter(self, center):
        self.setPos(center-self.radius)


class RectangleItem(AbsorberGraphicsObject):
    def __init__(self, topLeft, size, color = 'w'):
        super().__init__()
        self.size = size
        self.color = color
        self.setPos(topLeft)
        self.generatePicture()

    def generatePicture(self):
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)
        p.setPen(pg.mkPen(self.color))
        p.drawRect(QtCore.QRectF(0, 0, self.size[0], self.size[1]))
        p.end()


class BeamstopCircle(CircleItem):
    sigRemoveRequested = QtCore.Signal(object)

    def __init__(self, center, radius, color):
        super().__init__(center, radius, color)
        # menu creation is deferred because it is expensive and often
        # the user will never see the menu anyway.
        self.menu = None

    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.RightButton:
            if self.raiseContextMenu(ev):
                ev.accept()

    def raiseContextMenu(self, ev):
        menu = self.scene().addParentContextMenus(self, self.getContextMenus(), ev)

        pos = ev.screenPos()
        menu.popup(QtCore.QPoint(pos.x(), pos.y()))
        return True

    def getContextMenus(self, event=None):
        if self.menu is None:
            self.menu = QtGui.QMenu()

            removal = QtGui.QAction("Remove beamstop", self.menu)
            removal.triggered.connect(self.remove_safely)
            self.menu.addAction(removal)
        return self.menu

    def remove_safely(self):
        """this ensures the removing function doesn't actually remove itself but only schedules its own removal. Otherwise things start crashing randomly and without error"""
        QtCore.QTimer.singleShot(0, lambda: self.sigRemoveRequested.emit(self))
