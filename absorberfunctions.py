import numpy as np
import scipy.optimize

import pyqtgraphutils


class BeamstopMover:
    def __init__(self, config, im_view, absorber_hardware, beamstop_manager):
        self.config = config
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

            target_combinations, target_distances = calc_beamstop_assignment(self.beamstop_manager.beamstops, handle_positions, self.config.PeakAbsorber.beamstop_inactive_cost * self.beamstop_manager.beamstop_parked.astype(np.bool_))

            required_moves = [BeamstopMoveTarget(self.beamstop_manager, self.im_view, combination[0], handle_positions[combination[1]]) for combination in np.swapaxes(target_combinations, 0, 1)[target_distances > self.config.PeakAbsorber.epsilon]]

            reststops = np.delete(np.arange(self.beamstop_manager.beamstops.shape[0]), target_combinations[0])[np.delete(np.logical_not(self.beamstop_manager.beamstop_parked), target_combinations[0])]
        else:
            reststops = np.arange(len(self.beamstop_manager.beamstops))[np.logical_not(self.beamstop_manager.beamstop_parked)]
            required_moves = []

        if reststops.size > 0:
            free_parking_position_nrs = np.logical_not(self.beamstop_manager.parking_position_occupied).nonzero()[0]

            if reststops.size > free_parking_position_nrs.size:
                print("not enough parking space available")  # error
                return

            rest_combinations, _ = calc_beamstop_assignment(self.beamstop_manager.beamstops[reststops], self.config.ParkingPositions.parking_positions[free_parking_position_nrs])
            required_moves.extend(BeamstopMoveParking(self.beamstop_manager, self.im_view, reststops[combination[0]], free_parking_position_nrs[combination[1]]) for combination in np.swapaxes(rest_combinations, 0, 1))

        self.move_beamstops(required_moves)

    def move_beamstops(self, required_moves):
        # TODO: find best path
        for move in required_moves:
            self.absorber_hardware.move_beamstop(move)
        self.absorber_hardware.go_home()


class BeamstopManager:
    def __init__(self, config):
        self.config = config
        self.beamstops = np.empty((0, 2))
        self.beamstop_parked = np.empty(0, dtype=np.int)
        self.parking_position_occupied = np.zeros(len(self.config.ParkingPositions.parking_positions), dtype=np.int)

    def add_beamstops(self, parking_nrs):
        if self.parking_position_occupied[parking_nrs].any():
            raise ValueError("cannot put beamstop on occupied parking position")
        self.parking_position_occupied[parking_nrs] = np.arange(self.beamstops.size, self.beamstops.size+len(parking_nrs))+1
        self.beamstop_parked = np.concatenate([self.beamstop_parked, parking_nrs+1])
        self.beamstops = np.concatenate([self.beamstops, self.config.ParkingPositions.parking_positions[parking_nrs]])

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
    def __init__(self, beamstop_manager, im_view, beamstop_nr, targetpos):
        self.beamstop_nr = beamstop_nr
        self.target_pos = targetpos
        self.beamstop_manager = beamstop_manager
        self.im_view = im_view

        self.trajectory_line = None
        self.add_line()

    def add_line(self):
        # this should be done via a function in ImageDrawer but I haven't figured out how to manage the lines yet
        self.trajectory_line = pyqtgraphutils.LineSegmentItem(self.im_view.machine_to_img_coord(self.target_pos), self.im_view.machine_to_img_coord(self.get_beamstop_pos()))
        self.im_view.im_view.addItem(self.trajectory_line)

    def remove_line(self):
        self.im_view.im_view.removeItem(self.trajectory_line)

    def get_target_pos(self):
        return self.target_pos

    def get_beamstop_pos(self):
        return self.beamstop_manager.beamstops[self.beamstop_nr]

    def finish_move(self):
        self.beamstop_manager.beamstops[self.beamstop_nr] = self.get_target_pos()
        self.beamstop_manager.free_parking_position(self.beamstop_nr)
        self.remove_line()

    def update_pos(self, pos):
        self.im_view.move_circle_in_machine_coord("beamstop_circles", self.beamstop_nr, pos)
        self.trajectory_line.pos()


class BeamstopMoveParking(BeamstopMoveTarget):
    def __init__(self, beamstop_manager, im_view, beamstop_nr, parking_nr):
        self.beamstop_manager = beamstop_manager
        self.beamstop_nr = beamstop_nr
        self.parking_nr = parking_nr
        self.target_pos = self.beamstop_manager.config.ParkingPositions.parking_positions[parking_nr]
        self.im_view = im_view

        self.add_line()

    def finish_move(self):
        self.beamstop_manager.beamstops[self.beamstop_nr] = self.get_target_pos()
        self.beamstop_manager.occupy_parking_position(self.parking_nr, self.beamstop_nr)
        self.remove_line()


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
