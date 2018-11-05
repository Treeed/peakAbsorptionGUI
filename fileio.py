from PyQt5 import QtGui
import fabio


class FileHandler:
    def __init__(self, im_view, parent_widget):
        self.im_view = im_view
        self.parent_widget = parent_widget

    def open_file(self):
        file_name, _ = QtGui.QFileDialog.getOpenFileName(self.parent_widget, "Open Image")
        if file_name:
            arr = fabio.open(str(file_name)).data
            self.im_view.set_image(arr)
