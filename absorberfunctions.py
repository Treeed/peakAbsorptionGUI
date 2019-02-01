import collisiondetection
# import pathfinder

import numpy as np
import scipy.optimize

import pyqtgraphutils
import logging


class BeamstopMover:
    def __init__(self, config, im_view, absorber_hardware, beamstop_manager):
        self.config = config
        self.im_view = im_view
        self.absorber_hardware = absorber_hardware
        self.beamstop_manager = beamstop_manager

        self.lg = logging.getLogger("main.absorberfunctions.beamstopmover")

        self.absorber_hardware.updater.posChanged.connect(self.im_view.set_crosshair_pos)
        self.absorber_hardware.updater.gripperChanged.connect(self.im_view.set_crosshair_color)

    def rearrange_all_beamstops(self):
        self.lg.info("calulating beamstop assignment")
        if len(self.im_view.items["handles"]) > len(self.beamstop_manager.beamstops):
            self.lg.warning("not enough beamstops available")
            return

        handle_positions = self.im_view.get_handles_machine_coords()
        if handle_positions.size > 0:
            self.lg.debug("handles available, calculating assignment to beamstops")

            target_combinations, target_distances = self.calc_beamstop_assignment(self.beamstop_manager.beamstops, handle_positions, self.config.PeakAbsorber.beamstop_inactive_cost * self.beamstop_manager.beamstop_parked.astype(np.bool_))

            required_moves = [BeamstopMove(self.beamstop_manager, self.im_view, combination[0], handle_positions[combination[1]]) for combination in np.swapaxes(target_combinations, 0, 1)[target_distances > self.config.PeakAbsorber.epsilon]]

            reststops = np.delete(np.arange(self.beamstop_manager.beamstops.shape[0]), target_combinations[0])[np.delete(np.logical_not(self.beamstop_manager.beamstop_parked), target_combinations[0])]
        else:
            self.lg.debug("no handles available")
            reststops = np.arange(len(self.beamstop_manager.beamstops))[np.logical_not(self.beamstop_manager.beamstop_parked)]
            required_moves = []

        if reststops.size > 0:
            self.lg.debug("unused beamstops available calculating cleanup")
            free_parking_position_nrs = np.logical_not(self.beamstop_manager.parking_position_occupied).nonzero()[0]

            if reststops.size > free_parking_position_nrs.size:
                self.lg.warning("not enough parking space available: %d reststops but only %d parking spots", reststops.size, free_parking_position_nrs.size)
                return

            rest_combinations, _ = self.calc_beamstop_assignment(self.beamstop_manager.beamstops[reststops], self.config.ParkingPositions.parking_positions[free_parking_position_nrs])
            required_moves.extend(BeamstopMove(self.beamstop_manager, self.im_view, reststops[combination[0]], self.config.ParkingPositions.parking_positions[free_parking_position_nrs[combination[1]]]) for combination in np.swapaxes(rest_combinations, 0, 1))

        self.calc_expected_collisions(required_moves)
        self.move_beamstops(required_moves)

    # returns combinations of [beamstops, target_positions] and the distances between the two
    @staticmethod
    def calc_beamstop_assignment(beamstops, target_positions, penalties=None):
        if not beamstops.size or not target_positions.size:
            return np.array([]), np.array([])

        # calculate distances from all beamstop targets to all beamstops and add penalties for suboptimal beamstops. Penalty list must have length of beamstop list
        distances = calc_vec_len(target_positions - beamstops[:, np.newaxis])
        if penalties is not None:
            penalised_distances = distances + penalties[:, np.newaxis]
        else:
            penalised_distances = distances
        combinations = np.array(scipy.optimize.linear_sum_assignment(penalised_distances))
        return combinations, distances[tuple(combinations)]

    def calc_expected_collisions(self, moves):
        """
        Modifies the moves in the list to include paths which avoid collisions if necessary

        Simulates the expected constellation of beamstops after every move, then runs collision detection
        and adds the calculated intermediate stops to the moves that would collide with a beamstop otherwise.
        """
        simulation_beamstops = self.beamstop_manager.beamstops.copy()
        collision_detector = collisiondetection.CollisionDetection()
        for move in moves:
            # move.path = pathfinder.find_path(move.beamstop_pos, move.target_pos, np.delete(simulation_beamstops, move.beamstop_nr, 0), 11.5, [500, 500])
            # calculate beamstop list which excludes the currently driven beamstop and has [x, y, distance_to_current] instead of just [x, y]
            collision_bs_list = np.append(np.delete(simulation_beamstops, move.beamstop_nr, 0), calc_vec_len(np.delete(simulation_beamstops, move.beamstop_nr, 0)-move.beamstop_pos)[:, np.newaxis], 1)
            move.path = collision_detector.find_path(move.target_pos, move.beamstop_pos, collision_bs_list, self.config.PeakAbsorber.gripper_radius + self.config.PeakAbsorber.beamstop_radius, max_multi=30)
            move.add_lines()
            simulation_beamstops[move.beamstop_nr] = move.target_pos

    def move_beamstops(self, required_moves):
        # TODO: find best path
        self.lg.debug("working through list of moves")
        for move in required_moves:
            self.absorber_hardware.move_beamstop(move)
        self.absorber_hardware.go_home()


