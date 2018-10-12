from PyQt4 import QtGui, QtCore
import sys
import pyqtgraph as pg
import numpy as np
from PIL import Image
import pickle
import time
import math
import tango


class ViewData(QtGui.QMainWindow):
    def __init__(self, parent=None):
        super(ViewData, self).__init__(parent)
        self.widget = QtGui.QWidget()
        self.widget.setLayout(QtGui.QGridLayout())

        # ni=Image.open('SYN_49a_piston_OK.tif')
        ni = Image.open('DAC4-00002MODD.png')  # default_image
        arr = np.array(ni)
        self.imv = pg.ImageView()

        # imv2=pg.ViewBox()
        # self.widget.addItem(imv2)

        button_new_target = QtGui.QPushButton("new target")
        button_new_target.clicked.connect(self.change)
        # button_new_target.move(600,50)

        button_open_file = QtGui.QPushButton("open image")
        button_open_file.clicked.connect(self.open_file)
        # button_open_file.move(600,100)

        button_write_to_file = QtGui.QPushButton("write to file")
        button_write_to_file.clicked.connect(self.write_data)

        button_reset_roi = QtGui.QPushButton("reset ROI")
        button_reset_roi.clicked.connect(self.reset_roi)

        button_read_file = QtGui.QPushButton("read file")
        button_read_file.clicked.connect(self.read_data)

        button_move_pellets = QtGui.QPushButton("move pellets")
        # button_move_pellets.clicked.connect(self.moveAll)
        button_move_pellets.clicked.connect(self.move_all)

        button_calibrate = QtGui.QPushButton("calibrate")
        button_calibrate.clicked.connect(self.calibrate)

        button_re_arrange = QtGui.QPushButton("rearrange")
        button_re_arrange.clicked.connect(self.rearrange)

        button_add_bs = QtGui.QPushButton("add_bs")
        button_add_bs.clicked.connect(self.add_bs)

        mx = 'p02/motor/elab.01'  # x_motor
        my = 'p02/motor/elab.02'  # y_motor
        gr = 'p02/register/elab.out08'  # io_register
        self.gripper = tango.DeviceProxy(gr)
        self.motox = tango.DeviceProxy(mx)
        self.motoy = tango.DeviceProxy(my)
        self.yBacklash = 3.0  # backlash
        self.amount = 5  # amount_of_beamstops
        self.imv.setImage(arr)
        self.roiAll = []  # create_list(roi means region of interest)
        self.roiPos = []  # create_list only for position data
        self.roiSize = []  # create_list which contains updated sizes of rois
        self.roiPosOld = []  # create roi pos list which is later used as buffer
        self.filenames = QtCore.QStringList()
        self.filenames.append('DAC4-00002MODD.png')

        self.roiPos.append([80, 50, 0])  # first_roi_default_position
        self.roiSize.append([20, 20])  # first_roi_default_size
        self.roiAll.append(pg.CircleROI([80, 50, 0], [20, 20], pen=(15, 15)))
        self.roiAll[0].sigRegionChanged.connect(self.update)

        self.widget.layout().addWidget(self.imv, 0, 0, 3, 3)
        self.widget.layout().addWidget(button_new_target, 4, 0)
        self.widget.layout().addWidget(button_open_file, 4, 1)
        self.widget.layout().addWidget(button_write_to_file, 4, 2)
        self.widget.layout().addWidget(button_reset_roi, 5, 0)
        self.widget.layout().addWidget(button_move_pellets, 5, 1)
        self.widget.layout().addWidget(button_read_file, 5, 2)
        self.widget.layout().addWidget(button_calibrate, 6, 0)
        self.widget.layout().addWidget(button_re_arrange, 6, 1)
        self.widget.layout().addWidget(button_add_bs, 6, 2)
        # self.widget.layout().addWidget(imv2,5,5,3,3)
        self.setCentralWidget(self.widget)
        self.show()

    def update(self):
        for x in range(0, len(self.roiAll)):
            self.roiPos[x] = [self.roiAll[x].pos()[0], self.roiAll[x].pos()[1], 0]
            self.roiSize[x] = self.roiAll[x].size()

    def change(self):
        self.roiAll.append(pg.CircleROI([5, 5, 0], [20, 20], pen=(9, 15)))
        self.roiAll[len(self.roiAll) - 1].sigRegionChanged.connect(self.update)
        self.imv.addItem(self.roiAll[len(self.roiAll) - 1])
        self.roiPos.append([5, 5, 0])
        self.roiSize.append([20, 20])


    def open_file(self):
        # pdb.set_trace()
        file_handling = QtGui.QFileDialog()
        file_handling.setFileMode(QtGui.QFileDialog.AnyFile)
        if file_handling.exec_():
            self.filenames = file_handling.selectedFiles()
            name = self.filenames[0]
            ni = Image.open(str(name))
            arr = np.array(ni)
            self.imv = pg.ImageView()
            self.imv.setImage(arr)
            self.widget.layout().addWidget(self.imv, 0, 0, 3, 3)
            self.roiAll = []
            self.roiPos = []
            self.roiSize = []

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


    def wait_move(self, motor):
        while motor.state() == tango.DevState.MOVING:
            time.sleep(0.01)


    def make_bs_list(self, amount):
        bs_list = []
        for i in range(0, amount):
            bs_list.append([0, 0 + i * 10])
        return bs_list


    def calc_ind(self, x):
        for i in range(0, len(x)):
            x[i][2] = math.sqrt(pow(x[i][0], 2) + pow(x[i][1], 2))
        return x


    def sort_ind(self, x, item_ind):
        x = sorted(x, key=lambda item: item[item_ind])
        return x


    def list_cmp(self, o_list, n_list):
        ind = []
        j = 0
        for i in range(0, len(o_list)):
            if not(o_list[i] == n_list[i]):
                ind.append(i) #TODO: sure you want to append i? j is not used
                j = +1 #TODO: this just assigns 1 to j
        return ind


    def calc_alpha(self, xn, x0, yn, y0):
        alpha = 180 / math.pi * math.atan(float(yn - y0) / float(xn - x0))
        return alpha


    def calc_vec_len(self, xn, x0, yn, y0):
        length = math.sqrt(pow((xn - x0), 2) + pow((yn - y0), 2))
        return length


    def add_bs(self):
        new_list = []
        buf_list = self.roiPos
        bs = [10, 10]
        target = []
        for i in range(0, len(buf_list)):
            buf_list[i][2] = self.calc_vec_len(buf_list[i][0], bs[0], buf_list[i][1], bs[1])
        target.append(buf_list[len(buf_list) - 1])
        target[0].append(0)
        for i in range(0, len(buf_list)):
            if buf_list[i][2] < target[0][2]:
                new_list.append(buf_list[i])
        target[0][3] = self.calc_alpha(target[0][0], bs[0], target[0][1], bs[1])
        for i in range(0, len(new_list)):
            new_list[i].append(0)
            new_list[i][3] = new_list[0][2] * math.tan(
                math.pi / 180 * self.calc_alpha(new_list[i][0], bs[0], new_list[i][1], bs[1]) - target[0][3])


    def rearrange(self):
        ch_list = []
        ch_ind = self.list_cmp(self.roiPos, self.roiPosOld)
        for i in range(0, len(ch_ind)):
            ch_list.append(self.roiPosOld[ch_ind[i]])
        for i in range(0, len(ch_list)):
            self.gripper.value = 0
            self.motox.position = ch_list[i][0]
            self.wait_move(self.motox)
            self.motoy.position = ch_list[i][1]
            self.wait_move(self.motoy)
            self.gripper.value = 1
            time.sleep(2)
            self.motox.position = self.roiPos[i][0]
            self.wait_move(self.motoy)
            self.motoy.position = 400 - self.roiPos[i][1]
            self.wait_move(self.motoy)
            # self.motoy.position = 400 - self.roiPos[i][1] - self.yBacklash
            # while (self.motoy.state() == tango.DevState.MOVING):
            #	time.sleep(0.01)
            self.gripper.value = 0
            time.sleep(2)
            self.motox.position = 0
            self.wait_move(self.motox)
            self.motoy.position = 0
            self.wait_move(self.motoy)
        self.roiPosOld = self.roiPos


    def move_all(self):
        # pdb.set_trace()
        self.gripper.value = 0
        time.sleep(2)
        self.roiPosOld = self.roiPos
        bs_list = self.make_bs_list(self.amount)
        self.roiPos = self.calc_ind(self.roiPos)
        self.roiPos = self.sort_ind(self.roiPos, 2)
        # pdb.set_trace()

        for i in range(0, len(self.roiPos)):
            self.motox.position = bs_list[i][0]
            self.wait_move(self.motox)
            self.motoy.position = bs_list[i][1]
            self.wait_move(self.motoy)
            self.gripper.value = 1
            time.sleep(2)
            self.motox.position = self.roiPos[i][0]
            self.wait_move(self.motox)
            self.motoy.position = 400 - self.roiPos[i][1]
            self.wait_move(self.motoy)
            self.gripper.value = 0
            time.sleep(2)
        self.motox.position = 0
        self.motoy.position = 0
        self.roi_pos_old = self.roiPos


    def calibrate(self):
        slew_buf_x = self.motox.slewrate
        slew_buf_y = self.motox.slewrate
        self.motox.slewrate = 400
        self.motoy.slewrate = 400
        self.motox.moveToCwLimit()
        self.wait_move(self.motox)
        self.motox.calibrate(0)
        self.motoy.moveToCwLimit()
        self.wait_move(self.motox) #TODO: sure you wait for x again?
        self.motoy.calibrate(0) #TODO: don't use calibrate
        self.motox.slewrate = slew_buf_x
        self.motoy.slewrate = slew_buf_y


    def reset_roi(self):
        for x in range(0, len(self.roiAll)):
            self.imv.removeItem(self.roiAll[x])
        self.roiAll = []
        self.roiPos = []


def main():
    app = QtGui.QApplication(sys.argv)
    vd = ViewData()
    vd.show()
    app.exec_()


if __name__ == '__main__':
    main()
