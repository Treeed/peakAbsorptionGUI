from PyQt5 import QtGui, QtWidgets, QtCore
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

    def save_state(self, filename, save_handles=False, save_parked_beamstops=True, save_active_beamstops=True):
        """saves the current beamstop positions and if enabled handle positions to a file"""
        to_save = {}
        if save_active_beamstops and np.logical_not(self.beamstop_manager.beamstop_parked).any():
            to_save["beamstops"] = []
            for beamstop in self.beamstop_manager.beamstops[np.logical_not(self.beamstop_manager.beamstop_parked)]:
                to_save["beamstops"].append({
                    "position": list(beamstop)
                })
        if save_parked_beamstops and self.beamstop_manager.beamstop_parked.any():
            if "beamstops" not in to_save:
                to_save["beamstops"] = []
            for beamstop in self.beamstop_manager.beamstops[self.beamstop_manager.beamstop_parked != 0]:
                to_save["beamstops"].append({
                    "position": list(beamstop)
                })
        if save_handles and self.im_view.items["handles"]:
            to_save["handles"] = []
            for handle in self.im_view.get_handles_machine_coords():
                to_save["handles"].append({
                    "position": list(handle)
                })
        if "beamstops" not in to_save and "handles" not in to_save:
            self.lg.warning("Nothing selected for saving")
            return

        with open(filename, "w") as output_file:
            json.dump(to_save, output_file, indent=4)
        self.lg.info("saved current state to %s", filename)

    def save_state_gui(self):
        """Displays a dialog to select the file name and which positions to save"""
        filename, _ = QtGui.QFileDialog.getSaveFileName(self.parent_widget, 'Save State', filter="Peak Absorber Data File (*.pabs);;Any File (*)")
        if not filename:
            self.lg.warning("no file name selected")
            return

        checkboxes = {
            "beamstops":
                {"text": "beamstops",
                 "children": {
                     "active": {"text": "active_beamstops"},
                     "parked": {"text": "parked_beastops"}},
                 "expanded": True},
            "handles":
                {"text": "handles"}
        }

        CheckboxDialog(checkboxes, "Select positions to save:").exec_()

        self.save_state(filename,
                        save_handles=checkboxes["handles"]["checked"],
                        save_parked_beamstops=checkboxes["beamstops"]["children"]["parked"]["checked"],
                        save_active_beamstops=checkboxes["beamstops"]["children"]["active"]["checked"])

    def load_state(self, loaded_data, load_beamstops=True, load_handles=True):
        loaded_beamstops = loaded_handles = 0
        if load_beamstops and "beamstops" in loaded_data and loaded_data["beamstops"]:
            beamstops = np.array([beamstop["position"] for beamstop in loaded_data["beamstops"]])
            loaded_beamstops = self.beamstop_manager.add_beamstops(beamstops)

        if load_handles and "handles" in loaded_data and loaded_data["handles"]:
            handles = np.array([handle["position"] for handle in loaded_data["handles"]])
            for handle in handles:
                self.im_view.add_handle_in_machine_coord(handle)
            loaded_handles = len(handles)
        self.lg.info("loaded %s beamstops and %s handles", loaded_beamstops, loaded_handles)

    def load_state_file(self, filename, load_beamstops=True, load_handles=True):
        """loads beamstops and handles from a specified file name.
        This is separate from load_state so the gui version can first load and evaluate the data before passing it to load_state"""
        with open(filename, "r") as input_file:
            loaded = json.load(input_file)
        self.load_state(loaded, load_beamstops, load_handles)

    def load_state_gui(self):
        """displays dialogs what file to load and what positions to load from the file"""
        filename, _ = QtGui.QFileDialog.getOpenFileName(self.parent_widget, "Open Peak Absorber Data File", filter="Peak Absorber Data File (*.pabs);;Any File (*)")
        if not filename:
            self.lg.warning("no file selected")
            return

        with open(filename, "r") as input_file:
            loaded = json.load(input_file)

        # generate the tree of checkboxes with the positions in it
        checkboxes = {}
        for itemtype in ["beamstops", "handles"]:
            if itemtype in loaded and loaded[itemtype]:
                checkboxes[itemtype] = {"text": itemtype,
                                        "children": {},
                                        "expanded": False}
                for index, item in enumerate(loaded[itemtype]):
                    checkboxes[itemtype]["children"][index] = {"text": str(item)}
        if not checkboxes:
            self.lg.warning("file is empty, nothing to show")
            return

        if not CheckboxDialog(checkboxes, "Select positions to load:").exec() == QtWidgets.QDialog.Accepted:
            self.lg.warning("dialog was cancelled")
            return

        # remove every position that wasn't checked
        for itemtype in ["beamstops", "handles"]:
            if itemtype not in checkboxes:
                continue
            for index, item in sorted(checkboxes[itemtype]["children"].items(), key=lambda idx: idx[0], reverse=True):
                if not item["checked"]:
                    del(loaded[itemtype][index])
        self.load_state(loaded)


class CheckboxDialog(QtWidgets.QDialog):
    def __init__(self, checkboxes, instruction, parent=None):
        """Dialog that displays the checkboxes from the dictionary "checkboxes" and adds a key "checked" to every checkbox in the dictionary after the dialog was closed.
        Run like this: CheckboxDialog(checkboxes, "Select positions to load:").exec()"""
        super(CheckboxDialog, self).__init__(parent)
        self.checkboxes = checkboxes
        layout = QtWidgets.QVBoxLayout(self)

        label = QtWidgets.QLabel()
        label.setText(instruction)
        layout.addWidget(label)

        tree = QtWidgets.QTreeWidget()

        self.add_checkboxes(checkboxes, tree)
        tree.setHeaderHidden(1)
        layout.addWidget(tree)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.finished.connect(self.evaluate_all_checkboxes)

    def add_checkboxes(self, checkboxes, parentbox):
        for box_name, box in checkboxes.items():
            box["box_item"] = QtWidgets.QTreeWidgetItem(parentbox)
            box["box_item"].setText(0, box["text"])
            if "children" in box and box["children"]:
                box["box_item"].setFlags(box["box_item"].flags() | QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable)
                self.add_checkboxes(box["children"], box["box_item"])
            else:
                box["box_item"].setFlags(box["box_item"].flags() | QtCore.Qt.ItemIsUserCheckable)
            box["box_item"].setCheckState(0, QtCore.Qt.Checked)
            if "expanded" in box:
                box["box_item"].setExpanded(box["expanded"])

    def evaluate_checkboxes(self, checkboxes):
        for box_name, box in checkboxes.items():
            box["checked"] = box["box_item"].checkState(0)
            if "children" in box and box["children"]:
                self.evaluate_checkboxes(box["children"])

    def evaluate_all_checkboxes(self):
        self.evaluate_checkboxes(self.checkboxes)
