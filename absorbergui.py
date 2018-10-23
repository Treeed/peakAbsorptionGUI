from PyQt5 import QtGui
import pyqtgraph as pg

import absorberfunctions
import fileio
import hardware

class ViewData(QtGui.QMainWindow):
    def __init__(self):
        super().__init__()
        self.widget = QtGui.QWidget()
        self.widget.setLayout(QtGui.QGridLayout())

        self.im_view = pg.ImageView()

        self.file_handler = fileio.FileHandler(self.im_view, self.widget)
        self.absorber_hardware = hardware.PeakAbsorberHardware()
        self.beamstops = absorberfunctions.BeamstopManager(self.im_view, self.absorber_hardware)

        button_new_target = QtGui.QPushButton("new beamstop")
        button_new_target.clicked.connect(self.beamstops.add_handle)

        button_open_file = QtGui.QPushButton("open image")
        button_open_file.clicked.connect(self.file_handler.open_file)

        button_write_to_file = QtGui.QPushButton("write to file")
        button_write_to_file.clicked.connect(self.file_handler.write_data)

        button_reset_all_beamstops = QtGui.QPushButton("reset all beamstops")
        button_reset_all_beamstops.clicked.connect(self.beamstops.reset_all)

        button_read_file = QtGui.QPushButton("read file")
        button_read_file.clicked.connect(self.file_handler.read_data)

        button_move_pellets = QtGui.QPushButton("move pellets")
        button_move_pellets.clicked.connect(self.absorber_hardware.move_all)

        button_calibrate = QtGui.QPushButton("calibrate")
        button_calibrate.clicked.connect(self.absorber_hardware.calibrate)

        button_re_arrange = QtGui.QPushButton("rearrange")
        button_re_arrange.clicked.connect(self.absorber_hardware.rearrange)


        self.widget.layout().addWidget(self.im_view, 0, 0, 3, 3)
        self.widget.layout().addWidget(button_new_target, 4, 0)
        self.widget.layout().addWidget(button_open_file, 4, 1)
        self.widget.layout().addWidget(button_write_to_file, 4, 2)
        self.widget.layout().addWidget(button_reset_all_beamstops, 5, 0)
        self.widget.layout().addWidget(button_move_pellets, 5, 1)
        self.widget.layout().addWidget(button_read_file, 5, 2)
        self.widget.layout().addWidget(button_calibrate, 6, 0)
        self.widget.layout().addWidget(button_re_arrange, 6, 1)
        self.setCentralWidget(self.widget)
        self.show()



