from PyQt5 import QtGui
import pyqtgraph as pg
import pyqtgraphutils
import numpy as np
import logging

import absorberfunctions
import fileio
import hardware


class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        super().__init__()

        fileio.init_logger()
        self.lg = logging.getLogger("main.gui")

        self.lg.debug("initializing gui")
        self.widget = QtGui.QWidget()
        self.widget.setLayout(QtGui.QGridLayout())

        self.button_new_target = QtGui.QPushButton("new handle")
        self.button_open_file = QtGui.QPushButton("open image")
        self.button_reset_all_beamstops = QtGui.QPushButton("reset all handles")
        self.button_re_arrange = QtGui.QPushButton("rearrange")
        self.button_home = QtGui.QPushButton("experimental homing")
        self.add_beamstops = QtGui.QPushButton("add beamstops")

        self.lg.debug("importing config")
        import config as config

        self.beamstop_manager = absorberfunctions.BeamstopManager(config)
        self.absorber_hardware = hardware.PeakAbsorberHardware(config)
        self.image_view = ImageDrawer(config, self.absorber_hardware, self.beamstop_manager)
        self.file_handler = fileio.FileHandler(config, self.image_view, self.widget, self.beamstop_manager)
        self.beamstop_mover = absorberfunctions.BeamstopMover(config, self.image_view, self.absorber_hardware, self.beamstop_manager)

        self.lg.debug("initializing and adding widgets")
        self.button_new_target.clicked.connect(self.image_view.add_handle)
        self.button_open_file.clicked.connect(self.file_handler.open_image)
        self.button_reset_all_beamstops.clicked.connect(self.image_view.reset_all_handles)
        self.button_re_arrange.clicked.connect(self.rearrange)
        self.button_home.clicked.connect(self.home)
        self.add_beamstops.clicked.connect(self.file_handler.open_beamstop_list)

        self.widget.layout().addWidget(self.image_view.im_view, 0, 1, 10, 10)
        self.widget.layout().addWidget(self.button_new_target, 0, 0)
        self.widget.layout().addWidget(self.button_open_file, 1, 0)
        self.widget.layout().addWidget(self.button_home, 2, 0)
        self.widget.layout().addWidget(self.button_reset_all_beamstops, 3, 0)
        self.widget.layout().addWidget(self.button_re_arrange, 4, 0)
        self.widget.layout().addWidget(self.add_beamstops, 5, 0)
        self.setCentralWidget(self.widget)
        self.show()

    def rearrange(self):
        self.set_enable_all_hardware_buttons(False)
        self.beamstop_mover.rearrange_all_beamstops()
        self.set_enable_all_hardware_buttons(True)

    def home(self):
        self.set_enable_all_hardware_buttons(False)
        self.absorber_hardware.home()
        self.set_enable_all_hardware_buttons(True)

    def set_enable_all_hardware_buttons(self, enabled):
        self.button_re_arrange.setEnabled(enabled)
        self.button_home.setEnabled(enabled)


class ImageDrawer:
    def __init__(self, config, absorber_hardware, beamstop_manager):
        self.lg = logging.getLogger("main.gui.imagedrawer")
        self.lg.debug("initializing image drawer")
        self.config = config
        self.absorber_hardware = absorber_hardware
        self.beamstop_manager = beamstop_manager
        self.im_view = pg.ImageView()
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

    def add_handle(self):
        self.lg.debug("adding handle")
        handle = pg.CircleROI([100, 100], [50, 50], pen=(9, 15), removable=True)
        handle.sigRemoveRequested.connect(self.remove_handle)
        self.add_graphics_item(handle, "handles")

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
        self.absorber_hardware.updater.posChanged.connect(self.set_crosshair_pos)
        self.absorber_hardware.updater.gripperChanged.connect(self.set_crosshair_color)

    def set_crosshair_pos(self, pos):
        img_pos = self.machine_to_img_coord(pos)
        self.items["crosshair"][0].setValue(img_pos[0])
        self.items["crosshair"][1].setValue(img_pos[1])

    def set_crosshair_color(self, gripper_pos):
        color = self.config.Gui.color_crosshair.map(gripper_pos)
        self.items["crosshair"][0].setPen(color)
        self.items["crosshair"][1].setPen(color)
