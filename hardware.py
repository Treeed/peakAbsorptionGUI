import tango
import absorberfunctions
import numpy as np
import logging
from PyQt5.QtCore import QEventLoop, QTimer, pyqtSignal, QObject


class PeakAbsorberHardware:
    def __init__(self, config):
        self.config = config

        self._gripper = tango.DeviceProxy(self.config.PeakAbsorber.tango_server + self.config.PeakAbsorber.gripper_path)
        self._motor_x = tango.DeviceProxy(self.config.PeakAbsorber.tango_server + self.config.PeakAbsorber.motor_x_path)
        self._motor_y = tango.DeviceProxy(self.config.PeakAbsorber.tango_server + self.config.PeakAbsorber.motor_y_path)

        self.updater = MovementUpdater(config, self)
        self.lg = logging.getLogger("main.hardware.hardware")

    def move_beamstop(self, move):
        self.lg.info("moving beamstop %d to %s", move.beamstop_nr, str(move.get_target_pos()))
        self.move_to(move.get_beamstop_pos(), "travel")
        self.move_gripper(1)
        self.updater.set_current_move(move)
        self.move_to(move.get_target_pos(), "beamstop")
        self.updater.set_current_move(None)
        self.move_gripper(0)

        move.finish_move()

    def move_gripper(self, pos):
        self.lg.debug("moving gripper to %s", str(pos))
        self._gripper.value = pos
        self.updater.set_gripper_moving()
        self.wait(self.config.PeakAbsorber.timeout_ms, self.updater.gripperFinished)

    def move_to(self, pos, slewrate="beamstop"):
        self.lg.debug("moving to %s with %s speed", str(pos), slewrate)
        # TODO: handle errors
        distance = [self._motor_x.position - pos[0], self._motor_y.position - pos[1]]
        travel_distance = absorberfunctions.calc_vec_len([distance[0], distance[1]])
        if travel_distance < self.config.PeakAbsorber.epsilon:
            return
        # calculate slewrates at which the motors will reach their target values simultaneously and the total grabber speed matches the set slewrate
        self._motor_x.slewrate = abs(distance[0]) * self.config.PeakAbsorber.slewrates[slewrate] / travel_distance
        self._motor_y.slewrate = abs(distance[1]) * self.config.PeakAbsorber.slewrates[slewrate] / travel_distance
        self._motor_x.position = pos[0]
        self._motor_y.position = pos[1]
        self.updater.set_motor_moving()
        self.wait(self.config.PeakAbsorber.timeout_ms, self.updater.moveFinished)

    def get_hardware_status(self):
        pos = self._motor_x.position, self._motor_y.position, self._gripper.value
        state = self._motor_x.state(), self._motor_y.state(), self._gripper.state()
        return pos, state

    def go_home(self):
        self.move_to([0, 0], "travel")
        self.lg.info("went home")

    def home(self, precise=True):
        # TODO: this function cannot be tested in simulation mode and therefore needs testing and adjusting on the hardware
        self.lg.info("homing translations")
        self.move_to_limits("homing")
        correction = np.array(self.get_hardware_status()[0][0:1])
        self._motor_x.SetStepPosition(0)
        self._motor_y.SetStepPosition(0)
        self.move_to(self.config.PeakAbsorber.limit_switch_max_hysterisis, "travel")
        if self._motor_x.cwlimit or self._motor_y.cwlimit:
            self.lg.critical("homing switches didn't disengage after moving %s out!", str(self.config.PeakAbsorber.limit_switch_max_hysterisis))
        if precise:
            self.move_to_limits("homing_precise")
            correction += np.array(self.get_hardware_status()[0][0:1])
            self._motor_x.SetStepPosition(0)
            self._motor_y.SetStepPosition(0)
            self.move_to(self.config.PeakAbsorber.limit_switch_max_hysterisis, "travel")
            if self._motor_x.cwlimit or self._motor_y.cwlimit:
                self.lg.critical("homing switches didn't disengage after moving %s out!", str(self.config.PeakAbsorber.limit_switch_max_hysterisis))
        self._motor_x.SetStepPosition(0)
        self._motor_y.SetStepPosition(0)
        self.lg.info("homing corrected position by %s mm", str(correction))
        return correction
        # TODO: if the correction is too high warn the user that the beamstops need to be reparked manually

    def move_to_limits(self, slewrate):
        self.lg.debug("moving to cw limits")
        self._motor_x.slewrate = self.config.PeakAbsorber.slewrates[slewrate]
        self._motor_y.slewrate = self.config.PeakAbsorber.slewrates[slewrate]
        self._motor_x.moveToCwLimit()
        self._motor_y.moveToCwLimit()
        self.updater.set_motor_moving()
        self.wait(self.config.PeakAbsorber.timeout_ms, self.updater.moveFinished)

    @staticmethod
    def wait(timeout, signal=None):
        loop = QEventLoop()
        QTimer.singleShot(timeout, loop.quit)
        if signal is not None:
            signal.connect(loop.quit)
        loop.exec()


