import pickle
from PyQt5 import QtGui
import fabio

class FileHandler:
    def __init__(self, im_view, parent_widget):
        self.im_view = im_view
        self.parent_widget = parent_widget

    def write_data(self):
        with open('%s.data' % str(self.filenames[0]), 'wb') as f:
            data_container = [self.filenames[0], self.roiPos, self.roiSize]
            pickle.dump(data_container, f)

    def read_data(self):
        file_handling = QtGui.QFileDialog()
        file_handling.setFileMode(QtGui.QFileDialog.AnyFile)
        if file_handling.exec_():
            self.filenames = file_handling.selectedFiles()
            name = self.filenames[0]
        with open(str(name), 'r') as f:
            data = pickle.load(f)
        self.reset_roi()
        self.roiPos = data[1]
        self.roiSize = data[2]
        for x in range(0, len(self.roiPos)):
            self.roiAll.append(
                pg.CircleROI([self.roiPos[x][0], self.roiPos[x][1]], [self.roiSize[x][0], self.roiSize[x][1]],
                             pen=(9, 15)))
            self.roiAll[len(self.roiAll) - 1].sigRegionChanged.connect(self.update)
            self.imv.addItem(self.roiAll[len(self.roiAll) - 1])

    def open_file(self):
        file_name, _ = QtGui.QFileDialog.getOpenFileName(self.parent_widget, "Open Image")
        if file_name:
            arr = fabio.open(str(file_name)).data
            self.im_view.setImage(arr)