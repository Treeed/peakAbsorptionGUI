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
        if not file_name:
            self.lg.warning("no image selected")
            return
        try:
            arr = fabio.open(str(file_name)).data
        except IOError as fabio_msg:
            self.lg.error("image opening failed: %s", str(fabio_msg))
        else:
            arr = self.manipulate_image(arr)
            self.lg.debug("setting image of size %s", str(arr.shape))
            self.im_view.set_image(arr)

    def manipulate_image(self, arr):
        """apply image manipulations to the array. A single rot90 is applied at the end regardless of configuration because the imageviewer is tilted by -90°"""
        for manipulation in self.config.Detector.image_manipulations + ["rot90"]:
            if manipulation == "rot90":
                arr = np.rot90(arr, 1, (1, 0))
            if manipulation == "rot180":
                arr = np.rot90(arr, 2, (1, 0))
            if manipulation == "rot270":
                arr = np.rot90(arr, 3, (1, 0))
            if manipulation == "mir_horiz":
                arr = np.fliplr(arr)
            if manipulation == "mir_vert":
                arr = np.flipud(arr)
        return arr

    def open_beamstop_list(self):
        file_name, _ = QtGui.QFileDialog.getOpenFileName(self.parent_widget, "Open Beamstop List", filter="Comma Separated Values (*.csv);;Any File (*)")
        if file_name:
            with open(file_name, newline='') as parking_list:
                parking_nrs = np.loadtxt(parking_list, delimiter=",", dtype=int)
            self.im_view.add_beamstop_circles(self.beamstop_manager.add_beamstops(parking_nrs))