class MovementUpdater(QObject):
    moveFinished = pyqtSignal()
    gripperFinished = pyqtSignal()
    posChanged = pyqtSignal(tuple)
    gripperChanged = pyqtSignal(float)

    def __init__(self, config, absorber_hardware):
        super().__init__()
        self.config = config
        self.absorber_hardware = absorber_hardware
        self.lg = logging.getLogger("main.hardware.movementupdater")

        self.motor_moving = False
        self.gripper_moving = False
        self.current_move = None
        self.last_status = None
        self.last_gripper_pos = 0
        self.estimated_real_gripper_pos = 0

        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(1000/self.config.PeakAbsorber.idle_polling_rate)

        self.gripper_timer = QTimer()
        self.gripper_timer.timeout.connect(self.update_gripper_pos)

    def update(self):
        status = self.absorber_hardware.get_hardware_status()
        if self.motor_moving and status[1][0] != tango.DevState.MOVING and status[1][1] != tango.DevState.MOVING:
            self.moveFinished.emit()
            self.set_idle()
        if self.current_move is not None:
            self.current_move.update_pos((status[0][0], status[0][1]))
        if self.last_status != status:
            self.posChanged.emit((status[0][0], status[0][1]))
            self.last_status = status
        if self.last_gripper_pos != status[0][2]:
            self.last_gripper_pos = status[0][2]
            self.estimate_gripper_pos()

    def set_current_move(self, move):
        self.update()
        self.current_move = move

    def set_idle(self):
        self.motor_moving = False
        self.gripper_moving = False
        self.timer.setInterval(self.config.PeakAbsorber.idle_polling_rate)

    def set_motor_moving(self):
        self.motor_moving = True
        self.timer.setInterval(self.config.PeakAbsorber.moving_polling_rate)

    def set_gripper_moving(self):
        self.gripper_moving = True
        self.timer.setInterval(self.config.PeakAbsorber.moving_polling_rate)

    def estimate_gripper_pos(self):
        self.lg.debug("gripper changed state")
        self.estimated_real_gripper_pos = float(not self.last_gripper_pos)
        self.gripper_timer.start(1000/self.config.PeakAbsorber.moving_polling_rate)

    def update_gripper_pos(self):
        if self.last_gripper_pos:
            self.estimated_real_gripper_pos += 1/self.config.PeakAbsorber.moving_polling_rate/(self.config.PeakAbsorber.gripper_time_ms/1000)
        elif not self.last_gripper_pos:
            self.estimated_real_gripper_pos -= 1/self.config.PeakAbsorber.moving_polling_rate/(self.config.PeakAbsorber.gripper_time_ms/1000)

        if self.estimated_real_gripper_pos >= 1 or self.estimated_real_gripper_pos <= 0:
            self.gripper_timer.stop()
            self.set_idle()
            self.estimated_real_gripper_pos = self.last_gripper_pos
            self.gripperFinished.emit()

        self.gripperChanged.emit(self.estimated_real_gripper_pos)
