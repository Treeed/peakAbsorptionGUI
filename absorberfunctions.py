import numpy as np
import scipy.optimize

import absorbergui


class BeamstopMover:
    def __init__(self, im_view, absorber_hardware, beamstop_manager):
        self.im_view = im_view
        self.absorber_hardware = absorber_hardware
        self.beamstop_manager = beamstop_manager

    def rearrange_all_beamstops(self):
        if len(self.im_view.items["handles"]) > len(self.beamstop_manager.beamstops):
            print("not enough beamstops available")  # error
            return

        handle_positions = self.im_view.get_handles_machine_coords()
        # TODO: get machine coordinates
        # TODO: check behaviour without elements
        if handle_positions.size > 0:
            beamstop_inactive_cost = 500  # how much virtual distance (mm) is added to penalise moving extra beamstops into the active area #config
            target_combinations, target_distances = calc_beamstop_assignment(self.beamstop_manager.beamstops, handle_positions, beamstop_inactive_cost * self.beamstop_manager.beamstop_parked.astype(np.bool_))

            epsilon = 0.0001  # beamstops that are offset from their target below this value are considered floating point errors and will not be moved #config
            required_moves = [BeamstopMoveTarget(self.beamstop_manager, combination[0], handle_positions[combination[1]]) for combination in np.swapaxes(target_combinations, 0, 1)[target_distances > epsilon]]

            reststops = np.delete(np.arange(self.beamstop_manager.beamstops.shape[0]), target_combinations[0])[np.delete(np.logical_not(self.beamstop_manager.beamstop_parked), target_combinations[0])]
        else:
            reststops = np.arange(len(self.beamstop_manager.beamstops))[np.logical_not(self.beamstop_manager.beamstop_parked)]
            required_moves = []

        if reststops.size > 0:
            free_parking_position_nrs = np.logical_not(self.beamstop_manager.parking_position_occupied).nonzero()[0]

            if reststops.size > free_parking_position_nrs.size:
                print("not enough parking space available")  # error
                return

            rest_combinations, _ = calc_beamstop_assignment(self.beamstop_manager.beamstops[reststops], self.beamstop_manager.parking_positions[free_parking_position_nrs])
            required_moves.extend(BeamstopMoveParking(self.beamstop_manager, reststops[combination[0]], free_parking_position_nrs[combination[1]]) for combination in np.swapaxes(rest_combinations, 0, 1))

        self.move_beamstops(required_moves)

    def move_beamstops(self, required_moves):
        # TODO: find best path
        for move in required_moves:
            with absorbergui.DrawTempLineInMachCoord(self.im_view, move.get_beamstop_pos(), move.get_target_pos()):
                self.absorber_hardware.move_beamstop(move)
                self.im_view.move_circle_in_machine_coord(move.beamstop_nr, move.get_target_pos())
                # TODO: leave it to update_pos and the move to draw these things instead
        # TODO: home afterwards