class BeamstopManager:
    def __init__(self, config, im_view):
        self.config = config
        self.im_view = im_view
        self.lg = logging.getLogger("main.absorberfunctions.beamstopmanager")

        # these three lists must only ever be modified together.
        # When a beamstop moves the position has to be changed in "beamstops";
        #   if it leaves a parking position the parking position has to be freed in "parking_position_occupied" and the "beamstop_parked" value at the index of the beamstop has to be set to zero;
        #   if it occupies a parking position the "parking_position_occupied" value has to be set to the index of the beamstop+1 and the "beamstop_parked" value has to be set to the index of the parking position+1
        # list of all beamstops where each element is a position as [x, y]
        self._beamstops = np.empty((0, 2))
        # list of all beamstops where each element is the index+1 of the parking spot that the beamstop uses or 0 if it doesn't use a parking spot
        self._beamstop_parked = np.empty(0, dtype=np.int)
        # list of all parking position where each element is the index+1 of the beamspot that currently uses it or 0 if no beamstop uses it
        self._parking_position_occupied = np.zeros(len(self.config.ParkingPositions.parking_positions), dtype=np.int)

    def add_beamstops(self, new_positions):
        parked_beamstops = np.argwhere(np.isclose(calc_vec_len(self.config.ParkingPositions.parking_positions - new_positions[:, np.newaxis]), 0))
        if self._parking_position_occupied[parked_beamstops[:, 1]].any():
            self.lg.warning("cannot put beamstop on occupied parking position")
            return None
        self._parking_position_occupied[parked_beamstops[:, 1]] = self._beamstops.size + parked_beamstops[:, 0] + 1
        self._beamstop_parked = np.concatenate([self._beamstop_parked, np.zeros(len(new_positions), dtype=np.int)])
        self._beamstop_parked[parked_beamstops[:, 0] + len(self._beamstops)] = parked_beamstops[:, 1] + 1
        self._beamstops = np.concatenate([self._beamstops, new_positions])
        self.im_view.add_beamstop_circles(new_positions)
        return len(new_positions)

    def _occupy_parking_position(self, parking_nr, beamstop_nr):
        self.lg.debug("occupying parking pos %d with beamstop %d", parking_nr, beamstop_nr)
        if self._parking_position_occupied[parking_nr]:
            self.lg.warning("cannot put beamstop on occupied parking position")
        self._parking_position_occupied[parking_nr] = beamstop_nr + 1
        self._beamstop_parked[beamstop_nr] = parking_nr + 1

    def _free_parking_position(self, beamstop_nr):
        if not self._beamstop_parked[beamstop_nr]:
            self.lg.debug("beamstop %d is not parked", beamstop_nr)
            return
        parking_nr = self._beamstop_parked[beamstop_nr] - 1
        self.lg.debug("freeing parking position %d from beamstop %d", parking_nr, beamstop_nr)
        self._beamstop_parked[beamstop_nr] = 0
        self._parking_position_occupied[parking_nr] = 0

    def move(self, beamstop_nr, pos):
        new_parking_spot = np.argwhere(np.isclose(calc_vec_len(self.config.ParkingPositions.parking_positions - pos), 0))
        if new_parking_spot.size:
            self._occupy_parking_position(new_parking_spot, beamstop_nr)
        self.beamstops[beamstop_nr] = pos
        self._free_parking_position(beamstop_nr)

    @property
    def parking_position_occupied(self):
        return self._parking_position_occupied

    @property
    def beamstop_parked(self):
        return self._beamstop_parked

    @property
    def beamstops(self):
        return self._beamstops


class BeamstopMove:
    def __init__(self, beamstop_manager, im_view, beamstop_nr, target_pos):
        self.beamstop_nr = beamstop_nr
        self.target_pos = target_pos
        self.beamstop_manager = beamstop_manager
        self.im_view = im_view

        self.beamstop_pos = self.beamstop_manager.beamstops[self.beamstop_nr]
        self.path = [target_pos]
        self.trajectory_lines = None

    def add_lines(self):
        # this should be done via a function in ImageDrawer but I haven't figured out how to manage the lines yet
        complete_path = np.concatenate([[self.beamstop_pos], self.path], axis=0)
        self.trajectory_lines = [pyqtgraphutils.LineSegmentItem(self.im_view.machine_to_img_coord(complete_path[segment]), self.im_view.machine_to_img_coord(complete_path[segment + 1])) for segment in range(len(complete_path) - 1)]
        for line in self.trajectory_lines:
            self.im_view.im_view.addItem(line)

    def remove_lines(self):
        for line in self.trajectory_lines:
            self.im_view.im_view.removeItem(line)

    def finish_move(self):
        self.beamstop_manager.move(self.beamstop_nr, self.target_pos)
        self.remove_lines()

    def update_pos(self, pos):
        self.im_view.move_circle_in_machine_coord("beamstop_circles", self.beamstop_nr, pos)


class ConfigError(Exception):
    """Exception raised if a config value isn't within the expected range"""
    def __init__(self, value, message):
        """
        init
        :param value: name of the value that didn't meet expectations
        :param message: error message
        """
        self.value = value
        self.message = message


# get the length of a vector or list of vectors
def calc_vec_len(vec):
    vec = np.array(vec)
    return np.sqrt((vec*vec).sum(axis=-1))
