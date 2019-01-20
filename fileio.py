from PyQt5 import QtGui
import fabio
import logging
import numpy as np
import json


class FileHandler:
    def __init__(self, config, im_view, parent_widget, beamstop_manager, beamstop_mover):
        self.config = config
        self.im_view = im_view
        self.parent_widget = parent_widget
        self.beamstop_manager = beamstop_manager
        self.beamstop_mover = beamstop_mover

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

    def save_state(self, save_handles=False):
        """saves the current beamstop positions and if enabled handle positions to a file"""
        file_name, _ = QtGui.QFileDialog.getSaveFileName(self.parent_widget, 'Save State', filter="Peak Absorber Data File (*.pabs);;Any File (*)")
        if not file_name:
            self.lg.warning("no file name selected")
            return

        to_save = {"beamstops": []}
        for beamstop_index, beamstop in enumerate(self.beamstop_manager.beamstops):
            to_save["beamstops"].append({
                "position": list(beamstop)
            })
        if save_handles:
            to_save["handles"] = []
            for handle in self.im_view.get_handles_machine_coords():
                to_save["handles"].append({
                    "position": list(handle)
                })
        with open(file_name, "w") as output_file:
            json.dump(to_save, output_file, indent=4)
        self.lg.info("saved current state to %s", file_name)

    def save_state_handles(self):
        """for saving the state with handles if no arguments can be provided (qtgui buttons)"""
        self.save_state(True)

    def load_state(self):
        file_name, _ = QtGui.QFileDialog.getOpenFileName(self.parent_widget, "Open Peak Absorber Data File", filter="Peak Absorber Data File (*.pabs);;Any File (*)")
        if not file_name:
            self.lg.warning("no file selected")
            return

        with open(file_name, "r") as input_file:
            loaded = json.load(input_file)
        if "beamstops" in loaded and loaded["beamstops"]:
            beamstops = np.array([beamstop["position"] for beamstop in loaded["beamstops"]])
            self.beamstop_manager.add_beamstops(beamstops)

        if "handles" in loaded and loaded["handles"]:
            handles = np.array([handle["position"] for handle in loaded["handles"]])
            for handle in handles:
                self.im_view.add_handle_in_machine_coord(handle)