class BeamstopManager:
    def __init__(self):
        self.parking_positions = np.array([[10, 10],
                                           [10, 20],
                                           [10, 30],
                                           [10, 40],
                                           [10, 50],
                                           [10, 60],
                                           [10, 70],
                                           [10, 80]])
        # [ 10,  90],
        # [ 10, 100],
        # [ 10, 110],
        # [ 10, 120],
        # [ 10, 130],
        # [ 10, 140],
        # [ 10, 150],
        # [ 10, 160],
        # [ 10, 170],
        # [ 10, 180],
        # [ 10, 190],
        # [ 10, 200],
        # [ 10, 210],
        # [ 10, 220],
        # [ 10, 230],
        # [ 10, 240],
        # [ 10, 250],
        # [ 10, 260],
        # [ 10, 270],
        # [ 10, 280],
        # [ 10, 290],
        # [ 10, 300],
        # [ 10, 310],
        # [ 10, 320],
        # [ 10, 330],
        # [ 10, 340],
        # [ 10, 350],
        # [ 10, 360],
        # [ 10, 370],
        # [ 10, 380],
        # [ 10, 390],
        # [ 20, 390],
        # [ 30, 390],
        # [ 40, 390],
        # [ 50, 390],
        # [ 60, 390],
        # [ 70, 390],
        # [ 80, 390],
        # [ 90, 390],
        # [100, 390],
        # [110, 390],
        # [120, 390],
        # [130, 390],
        # [140, 390],
        # [150, 390],
        # [160, 390],
        # [170, 390],
        # [180, 390],
        # [190, 390],
        # [200, 390],
        # [210, 390],
        # [220, 390],
        # [230, 390],
        # [240, 390],
        # [250, 390],
        # [260, 390],
        # [270, 390],
        # [280, 390],
        # [290, 390],
        # [300, 390],
        # [310, 390],
        # [320, 390],
        # [330, 390],
        # [340, 390],
        # [350, 390],
        # [360, 390],
        # [370, 390],
        # [380, 390],
        # [390, 390],
        # [400, 390],
        # [410, 390],
        # [420, 390],
        # [430, 390],
        # [440, 390],
        # [450, 390],
        # [460, 390],
        # [470, 390],
        # [480, 390],
        # [490, 390],
        # [490, 380],
        # [490, 370],
        # [490, 360],
        # [490, 350],
        # [490, 340],
        # [490, 330],
        # [490, 320],
        # [490, 310],
        # [490, 300],
        # [490, 290],
        # [490, 280],
        # [490, 270],
        # [490, 260],
        # [490, 250],
        # [490, 240],
        # [490, 230],
        # [490, 220],
        # [490, 210],
        # [490, 200],
        # [490, 190],
        # [490, 180],
        # [490, 170],
        # [490, 160],
        # [490, 150],
        # [490, 140],
        # [490, 130],
        # [490, 120],
        # [490, 110],
        # [490, 100],
        # [490,  90],
        # [490,  80],
        # [490,  70],
        # [490,  60],
        # [490,  50],
        # [490,  40],
        # [490,  30],
        # [490,  20],
        # [490,  10]])  # config #testing
        self.beamstops = np.empty((0, 2))
        self.beamstop_parked = np.empty(0, dtype=np.int)
        self.parking_position_occupied = np.zeros(len(self.parking_positions), dtype=np.int)  # testing

    def add_beamstops(self, parking_nrs):
        if self.parking_position_occupied[parking_nrs].any():
            raise ValueError("cannot put beamstop on occupied parking position")
        self.parking_position_occupied[parking_nrs] = np.arange(self.beamstops.size, self.beamstops.size+len(parking_nrs))+1
        self.beamstop_parked = np.concatenate([self.beamstop_parked, parking_nrs+1])
        self.beamstops = np.concatenate([self.beamstops, self.parking_positions[parking_nrs]])

    def occupy_parking_position(self, parking_nr, beamstop_nr):
        if self.parking_position_occupied[parking_nr]:
            raise ValueError("cannot put beamstop on occupied parking position")
        self.parking_position_occupied[parking_nr] = beamstop_nr+1
        self.beamstop_parked[beamstop_nr] = parking_nr+1

    def free_parking_position(self, beamstop_nr):
        if not self.beamstop_parked[beamstop_nr]:
            return
        parking_nr = self.beamstop_parked[beamstop_nr]-1
        self.beamstop_parked[beamstop_nr] = 0
        self.parking_position_occupied[parking_nr] = 0


class BeamstopMoveTarget:
    def __init__(self, beamstop_manager, beamstop_nr, targetpos):
        self.beamstop_nr = beamstop_nr
        self.target_pos = targetpos
        self.beamstop_manager = beamstop_manager

    def get_target_pos(self):
        return self.target_pos

    def get_beamstop_pos(self):
        return self.beamstop_manager.beamstops[self.beamstop_nr]

    def finish_move(self):
        self.beamstop_manager.beamstops[self.beamstop_nr] = self.get_target_pos()
        self.beamstop_manager.free_parking_position(self.beamstop_nr)

    def update_pos(self, pos):
        pass
        # TODO: draw line, update circle


class BeamstopMoveParking(BeamstopMoveTarget):
    def __init__(self, beamstop_manager, beamstop_nr, parking_nr):
        self.beamstop_manager = beamstop_manager
        self.beamstop_nr = beamstop_nr
        self.parking_nr = parking_nr
        self.target_pos = self.beamstop_manager.parking_positions[parking_nr]

    def finish_move(self):
        self.beamstop_manager.beamstops[self.beamstop_nr] = self.get_target_pos()
        self.beamstop_manager.occupy_parking_position(self.parking_nr, self.beamstop_nr)


# returns combinations of [beamstops, target_positions] and the distances between the two
def calc_beamstop_assignment(beamstops, target_positions, penalties=None):
    if not beamstops.size:
        return np.array([]), np.array([])
    if not target_positions.size:
        return np.array([]), np.array([])

    # calculate distances from all beamstop targets to all beamstops and add penalties for suboptimal beamstops. Penalty list must have length of beamstop list
    distances = calc_vec_len(target_positions - beamstops[:, np.newaxis])
    if penalties is not None:
        penalised_distances = distances + penalties[:, np.newaxis]
    else:
        penalised_distances = distances
    combinations = np.array(scipy.optimize.linear_sum_assignment(penalised_distances))
    return combinations, distances[tuple(combinations)]


# get the length of a vector or list of vectors
def calc_vec_len(vec):
    vec = np.array(vec)
    return np.sqrt((vec*vec).sum(axis=-1))
