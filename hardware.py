import time
import tango
import absorberfunctions
import numpy as np

class PeakAbsorberHardware:
    def __init__(self):
        #configurables
        _motor_x_path = 'p02/motor/elab.03' # config # testing
        _motor_y_path = 'p02/motor/elab.04' # config # testing
        _gripper_path = 'p02/register/elab.out08' # config
        self._slewrates = {
            "travel" : 100000,
            "beamstop" : 10000,
            "homing" : 1000,
        } # config
        self.parking_positions  = np.array([[ 10,  10],
       [ 10,  20],
       [ 10,  30],
       [ 10,  40],
       [ 10,  50],
       [ 10,  60],
       [ 10,  70],
       [ 10,  80],
       [ 10,  90],
       [ 10, 100],
       [ 10, 110],
       [ 10, 120],
       [ 10, 130],
       [ 10, 140],
       [ 10, 150],
       [ 10, 160],
       [ 10, 170],
       [ 10, 180],
       [ 10, 190],
       [ 10, 200],
       [ 10, 210],
       [ 10, 220],
       [ 10, 230],
       [ 10, 240],
       [ 10, 250],
       [ 10, 260],
       [ 10, 270],
       [ 10, 280],
       [ 10, 290],
       [ 10, 300],
       [ 10, 310],
       [ 10, 320],
       [ 10, 330],
       [ 10, 340],
       [ 10, 350],
       [ 10, 360],
       [ 10, 370],
       [ 10, 380],
       [ 10, 390],
       [ 20, 390],
       [ 30, 390],
       [ 40, 390],
       [ 50, 390],
       [ 60, 390],
       [ 70, 390],
       [ 80, 390],
       [ 90, 390],
       [100, 390],
       [110, 390],
       [120, 390],
       [130, 390],
       [140, 390],
       [150, 390],
       [160, 390],
       [170, 390],
       [180, 390],
       [190, 390],
       [200, 390],
       [210, 390],
       [220, 390],
       [230, 390],
       [240, 390],
       [250, 390],
       [260, 390],
       [270, 390],
       [280, 390],
       [290, 390],
       [300, 390],
       [310, 390],
       [320, 390],
       [330, 390],
       [340, 390],
       [350, 390],
       [360, 390],
       [370, 390],
       [380, 390],
       [390, 390],
       [400, 390],
       [410, 390],
       [420, 390],
       [430, 390],
       [440, 390],
       [450, 390],
       [460, 390],
       [470, 390],
       [480, 390],
       [490, 390],
       [490, 380],
       [490, 370],
       [490, 360],
       [490, 350],
       [490, 340],
       [490, 330],
       [490, 320],
       [490, 310],
       [490, 300],
       [490, 290],
       [490, 280],
       [490, 270],
       [490, 260],
       [490, 250],
       [490, 240],
       [490, 230],
       [490, 220],
       [490, 210],
       [490, 200],
       [490, 190],
       [490, 180],
       [490, 170],
       [490, 160],
       [490, 150],
       [490, 140],
       [490, 130],
       [490, 120],
       [490, 110],
       [490, 100],
       [490,  90],
       [490,  80],
       [490,  70],
       [490,  60],
       [490,  50],
       [490,  40],
       [490,  30],
       [490,  20],
       [490,  10]]) #config #testing
        self.limits = np.array([500, 400]) #limits of the drive mechanism #config
        self.active_area = np.array([200, 200]) #size of the active area of the detector. #config
        self.detector_origin = np.array([150,100]) #position of the lower left corner of the detector relative to the minimum position of the drive mechanism #config
        self.pixel_size = np.array([0.09765625, 0.09765625]) #size of one pixel in x and y. #config
        self.beamstop_radius = 1.5 #config


        self._gripper = tango.DeviceProxy(_gripper_path)
        self._motor_x = tango.DeviceProxy(_motor_x_path)
        self._motor_y = tango.DeviceProxy(_motor_y_path)

        self.beamstops = np.empty((0,2))
        self.beamstop_active = np.empty(0, dtype=np.bool_)
        self.parking_position_occupied = np.ones(len(self.parking_positions), dtype=np.bool_) #testing

    def add_beamstops(self, positions, active = None):
        #TODO: check for collisions
        if active is None:
            active = np.zeros(len(positions), dtype=np.bool_)
        self.beamstops = np.concatenate([self.beamstops, positions])
        self.beamstop_active = np.concatenate([self.beamstop_active, active])

    def move_beamstop(self, beamstop, target):
        self.move_to(self.beamstops[beamstop], "travel")
        self.engage_gripper()
        self.move_to(target, "beamstop")
        self.disengage_gripper()

        self.beamstop_active[beamstop] = check_in_box(target, self.detector_origin, self.active_area)
        self.beamstops[beamstop] = target
        #TODO: check whether it starts/stops occupying a parking position

    def engage_gripper(self):
        pass

    def disengage_gripper(self):
        pass

    def move_to(self, pos, slewrate = "beamstop"):
        #TODO: handle errors
        distance = [self._motor_x.position - pos[0], self._motor_y.position - pos[1]]
        travel_distance = absorberfunctions.calc_vec_len([distance[0], distance[1]])
        # calculate slewrates at which the motors will reach their target values simultaneously and the total grabber speed matches the set slewrate
        self._motor_x.slewrate = abs(distance[0]) * self._slewrates[slewrate] / travel_distance
        self._motor_y.slewrate = abs(distance[1]) * self._slewrates[slewrate] / travel_distance
        self._motor_x.position = pos[0]
        self._motor_y.position = pos[1]
        wait_move(self._motor_x)
        wait_move(self._motor_y)

def wait_move(motor):
    while motor.state() == tango.DevState.MOVING:
        time.sleep(0.01)

def check_in_box(pos, box_origin, box_size):
    return box_origin[0] < pos[0] < box_origin[0] + box_size[0] and box_origin[1] < pos[1] < box_origin[1] + box_size[1]