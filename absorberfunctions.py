import pyqtgraph as pg
import numpy as np
import scipy.optimize
import pyqtgraphutils

class BeamstopManager:
    def __init__(self, im_view, absorber_hardware):
        self.im_view = im_view
        self.absorber_hardware = absorber_hardware

        self.handles = [] # movable handles to specify the targets where the beamstops will be moved
        self.beamstop_circles = []

    def reset_all(self):
        for beamstop in self.handles:
            self.im_view.removeItem(beamstop)
        #TODO: reset the physical beamstops to their original positions

    def add_handle(self):
        self.handles.append(pg.CircleROI([100, 100], [50, 50], pen=(9, 15)))
        self.im_view.addItem(self.handles[-1])

#testing
    def add_teststops(self):
        teststops = self.absorber_hardware.parking_positions
        self.absorber_hardware.add_beamstops(teststops)
        for beamstop in teststops:
            self.beamstop_circles.append(self.circle_in_machine_coord(beamstop, color ='r'))
            self.im_view.addItem(self.beamstop_circles[-1])


    def rearrange_all_beamstops(self):
        if len(self.handles) > len(self.absorber_hardware.beamstops):
            print("not enough beamstops available") #error
            return
        handle_positions = self.get_handles_machine_coords()
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

    def get_handles_machine_coords(self):
        return np.array([self.img_to_machine_coord(np.array(handle.pos())+np.array(handle.size())/2) for handle in self.handles])

    def move_beamstops(self, required_moves):
        #TODO: find best path
        for move in required_moves:
            trajectory = pyqtgraphutils.LineSegmentItem(self.machine_to_img_coord(self.absorber_hardware.beamstops[move[0]]), self.machine_to_img_coord(move[1]))
            self.im_view.addItem(trajectory)
            self.absorber_hardware.move_beamstop(move[0], move[1])
            self.im_view.removeItem(trajectory)
            self.beamstop_circles[move[0]].setCenter(self.machine_to_img_coord(move[1]))


    def img_to_machine_coord(self, point):
        return np.array(point)*self.absorber_hardware.pixel_size+self.absorber_hardware.detector_origin

    def machine_to_img_coord(self, point):
        return (np.array(point)-self.absorber_hardware.detector_origin)/self.absorber_hardware.pixel_size

    def img_to_machine_scale(self, point):
        return np.array(point) * self.absorber_hardware.pixel_size

    def machine_to_img_scale(self, point):
        return np.array(point) / self.absorber_hardware.pixel_size

    def circle_in_machine_coord(self, pos, radius = None, color = 'w'):
        if radius is None:
            radius = self.absorber_hardware.beamstop_radius
        return pyqtgraphutils.CircleItem(self.machine_to_img_coord(pos), self.machine_to_img_scale(radius)[0], color)


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