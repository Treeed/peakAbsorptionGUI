import tango
import absorberfunctions
import numpy as np
from PyQt5.QtCore import QEventLoop, QTimer, pyqtSignal, QObject


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
        self.gripper_time_ms = 2000  # config

        self._gripper = tango.DeviceProxy(_tango_server + _gripper_path)
        self._motor_x = tango.DeviceProxy(_tango_server + _motor_x_path)
        self._motor_y = tango.DeviceProxy(_tango_server + _motor_y_path)

        self.updater = MovementUpdater(self)

    def move_beamstop(self, move):
        self.move_to(move.get_beamstop_pos(), "travel")
        self.engage_gripper()
        self.updater.set_current_move(move)
        self.move_to(move.get_target_pos(), "beamstop")
        self.updater.set_current_move(None)
        self.disengage_gripper()

        move.finish_move()

    def engage_gripper(self):
        self._gripper.value = 1
        wait(self.gripper_time_ms)

    def disengage_gripper(self):
        self._gripper.value = 0
        wait(self.gripper_time_ms)

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
        self.updater.set_moving()
        wait(100000, self.updater.moveFinished)  # config

    def get_hardware_status(self):
        pos = self._motor_x.position, self._motor_y.position, self._gripper.value
        state = self._motor_x.state(), self._motor_y.state(), self._gripper.state()
        return pos, state


class MovementUpdater(QObject):
    moveFinished = pyqtSignal()
    posChanged = pyqtSignal(tuple)

    def __init__(self, absorber_hardware):
        super().__init__()
        self.absorber_hardware = absorber_hardware
        self.idle_polling_rate = 5  # config
        self.moving_polling_rate = 60  # config
        self.moving = False

        self.current_move = None
        self.last_status = None

        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(1000/self.idle_polling_rate)

    def update(self):
        status = self.absorber_hardware.get_hardware_status()
        if self.moving and status[1][0] != tango.DevState.MOVING and status[1][1] != tango.DevState.MOVING:
            self.moveFinished.emit()
            self.set_idle()
        if self.current_move is not None:
            self.current_move.update_pos((status[0][0], status[0][1]))
        if self.last_status != status:
            self.posChanged.emit((status[0][0], status[0][1]))
            self.last_status = status

    def set_current_move(self, move):
        self.update()
        self.current_move = move

    def set_idle(self):
        self.moving = False
        self.timer.setInterval(self.idle_polling_rate)

    def set_moving(self):
        self.moving = True
        self.timer.setInterval(self.moving_polling_rate)

    def quit(self):
        self.update()
        self.timer.stop()


def wait(timeout, signal = None):
    loop = QEventLoop()
    QTimer.singleShot(timeout, loop.quit)
    if signal is not None:
        signal.connect(loop.quit)
    loop.exec()


def check_in_box(pos, box_origin, box_size):
    return box_origin[0] < pos[0] < box_origin[0] + box_size[0] and box_origin[1] < pos[1] < box_origin[1] + box_size[1]
