import math
import pyqtgraph as pg


class BeamstopManager:
    def __init__(self, im_view, absorber_hardware):
        self.im_view = im_view
        self.absorber_hardware = absorber_hardware

        self.beamstop_handles = [] #movable handles to specify the targets where the beamstops will be moved

    def reset_all(self):
        for beamstop in self.beamstop_handles:
            self.im_view.removeItem(beamstop)
        #TODO: reset the physical beamstops to their original positions

    def add_handle(self):
        self.beamstop_handles.append(pg.CircleROI([5, 5], [20, 20], pen=(9, 15)))
        self.im_view.addItem(self.beamstop_handles[-1])

    def calcnextbs(self):
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

def calc_vec_len(x1, x2, y1, y2):
    return math.sqrt(pow((x1 - x2), 2) + pow((y1 - y2), 2))