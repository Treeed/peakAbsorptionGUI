import math
import pyqtgraph as pg
import numpy as np
import scipy.optimize

class BeamstopManager:
    def __init__(self, im_view, absorber_hardware):
        self.im_view = im_view
        self.absorber_hardware = absorber_hardware

        self.beamstop_handles = [] # movable handles to specify the targets where the beamstops will be moved
        self.teststops = []

    def reset_all(self):
        for beamstop in self.beamstop_handles:
            self.im_view.removeItem(beamstop)
        #TODO: reset the physical beamstops to their original positions

    def add_handle(self):
        self.beamstop_handles.append(pg.CircleROI([100, 100], [300, 300], pen=(9, 15)))
        self.im_view.addItem(self.beamstop_handles[-1])

    def add_teststop(self):
        self.teststops.append(pg.CircleROI([100, 100], [300, 300], pen=(3, 15)))
        self.im_view.addItem(self.teststops[-1])



    def rearrange_all_beamstops(self):
        self.absorber_hardware.beamstops = np.array([handle.pos() for handle in self.teststops])

        handle_positions = np.array([handle.pos() for handle in self.beamstop_handles])

        beamstop_inactive_cost = 500 #how much virtual distance (mm) is added to penalise moving extra beamstops into the active area
        combinations, distances = self.calc_beamstop_assignment(handle_positions, beamstop_inactive_cost * (not self.absorber_hardware.beamstop_active))
        #TODO: find best path (including moving out)
        epsilon = 0.0001  # beamstops that are offset from their target below this value are considered floating point errors and will not be moved
        required_moves = [(combination[0], handle_positions[combination[1]]) for combination in np.swapaxes(combinations, 0, 1)[distances > epsilon]]
        #reststops = np.delete(self.absorber_hardware.beamstops, combinations[:,1])[np.delete(not self.absorber_hardware.beamstop_active, combinations[:,1])]
        #required_moves.extend(stuff with targets
        self.move_beamstops(required_moves)
        #TODO: active beamstops
        #TODO: when using extra beamstops dont check for moving out
        np.setdiff1d(range(len()))

    def move_beamstops(self, required_moves):
        for move in required_moves:
            tt = pg.LineSegmentROI([self.absorber_hardware.beamstops[move[0]], move[1]])
            self.im_view.addItem(tt)
            # self.absorber_hardware.move_beamstop(move[0], move[1])

    #returns combinations of [beamstops, target_positions] and the distances between the two
    def calc_beamstop_assignment(self, target_positions, penalty):
        #calculate distances from all beamstop targets to all beamstops and add penalties for suboptimal beamstops. Penalty list must have length of beamstop list
        distances = calc_vec_len(target_positions - self.absorber_hardware.beamstops[:,np.newaxis]) + penalty
        combinations = np.array(scipy.optimize.linear_sum_assignment(distances))
        return combinations, distances[tuple(combinations)]

    def calcnextbs(self):
        new_list = []
        buf_list = self.roiPos
        bs = [10, 10]
        target = []
        for i in range(0, len(buf_list)):
            buf_list[i][2] = self.calc_vec_len([buf_list[i][0] - bs[0], buf_list[i][1] - bs[1]])
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

def calc_vec_len(vec):
    vec = np.array(vec)
    return np.sqrt((vec*vec).sum(axis=-1))