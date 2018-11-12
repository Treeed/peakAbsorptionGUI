from PyQt5 import QtGui
import fabio
import logging
import numpy as np


class FileHandler:
    def __init__(self, config, im_view, parent_widget, beamstop_manager):
        self.config = config
        self.im_view = im_view
        self.parent_widget = parent_widget
        self.beamstop_manager = beamstop_manager

        self.lg = logging.getLogger("main.fileio.filehandler")

    def open_image(self):
        file_name, _ = QtGui.QFileDialog.getOpenFileName(self.parent_widget, "Open Image")
        self.lg.info("opening image %s", file_name)
        if file_name:
            arr = fabio.open(str(file_name)).data
            self.lg.debug("setting image of size %s", str(arr.shape))
            self.im_view.set_image(arr)

    def open_beamstop_list(self):
        file_name, _ = QtGui.QFileDialog.getOpenFileName(self.parent_widget, "Open Beamstop List", filter="Comma Separated Values (*.csv);;Any File (*)")
        if file_name:
            with open(file_name, newline='') as parking_list:
                parking_nrs = np.loadtxt(parking_list, delimiter=",", dtype=int)
            self.im_view.add_beamstop_circles(self.beamstop_manager.add_beamstops(parking_nrs))


def init_logger():
    lg = logging.getLogger("main")
    lg.setLevel(logging.DEBUG)

    # these values should be configurable, but then we would need to load the config before being able to log that config loading failed...
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(name)-40s: %(message)s', '%Y-%m-%d %H:%M:%S')
    file_handler = logging.FileHandler("absorber.log")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)

    lg.addHandler(file_handler)
    lg.addHandler(console_handler)

    lg.info("initialized logger")
