import math

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


def reset_roi(self):
    for x in range(0, len(self.roiAll)):
        self.imv.removeItem(self.roiAll[x])
    self.roiAll = []
    self.roiPos = []

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