from PyQt5 import QtGui
import pyqtgraph as pg
import pyqtgraphutils

import absorberfunctions
import fileio
import hardware

class ViewData(QtGui.QMainWindow):
    def __init__(self):
        super().__init__()
        self.widget = QtGui.QWidget()
        self.widget.setLayout(QtGui.QGridLayout())

        self.im_view = pg.ImageView()
        self.im_view.getView().invertY(False)

        self.file_handler = fileio.FileHandler(self.im_view, self.widget)
        self.absorber_hardware = hardware.PeakAbsorberHardware()
        self.beamstops = absorberfunctions.BeamstopManager(self.im_view, self.absorber_hardware)


        button_new_target = QtGui.QPushButton("new handle")
        button_new_target.clicked.connect(self.beamstops.add_handle)

        button_open_file = QtGui.QPushButton("open image")
        button_open_file.clicked.connect(self.file_handler.open_file)

        button_reset_all_beamstops = QtGui.QPushButton("reset all handles")
        button_reset_all_beamstops.clicked.connect(self.beamstops.reset_all)

        button_re_arrange = QtGui.QPushButton("rearrange")
        button_re_arrange.clicked.connect(self.beamstops.rearrange_all_beamstops)

        test = QtGui.QPushButton("test")
        test.clicked.connect(self.beamstops.add_teststops)


        self.widget.layout().addWidget(self.im_view, 0, 0, 3, 3)
        self.widget.layout().addWidget(button_new_target, 4, 0)
        self.widget.layout().addWidget(button_open_file, 4, 1)
        self.widget.layout().addWidget(button_reset_all_beamstops, 5, 0)
        self.widget.layout().addWidget(button_re_arrange, 6, 1)
        self.widget.layout().addWidget(test, 6, 2)
        self.setCentralWidget(self.widget)
        self.show()


        self.limit_box = pyqtgraphutils.RectangleItem(self.beamstops.machine_to_img_coord([0, 0]), self.beamstops.machine_to_img_scale(self.absorber_hardware.limits))
        self.im_view.addItem(self.limit_box)
        self.detector_box = pyqtgraphutils.RectangleItem(self.beamstops.machine_to_img_coord(self.absorber_hardware.detector_origin), self.beamstops.machine_to_img_scale(self.absorber_hardware.active_area))
        self.im_view.addItem(self.detector_box)
        self.parking_spots = [self.beamstops.circle_in_machine_coord(parking_position) for parking_position in self.absorber_hardware.parking_positions]
        for spot in self.parking_spots:
            self.im_view.addItem(spot)