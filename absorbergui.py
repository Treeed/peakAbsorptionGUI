from PyQt5 import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
import pyqtgraphutils
import numpy as np
import logging

import absorberfunctions
import fileio
import hardware
import logger


class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        super().__init__()

        self.resize(QtWidgets.QDesktopWidget().availableGeometry(self).size() * 0.7)

        self.status_monitor = logger.init_logger()
        self.lg = logging.getLogger("main.gui")

        self.lg.debug("initializing gui")
        self.logsplitter = QtWidgets.QSplitter()
        self.logsplitter.setOrientation(QtCore.Qt.Vertical)
        self.buttonsplitter = QtWidgets.QSplitter()
        self.buttons = QtWidgets.QWidget()
        self.buttons.setLayout(QtWidgets.QVBoxLayout())

        self.logsplitter.addWidget(self.buttonsplitter)
        self.buttonsplitter.addWidget(self.buttons)

        self.button_new_handle = QtGui.QPushButton("new handle")
        self.button_open_file = QtGui.QPushButton("open image")
        self.button_reset_all_beamstops = QtGui.QPushButton("reset all handles")
        self.button_re_arrange = QtGui.QPushButton("rearrange")
        self.button_home = QtGui.QPushButton("experimental homing")
        self.save_state = QtGui.QPushButton("save current state")
        self.load_state = QtGui.QPushButton("load positions")

        self.hardware_buttons = [self.button_re_arrange, self.button_home, self.save_state]

        self.lg.debug("importing config")
        import testconfig as config

        self.absorber_hardware = hardware.PeakAbsorberHardware(config)
        self.image_view = ImageDrawer(config)
        self.beamstop_manager = absorberfunctions.BeamstopManager(config, self.image_view)
        self.beamstop_mover = absorberfunctions.BeamstopMover(config, self.image_view, self.absorber_hardware, self.beamstop_manager)
        self.file_handler = fileio.FileHandler(config, self.image_view, self.logsplitter, self.beamstop_manager, self.beamstop_mover)

        self.lg.debug("initializing and adding widgets")
        self.button_new_handle.clicked.connect(self.image_view.handles.add_default_handle)
        self.button_open_file.clicked.connect(self.file_handler.open_image)
        self.button_reset_all_beamstops.clicked.connect(self.image_view.handles.reset_all_handles)
        self.button_re_arrange.clicked.connect(self.rearrange)
        self.button_home.clicked.connect(self.home)
        self.save_state.clicked.connect(self.file_handler.save_state_gui)
        self.load_state.clicked.connect(self.file_handler.load_state_gui)

        self.buttonsplitter.addWidget(self.image_view.im_view)
        self.buttonsplitter.setStretchFactor(0, 0)
        self.buttonsplitter.setStretchFactor(1, 1)

        self.logsplitter.addWidget(self.status_monitor)
        self.logsplitter.setStretchFactor(0, 1)
        self.logsplitter.setStretchFactor(1, 0)

        self.buttons.layout().addStretch()
        self.buttons.layout().addWidget(self.button_new_handle)
        self.buttons.layout().addWidget(self.button_open_file)
        self.buttons.layout().addWidget(self.button_home)
        self.buttons.layout().addWidget(self.button_reset_all_beamstops)
        self.buttons.layout().addWidget(self.button_re_arrange)
        self.buttons.layout().addWidget(self.save_state)
        self.buttons.layout().addWidget(self.load_state)
        self.buttons.layout().addStretch()

        self.setCentralWidget(self.logsplitter)
        self.show()

    def rearrange(self):
        with DisableButtons(self.hardware_buttons):
            self.beamstop_mover.rearrange_all_beamstops()

    def home(self):
        with DisableButtons(self.hardware_buttons):
            self.absorber_hardware.home()


class DisableButtons:
    def __init__(self, buttons):
        self.buttons = buttons

    def __enter__(self):
        for button in self.buttons:
            button.setEnabled(False)

    def __exit__(self, exc_type, exc_val, exc_tb):
        for button in self.buttons:
            button.setEnabled(True)


class ImageDrawer:
    """class to hold the image view and everything that gets shown on it"""
    def __init__(self, config):
        self.lg = logging.getLogger("main.gui.imagedrawer")
        self.lg.debug("initializing image drawer")
        self.config = config
        self.im_view = NoButtonImageView()
        self.im_view.getView().invertY(False)

        self.handles = HandleHandler(self.im_view, self.config)
        self.beamstop_circles = BeamstopCircleHandler(self.im_view, self.config)
        self.trajectory_lines = TrajectoryHandler(self.im_view, self.config)
        self.outlines = OutlineHandler(self.im_view, self.config)
        self.parking_spots = ParkingSpotHandler(self.im_view, self.config)
        self.crosshair = CrosshairHandler(self.im_view, self.config)

    def set_image(self, array):
            self.im_view.setImage(array)


