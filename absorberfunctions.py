import numpy as np
import scipy.optimize

import absorbergui

class BeamstopManager:
    def __init__(self, im_view, absorber_hardware):
        self.im_view = im_view
        self.absorber_hardware = absorber_hardware

    def rearrange_all_beamstops(self):
        if len(self.im_view.items["handles"]) > len(self.absorber_hardware.beamstops):
            print("not enough beamstops available") #error
            return
        if len(self.im_view.items["handles"]) == 0:
            print("no handles")
            return

        handle_positions = self.im_view.get_handles_machine_coords()
        #TODO: get machine coordinates
        #TODO: check behaviour without elements
        beamstop_inactive_cost = 500 #how much virtual distance (mm) is added to penalise moving extra beamstops into the active area #config
        target_combinations, target_distances = calc_beamstop_assignment(self.absorber_hardware.beamstops, handle_positions, beamstop_inactive_cost * np.logical_not(self.absorber_hardware.beamstop_active))

        epsilon = 0.0001  # beamstops that are offset from their target below this value are considered floating point errors and will not be moved #config
        required_moves = [(combination[0], handle_positions[combination[1]]) for combination in np.swapaxes(target_combinations, 0, 1)[target_distances > epsilon]]

        reststops = np.delete(range(len(self.absorber_hardware.beamstops)), target_combinations[0])[np.delete(self.absorber_hardware.beamstop_active, target_combinations[0])]
        free_parking_positions = self.absorber_hardware.parking_positions[np.logical_not(self.absorber_hardware.parking_position_occupied)]

        if reststops.size > free_parking_positions.size:
            print("not enough parking space available") #error
            return
        if reststops.size > 0:
            rest_combinations, _ = calc_beamstop_assignment(self.absorber_hardware.beamstops[reststops], free_parking_positions)
            required_moves.extend([reststops[rest_combinations[0]], free_parking_positions[rest_combinations[1]]])

        self.move_beamstops(required_moves)



    def move_beamstops(self, required_moves):
        #TODO: find best path
        for move in required_moves:
            with absorbergui.DrawTempLineInMachCoord(self.im_view,self.absorber_hardware.beamstops[move[0]], move[1]):
                self.absorber_hardware.move_beamstop(move[0], move[1])
                self.im_view.move_circle_in_machine_coord(move[0], move[1])
        #TODO: home afterwards




#returns combinations of [beamstops, target_positions] and the distances between the two
def calc_beamstop_assignment(beamstops, target_positions, penalties = 0):
    if not beamstops.size:
        return np.array([]), np.array([])
    if not target_positions.size:
        return np.array([]), np.array([])

    #calculate distances from all beamstop targets to all beamstops and add penalties for suboptimal beamstops. Penalty list must have length of beamstop list
    distances = calc_vec_len(target_positions - beamstops[:,np.newaxis])
    if penalties is not None:
        penalised_distances =  distances + penalties[:,np.newaxis]
    else:
        penalised_distances = distances
    combinations = np.array(scipy.optimize.linear_sum_assignment(penalised_distances))
    return combinations, distances[tuple(combinations)]

# get the length of a vector or list of vectors
def calc_vec_len(vec):
    vec = np.array(vec)
    return np.sqrt((vec*vec).sum(axis=-1))