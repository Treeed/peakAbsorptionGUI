import time
import tango
import absorberfunctions
import numpy as np
from PyQt5.QtGui import QApplication


class PeakAbsorberHardware:
    def __init__(self):
        # configurables
        _tango_server = 'haspp02oh1:10000/'  # config
        _motor_x_path = 'p02/motor/elab.03'  # config # testing
        _motor_y_path = 'p02/motor/elab.04'  # config # testing
        _gripper_path = 'p02/register/elab.out08'  # config
        self._slewrates = {
            "travel": 100000,
            "beamstop": 100000,
            "homing": 1000,
        }  # config

        self.limits = np.array([500, 400])  # limits of the drive mechanism #config
        self.active_area = np.array([200, 200])  # size of the active area of the detector. #config
        self.detector_origin = np.array([150, 100])  # position of the lower left corner of the detector relative to the minimum position of the drive mechanism #config
        self.pixel_size = np.array([0.09765625, 0.09765625])  # size of one pixel in x and y. #config
        self.beamstop_radius = 1.5  # config

        self._gripper = tango.DeviceProxy(_tango_server + _gripper_path)
        self._motor_x = tango.DeviceProxy(_tango_server + _motor_x_path)
        self._motor_y = tango.DeviceProxy(_tango_server + _motor_y_path)

    def move_beamstop(self, move, updater):
        self.move_to(move.get_beamstop_pos(), "travel")
        self.engage_gripper()
        updater.set_current_move(move)
        self.move_to(move.get_target_pos(), "beamstop")
        updater.set_current_move(None)
        self.disengage_gripper()

        move.finish_move()

    def engage_gripper(self):
        self._gripper.value = 1
        time.sleep(2)

    def disengage_gripper(self):
        self._gripper.value = 0
        time.sleep(2)

    def move_to(self, pos, slewrate="beamstop"):
        # TODO: handle errors
        distance = [self._motor_x.position - pos[0], self._motor_y.position - pos[1]]
        travel_distance = absorberfunctions.calc_vec_len([distance[0], distance[1]])
        epsilon = 0.001  # config
        if travel_distance < epsilon:
            return
        # calculate slewrates at which the motors will reach their target values simultaneously and the total grabber speed matches the set slewrate
        self._motor_x.slewrate = abs(distance[0]) * self._slewrates[slewrate] / travel_distance
        self._motor_y.slewrate = abs(distance[1]) * self._slewrates[slewrate] / travel_distance
        self._motor_x.position = pos[0]
        self._motor_y.position = pos[1]
        wait_move(self._motor_x)
        wait_move(self._motor_y)

    def get_hardware_status(self):
        pos = self._motor_x.position, self._motor_y.position, self._gripper.value
        state = self._motor_x.state(), self._motor_y.state(), self._gripper.state()
        return pos, state


def wait_move(motor):
    while motor.state() == tango.DevState.MOVING:
        time.sleep(0.01)  # config
        QApplication.processEvents()


def check_in_box(pos, box_origin, box_size):
    return box_origin[0] < pos[0] < box_origin[0] + box_size[0] and box_origin[1] < pos[1] < box_origin[1] + box_size[1]