class GraphicsHandler:
    name = "Unimplemented Graphics Item"
    """base class for everything that gets drawn. children of this class contain all of a specific type of items. All coordinates given are always in machine coordinates"""
    def __init__(self, im_view, config):
        self.im_view = im_view
        self.config = config
        self.items = []
        self.remover = None
        self.lg = logging.getLogger("main.gui."+self.name)

    def img_to_machine_coord(self, point):
        return np.array(point)*self.config.Detector.pixel_size+self.config.Detector.detector_origin

    def machine_to_img_coord(self, point):
        return (np.array(point)-self.config.Detector.detector_origin)/self.config.Detector.pixel_size

    def img_to_machine_scale(self, size):
        return np.array(size) * self.config.Detector.pixel_size

    def machine_to_img_scale(self, size):
        return np.array(size) / self.config.Detector.pixel_size

    def add_item(self, item):
        self.im_view.addItem(item)
        self.items.append(item)

    def remove_item(self, item):
        self.lg.debug("removing " + self.name)
        self.im_view.removeItem(item)
        self.items.remove(item)
        if self.remover is not None:
            self.remover(item)


class HandleHandler(GraphicsHandler):
    name = "handle"
    def add_handle(self, pos):
        radius = self.config.Gui.radius_handle
        self.add_handle_img_coord(self.machine_to_img_coord(np.array(pos)-radius), self.machine_to_img_scale(radius))

    def add_handle_img_coord(self, pos, radius):
        self.lg.debug("adding handle")
        handle = pg.CircleROI(pos, radius*2, pen=(pg.mkPen(self.config.Gui.color_handle)), removable=True)
        handle.sigRemoveRequested.connect(self.remove_item)
        self.add_item(handle)

    def add_default_handle(self):
        self.add_handle([200, 200])

    def reset_all_handles(self):
        self.lg.info("resetting all handles")
        for handle in self.items:
            self.im_view.removeItem(handle)
        self.items.clear()

    def get_handle_positions(self):
        return np.array([self.img_to_machine_coord(np.array(handle.pos())+np.array(handle.size())/2) for handle in self.items])


class BeamstopCircleHandler(GraphicsHandler):
    name = "beamstop circle"

    def move_circle(self, circle,  pos):
        circle.setCenter(self.machine_to_img_coord(pos))

    def add_circle(self, pos):
        circle = pyqtgraphutils.BeamstopCircle(self.machine_to_img_coord(pos), self.machine_to_img_scale(self.config.PeakAbsorber.beamstop_radius)[0], self.config.Gui.color_beamstops)
        circle.sigRemoveRequested.connect(self.remove_item)
        self.add_item(circle)
        return circle


class CrosshairHandler(GraphicsHandler):
    name = "crosshair"

    def __init__(self, im_view, config):
        super().__init__(im_view, config)
        self.line_x = pg.InfiniteLine(0, 90)
        self.line_y = pg.InfiniteLine(0, 0)
        self.add_item(self.line_x)
        self.add_item(self.line_y)
        self.set_crosshair_color(0)

    def set_crosshair_pos(self, pos):
        img_pos = self.machine_to_img_coord(pos)
        self.line_x.setValue(img_pos[0])
        self.line_y.setValue(img_pos[1])

    def set_crosshair_color(self, gripper_pos):
        color = self.config.Gui.color_crosshair.map(gripper_pos)
        self.line_x.setPen(color)
        self.line_y.setPen(color)


class OutlineHandler(GraphicsHandler):
    name = "outline"

    def __init__(self, im_view, config):
        super().__init__(im_view, config)
        self.limit_box = self.add_box([0, 0], self.config.PeakAbsorber.limits, self.config.Gui.color_absorber_geometry)
        self.detector_box = self.add_box(self.config.Detector.detector_origin, self.config.Detector.active_area, self.config.Gui.color_absorber_geometry)

    def add_box(self, pos, size, color='w'):
        box = pyqtgraphutils.RectangleItem(self.machine_to_img_coord(pos), self.machine_to_img_scale(size), color)
        self.add_item(box)
        return box


class ParkingSpotHandler(GraphicsHandler):
    name = "parking spot"

    def __init__(self, im_view, config):
        super().__init__(im_view, config)
        for parking_position in self.config.ParkingPositions.parking_positions:
            self.add_circle(parking_position)

    def add_circle(self, pos):
        circle = pyqtgraphutils.CircleItem(self.machine_to_img_coord(pos), self.machine_to_img_scale(self.config.PeakAbsorber.beamstop_radius)[0], self.config.Gui.color_absorber_geometry)
        self.add_item(circle)
        return circle


class TrajectoryHandler(GraphicsHandler):
    name = "trajectory"

    def add_polyline(self, points):
        line = pyqtgraphutils.PolyLineItem(self.machine_to_img_coord(points), self.config.Gui.color_trajectory)
        self.add_item(line)
        return line


class NoButtonImageView(pg.ImageView):
    """the image view by default tries to cycle through a set of images when the arrow keys are used. If only a single image is loaded it just crashes. This disables this functionality"""
    def keyPressEvent(self, ev):
        pass
