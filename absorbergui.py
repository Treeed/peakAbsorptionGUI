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

        self.button_new_target = QtGui.QPushButton("new handle")
        self.button_open_file = QtGui.QPushButton("open image")
        self.button_reset_all_beamstops = QtGui.QPushButton("reset all handles")
        self.button_re_arrange = QtGui.QPushButton("rearrange")
        self.button_home = QtGui.QPushButton("experimental homing")
        self.save_state = QtGui.QPushButton("save current state")
        self.load_state = QtGui.QPushButton("load positions")

        self.hardware_buttons = [self.button_re_arrange, self.button_home, self.save_state]

        self.lg.debug("importing config")
        import config as config

        self.absorber_hardware = hardware.PeakAbsorberHardware(config)
        self.image_view = ImageDrawer(config)
        self.beamstop_manager = absorberfunctions.BeamstopManager(config, self.image_view)
        self.beamstop_mover = absorberfunctions.BeamstopMover(config, self.image_view, self.absorber_hardware, self.beamstop_manager)
        self.file_handler = fileio.FileHandler(config, self.image_view, self.logsplitter, self.beamstop_manager, self.beamstop_mover)

        self.lg.debug("initializing and adding widgets")
        self.button_new_target.clicked.connect(self.image_view.add_default_handle)
        self.button_open_file.clicked.connect(self.file_handler.open_image)
        self.button_reset_all_beamstops.clicked.connect(self.image_view.reset_all_handles)
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
        self.buttons.layout().addWidget(self.button_new_target)
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
    def __init__(self, config):
        self.lg = logging.getLogger("main.gui.imagedrawer")
        self.lg.debug("initializing image drawer")
        self.config = config
        self.im_view = NoButtonImageView()
        self.im_view.getView().invertY(False)

        self.items = {
            "handles": [],
            "beamstop_circles": [],
            "parking_spots": [],
            "limit_box": [],
            "detector_box": [],
            "crosshair": []
        }

        self.lg.debug("adding absorber geometry and crosshair")
        self.draw_absorber_geometry()
        self.init_crosshair()

    def draw_absorber_geometry(self):
        self.box_in_machine_coords("limit_box", [0, 0], self.config.PeakAbsorber.limits, self.config.Gui.color_absorber_geometry)
        self.box_in_machine_coords("detector_box", self.config.Detector.detector_origin, self.config.Detector.active_area, self.config.Gui.color_absorber_geometry)
        for parking_position in self.config.ParkingPositions.parking_positions:
            self.circle_in_machine_coord("parking_spots", parking_position, color=self.config.Gui.color_absorber_geometry)

    def img_to_machine_coord(self, point):
        return np.array(point)*self.config.Detector.pixel_size+self.config.Detector.detector_origin

    def machine_to_img_coord(self, point):
        return (np.array(point)-self.config.Detector.detector_origin)/self.config.Detector.pixel_size

    def img_to_machine_scale(self, point):
        return np.array(point) * self.config.Detector.pixel_size

    def machine_to_img_scale(self, point):
        return np.array(point) / self.config.Detector.pixel_size

    def box_in_machine_coords(self, purpose, pos, size, color='w'):
        box = pyqtgraphutils.RectangleItem(self.machine_to_img_coord(pos), self.machine_to_img_scale(size), color)
        self.add_graphics_item(box, purpose)

    def circle_in_machine_coord(self, purpose, pos, radius=None, color='w'):
        if radius is None:
            radius = self.config.PeakAbsorber.beamstop_radius
        circle = pyqtgraphutils.CircleItem(self.machine_to_img_coord(pos), self.machine_to_img_scale(radius)[0], color)
        self.add_graphics_item(circle, purpose)

    def move_circle_in_machine_coord(self, purpose, circle_nr,  pos):
        self.items[purpose][circle_nr].setCenter(self.machine_to_img_coord(pos))

    def add_graphics_item(self, item, purpose):
        self.im_view.addItem(item)
        self.items[purpose].append(item)

    def add_handle(self, pos, radius, color):
        self.lg.debug("adding handle")
        handle = pg.CircleROI(pos, radius*2, pen=(pg.mkPen(color)), removable=True)
        handle.sigRemoveRequested.connect(self.remove_handle)
        self.add_graphics_item(handle, "handles")

    def add_handle_in_machine_coord(self, pos, radius=2, color='b'):
        self.add_handle(self.machine_to_img_coord(np.array(pos)-radius), self.machine_to_img_scale(radius), color)

    def add_default_handle(self):
        self.add_handle_in_machine_coord([200, 200])

    def set_image(self, array):
            self.im_view.setImage(array)

    def reset_all_handles(self):
        self.lg.info("resetting all handles")
        for handle in self.items["handles"]:
            self.im_view.removeItem(handle)
        self.items["handles"].clear()

    def remove_handle(self, handle):
        self.lg.debug("removing handle")
        self.im_view.removeItem(handle)
        self.items["handles"].remove(handle)

    def add_beamstop_circles(self, positions):
        if positions is not None:
            for beamstop in positions:
                self.circle_in_machine_coord("beamstop_circles", beamstop, color=self.config.Gui.color_beamstops)

    def get_handles_machine_coords(self):
        return np.array([self.img_to_machine_coord(np.array(handle.pos())+np.array(handle.size())/2) for handle in self.items["handles"]])

    def init_crosshair(self):
        line_x = pg.InfiniteLine(0, 90, 'g')
        line_y = pg.InfiniteLine(0, 0, 'g')
        self.add_graphics_item(line_x, "crosshair")
        self.add_graphics_item(line_y, "crosshair")

    def set_crosshair_pos(self, pos):
        img_pos = self.machine_to_img_coord(pos)
        self.items["crosshair"][0].setValue(img_pos[0])
        self.items["crosshair"][1].setValue(img_pos[1])

    def set_crosshair_color(self, gripper_pos):
        color = self.config.Gui.color_crosshair.map(gripper_pos)
        self.items["crosshair"][0].setPen(color)
        self.items["crosshair"][1].setPen(color)


class NoButtonImageView(pg.ImageView):
    """the image view by default tries to cycle through a set of images when the arrow keys are used. If only a single image is loaded it just crashes. This disables this functionality"""
    def keyPressEvent(self, ev):
        pass
