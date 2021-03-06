import collisiondetection
import pathfinder

import numpy as np
import scipy.optimize

from PyQt5 import QtGui, QtWidgets
import logging


class BeamstopMover:
    def __init__(self, config, im_view, absorber_hardware, beamstop_manager):
        self.config = config
        self.im_view = im_view
        self.absorber_hardware = absorber_hardware
        self.beamstop_manager = beamstop_manager

        self.lg = logging.getLogger("main.absorberfunctions.beamstopmover")

    def rearrange_all_beamstops(self):
        self.lg.info("calulating beamstop assignment")
        handle_positions = self.im_view.handles.get_handle_positions()

        combos, spacing = self.check_spacing(handle_positions)
        if len(spacing):
            self.lg.warning("your handles are too close to each other. handle(s)1: %s, handle(s)2: %s, distance(s): %s movement was aborted", combos[0], combos[1], spacing)
            return

        required_moves = self.get_required_moves(handle_positions,
                                                 self.beamstop_manager.beamstops,
                                                 self.beamstop_manager.beamstop_parked,
                                                 self.beamstop_manager.parking_position_occupied)
        if not required_moves:
            self.lg.info("nothing to move")
            return

        self.lg.info("sorting moves")
        # sort moves to have consecutive moves close to each other. This sorting might be changed in the next step if required to find a path
        sorted_moves = self.sort_moves_distance(required_moves)

        self.lg.info("calulating paths")
        solved_moves, unsolved_moves = self.calc_expected_collisions(sorted_moves)
        if unsolved_moves:
            if not solved_moves:
                self.lg.warning("no solved moves, %d unsolved move(s), aborting movement", len(unsolved_moves))
                return
            self.lg.info("%d solved move(s), %d unsolved move(s)", len(solved_moves), len(unsolved_moves))
            msg = QtGui.QMessageBox
            answer = msg.question(None,
                                  '',
                                  "Would you like to rearrange the beamstops that have a path?\nNo path could be found \n"
                                  + " and\n".join("from {} to {}".format(move.beamstop_pos, move.target_pos) for move in unsolved_moves),
                                  msg.Yes | msg.No)
            if answer == msg.No:
                self.lg.debug("user aborted movement because of unsolved moves. removing lines")
                for move in solved_moves:
                    move.remove_lines()
                return
        self.move_beamstops(solved_moves)

    def check_spacing(self, handle_positions):
        """checks whether all positions passed in here are more than gripper radius apart. Returns indices of handles too close to each other and the distances within the pairs"""
        if not len(handle_positions):
            return [], []
        distances = calc_vec_len(handle_positions - handle_positions[:, np.newaxis])
        # get all indices where the handles are at most gripper radius apart
        close_handles = np.array(np.where(distances <= self.config.PeakAbsorber.beamstop_spacing))
        # this list contains every distance twice (from a to b and from b to a) and one 0-distance where the element is compared to itself. Remove those.
        close_handles = close_handles[:,close_handles[0] > close_handles[1]]
        return close_handles, distances[tuple(close_handles)]

    def get_required_moves(self, handles, beamstops, beamstop_parked, parking_position_occupied):
        if len(handles) > len(beamstops):
            self.lg.warning("not enough beamstops available")
            return []

        if handles.size:
            self.lg.debug("handles available, calculating assignment to beamstops")

            target_combinations, target_distances = self.calc_beamstop_assignment(beamstops, handles, self.config.PeakAbsorber.beamstop_inactive_cost * beamstop_parked.astype(np.bool_))

            required_moves = [BeamstopMove(self.beamstop_manager, self.im_view, combination[0], handles[combination[1]]) for combination in np.swapaxes(target_combinations, 0, 1)[target_distances > self.config.PeakAbsorber.epsilon]]

            reststops = np.delete(np.arange(beamstops.shape[0]), target_combinations[0])[np.delete(np.logical_not(beamstop_parked), target_combinations[0])]
        else:
            self.lg.debug("no handles available")
            reststops = np.arange(len(beamstops))[np.logical_not(beamstop_parked)]
            required_moves = []

        if reststops.size:
            self.lg.debug("unused beamstops available calculating cleanup")
            free_parking_position_nrs = np.logical_not(parking_position_occupied).nonzero()[0]

            if reststops.size > free_parking_position_nrs.size:
                self.lg.warning("not enough parking space available: %d reststops but only %d parking spots", reststops.size, free_parking_position_nrs.size)
                return []

            rest_combinations, _ = self.calc_beamstop_assignment(beamstops[reststops], self.config.ParkingPositions.parking_positions[free_parking_position_nrs])
            required_moves.extend(BeamstopMove(self.beamstop_manager, self.im_view, reststops[combination[0]], self.config.ParkingPositions.parking_positions[free_parking_position_nrs[combination[1]]]) for combination in np.swapaxes(rest_combinations, 0, 1))
        return required_moves

    @staticmethod
    def calc_beamstop_assignment(beamstops, target_positions, penalties=None):
        """returns combinations of [beamstops, target_positions] and the distances between the two where every pair is chosen so the total distance is as short as possible"""
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

    @staticmethod
    def sort_moves_distance(moves):
        """iteratively sorts the moves passed to it in a way so the first move is the one with the startpoint closest to 0,0
        the second move is the one with the start point closest to the end point of the first move and so on
        this is a simple way to reduce travel distance without a proper solver for transportation problems"""
        # to be able to quickly calculate distances between lists of points we unpack to moves into numpy arrays
        beamstop_positions = [move.beamstop_pos for move in moves]
        target_positions = [move.target_pos for move in moves]
        # to keep track which line originally was in which position the last column is just numbered from 0 to n
        positions = np.swapaxes([beamstop_positions, target_positions, np.swapaxes([np.arange(len(moves)), np.arange(len(moves))], 0, 1)], 0, 1)
        sorted_positions = np.array([[[0, 0], [0, 0], [0, 0]]])
        while len(positions):
            next_closest = np.argmin(calc_vec_len(positions[:, 0]-sorted_positions[-1, 1]))
            sorted_positions = np.append(sorted_positions, [positions[next_closest]], 0)
            positions = np.delete(positions, next_closest, 0)
        # we return the moves in the new order given by the indices in the last column except the first row which was the start point
        return [moves[x] for x in sorted_positions[1:, 2, 0].astype(int)]

    def calc_expected_collisions(self, moves):
        """
        Sorts the moves passed in into one list of unsolvable moves and one list of moves with paths in the order they should be done in. Also adds lines for every solved move

        Simulates the expected constellation of beamstops after every move, then runs collision detection which adds the path if there is one
        Reruns moves for which path finding failed until they either all have a path or none of the moves in the last iteration could find a path
        :moves: the moves to find a path for
        :returns (solved moves: moves with paths in order of execution, unsolved moves: moves for which no path could be found
        """
        progressbar = QtWidgets.QProgressDialog("Calculating Movements...", "Cancel", 0, len(moves))
        progressbar.setModal(True)
        progressbar.setMinimumDuration(50)

        unsolved_moves = moves.copy()
        solved_moves = []
        simulation_beamstops = self.beamstop_manager.beamstops.copy()
        progress = True
        while unsolved_moves and progress:
            progress = False
            for move in unsolved_moves.copy():
                if not self.calc_path(move, simulation_beamstops):
                    continue
                progress = True
                unsolved_moves.remove(move)
                solved_moves.append(move)
                move.add_line()
                simulation_beamstops[move.beamstop_nr] = move.target_pos
                progressbar.setValue(len(solved_moves))
        progressbar.setValue(len(moves))
        return solved_moves, unsolved_moves

    def calc_path(self, move, beamstops):
        """
        adds a path to use to a move if there is one
        :param move: move to add path to
        :param beamstops: beamstops to not collide with
        :returns: bool whether path was found or not
        """
        # calculate beamstop list which excludes the currently driven beamstop and has [x, y, distance_to_current] instead of just [x, y]
        collision_bs_list = np.append(np.delete(beamstops, move.beamstop_nr, 0), calc_vec_len(np.delete(beamstops, move.beamstop_nr, 0) - move.beamstop_pos)[:, np.newaxis], 1)
        try:
            move.path = np.array(collisiondetection.find_path(move.target_pos, move.beamstop_pos, collision_bs_list, self.config.PeakAbsorber.beamstop_spacing, max_multi=30))
            if np.any([move.path[:, 0] < 0, move.path[:, 1] > 0, move.path[:, 0] > self.config.PeakAbsorber.limits[0], move.path[:, 1] > self.config.PeakAbsorber.limits[1]]):
                raise collisiondetection.NoSolutionError("point was outside limits")
        except (collisiondetection.NoSolutionError, ArithmeticError) as error:
            self.lg.debug("using fallback algorithm because: %s", str(error))
            move.path = pathfinder.find_path(move.beamstop_pos, move.target_pos, np.delete(beamstops, move.beamstop_nr, 0), self.config.PeakAbsorber.beamstop_spacing, self.config.PeakAbsorber.limits)
        return move.path is not None

    def move_beamstops(self, required_moves):
        # TODO: find best path
        self.lg.debug("working through list of moves")
        for move in required_moves:
            self.absorber_hardware.move_beamstop(move)
        self.absorber_hardware.go_home()

    def move_randomly(self):
        """ function to randomly place handles and move beamstops to them in an infinite loop to test hardware function"""
        if not len(self.beamstop_manager.beamstops):
            self.lg.warning("no beamstops, aborting")
            return
        while True:
            self.im_view.handles.reset_all_handles()
            for beamstop in self.beamstop_manager.beamstops:
                self.im_view.handles.add_handle(np.random.rand(2)*self.config.PeakAbsorber.limits)
            self.rearrange_all_beamstops()


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

        self.im_view.beamstop_circles.remover = self.remove_beamstop
        self._beamstop_circles = []

    def add_beamstops(self, new_positions):
        parked_beamstops = np.argwhere(calc_vec_len(self.config.ParkingPositions.parking_positions - new_positions[:, np.newaxis]) < self.config.PeakAbsorber.epsilon)
        if self._parking_position_occupied[parked_beamstops[:, 1]].any():
            self.lg.warning("cannot put beamstop on occupied parking position")
            return None
        self._parking_position_occupied[parked_beamstops[:, 1]] = self._beamstops.size + parked_beamstops[:, 0] + 1
        self._beamstop_parked = np.concatenate([self._beamstop_parked, np.zeros(len(new_positions), dtype=np.int)])
        self._beamstop_parked[parked_beamstops[:, 0] + len(self._beamstops)] = parked_beamstops[:, 1] + 1
        self._beamstops = np.concatenate([self._beamstops, new_positions])

        for position in new_positions:
            self._beamstop_circles.append(self.im_view.beamstop_circles.add_circle(position))
        return len(new_positions)

    def remove_beamstop(self, beamstop_circle):
        """removes a beamstop from the record.
        This also decrements all indices pointing to elements that were at a higher position in the list that now "fall down" into the space that's freed."""
        beamstop_nr = self._beamstop_circles.index(beamstop_circle)
        parking_nr = self._beamstop_parked[beamstop_nr] - 1
        self._beamstop_circles.pop(beamstop_nr)
        self._parking_position_occupied[parking_nr] = 0
        # decrement all indices higher than the indices we had by one
        self._parking_position_occupied[self._parking_position_occupied > beamstop_nr] -= 1
        self._beamstop_parked = np.delete(self._beamstop_parked, beamstop_nr, axis=0)
        self._beamstops = np.delete(self._beamstops, beamstop_nr, axis=0)

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
        # first free the parking position if we were on one (don't run occupy first or you'll free the one sou just occupied)
        self._free_parking_position(beamstop_nr)
        # then check if our new position is on a parking position and if so occupy that one
        new_parking_spot = np.argwhere(calc_vec_len(self.config.ParkingPositions.parking_positions - pos) < self.config.PeakAbsorber.epsilon)
        if new_parking_spot.size:
            self._occupy_parking_position(new_parking_spot, beamstop_nr)
        self.beamstops[beamstop_nr] = pos

    @property
    def parking_position_occupied(self):
        return self._parking_position_occupied

    @property
    def beamstop_parked(self):
        return self._beamstop_parked

    @property
    def beamstops(self):
        return self._beamstops

    @property
    def beamstop_circles(self):
        return self._beamstop_circles


class BeamstopMove:
    def __init__(self, beamstop_manager, im_view, beamstop_nr, target_pos):
        self.beamstop_nr = beamstop_nr
        self.target_pos = target_pos
        self.beamstop_manager = beamstop_manager
        self.im_view = im_view

        self.beamstop_pos = self.beamstop_manager.beamstops[self.beamstop_nr]
        self.path = None
        self.trajectory_line = None

    def add_line(self):
        self.trajectory_line = self.im_view.trajectory_lines.add_polyline(np.concatenate([[self.beamstop_pos], self.path], axis=0))

    def remove_lines(self):
        self.im_view.trajectory_lines.remove_item(self.trajectory_line)
        self.trajectory_line = None

    def finish_move(self):
        self.remove_lines()

    def __del__(self):
        if self.trajectory_line is not None:
            self.remove_lines()


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
