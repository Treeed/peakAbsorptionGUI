from PyQt5 import QtGui
import pyqtgraph as pg
import pyqtgraphutils
import numpy as np

import absorberfunctions
import fileio
import hardware


class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        super().__init__()
        self.widget = QtGui.QWidget()
        self.widget.setLayout(QtGui.QGridLayout())

        self.beamstop_manager = absorberfunctions.BeamstopManager()
        self.absorber_hardware = hardware.PeakAbsorberHardware()
        self.image_view = ImageDrawer(self.absorber_hardware, self.beamstop_manager)
        self.file_handler = fileio.FileHandler(self.image_view, self.widget)
        self.beamstop_mover = absorberfunctions.BeamstopMover(self.image_view, self.absorber_hardware, self.beamstop_manager)

        button_new_target = QtGui.QPushButton("new handle")
        button_new_target.clicked.connect(self.image_view.add_handle)

        button_open_file = QtGui.QPushButton("open image")
        button_open_file.clicked.connect(self.file_handler.open_file)

        button_reset_all_beamstops = QtGui.QPushButton("reset all handles")
        button_reset_all_beamstops.clicked.connect(self.image_view.reset_all_handles)

        button_re_arrange = QtGui.QPushButton("rearrange")
        button_re_arrange.clicked.connect(self.beamstop_mover.rearrange_all_beamstops)

        test = QtGui.QPushButton("test")
        test.clicked.connect(self.image_view.add_teststops)

        self.widget.layout().addWidget(self.image_view.im_view, 0, 0, 3, 3)
        self.widget.layout().addWidget(button_new_target, 4, 0)
        self.widget.layout().addWidget(button_open_file, 4, 1)
        self.widget.layout().addWidget(button_reset_all_beamstops, 5, 0)
        self.widget.layout().addWidget(button_re_arrange, 6, 1)
        self.widget.layout().addWidget(test, 6, 2)
        self.setCentralWidget(self.widget)
        self.show()


class ImageDrawer:
    def __init__(self, absorber_hardware, beamstop_manager):
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

        self.draw_absorber_geometry()
        self.init_crosshair()

    def draw_absorber_geometry(self):
        self.box_in_machine_coords("limit_box", [0, 0], self.absorber_hardware.limits)
        self.box_in_machine_coords("detector_box", self.absorber_hardware.detector_origin, self.absorber_hardware.active_area)
        for parking_position in self.beamstop_manager.parking_positions:
            self.circle_in_machine_coord("parking_spots", parking_position)

    def img_to_machine_coord(self, point):
        return np.array(point)*self.absorber_hardware.pixel_size+self.absorber_hardware.detector_origin

    def machine_to_img_coord(self, point):
        return (np.array(point)-self.absorber_hardware.detector_origin)/self.absorber_hardware.pixel_size

    def img_to_machine_scale(self, point):
        return np.array(point) * self.absorber_hardware.pixel_size

    def machine_to_img_scale(self, point):
        return np.array(point) / self.absorber_hardware.pixel_size

    def box_in_machine_coords(self, purpose, pos, size, color='w'):
        box = pyqtgraphutils.RectangleItem(self.machine_to_img_coord(pos), self.machine_to_img_scale(size), color)
        self.im_view.addItem(box)
        self.items[purpose].append(box)

    def circle_in_machine_coord(self, purpose, pos, radius=None, color='w'):
        if radius is None:
            radius = self.absorber_hardware.beamstop_radius
        circle = pyqtgraphutils.CircleItem(self.machine_to_img_coord(pos), self.machine_to_img_scale(radius)[0], color)
        self.im_view.addItem(circle)
        self.items[purpose].append(circle)

    def move_circle_in_machine_coord(self, circle_nr,  pos):
        self.items["beamstop_circles"][circle_nr].setCenter(self.machine_to_img_coord(pos))

    def add_graphics_item(self, item, purpose):
        self.im_view.addItem(item)
        self.items[purpose].append(item)

    def add_handle(self):
        handle = pg.CircleROI([100, 100], [50, 50], pen=(9, 15), removable=True)
        handle.sigRemoveRequested.connect(self.remove_handle)
        self.im_view.addItem(handle)
        self.items["handles"].append(handle)

    def set_image(self, array):
            self.im_view.setImage(array)

    def reset_all_handles(self):
        for handle in self.items["handles"]:
            self.im_view.removeItem(handle)
        self.items["handles"].clear()

    def remove_handle(self, handle):
        self.im_view.removeItem(handle)
        self.items["handles"].remove(handle)

    # testing
    def add_teststops(self):
        teststops = self.beamstop_manager.parking_positions
        self.beamstop_manager.add_beamstops(np.arange(len(teststops)))
        for beamstop in teststops:
            self.circle_in_machine_coord("beamstop_circles", beamstop, color='r')
        # TODO: where to draw the circles? "add beamstops"?

    def get_handles_machine_coords(self):
        return np.array([self.img_to_machine_coord(np.array(handle.pos())+np.array(handle.size())/2) for handle in self.items["handles"]])

    def init_crosshair(self):
        line_x = pg.InfiniteLine(0, 90, pg.mkPen('g'))
        line_y = pg.InfiniteLine(0, 0, pg.mkPen('g'))
        self.add_graphics_item(line_x, "crosshair")
        self.add_graphics_item(line_y, "crosshair")
        self.absorber_hardware.updater.posChanged.connect(self.set_crosshair_pos)

    def set_crosshair_pos(self, pos):
        img_pos = self.machine_to_img_coord(pos)
        self.items["crosshair"][0].setValue(img_pos[0])
        self.items["crosshair"][1].setValue(img_pos[1])
