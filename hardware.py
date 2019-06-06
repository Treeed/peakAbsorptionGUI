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
        self.lg.info("moving beamstop %d to %s", move.beamstop_nr, str(move.target_pos))
        self.move_to(move.beamstop_pos, "travel")
        self.move_gripper(1)
        self.updater.set_current_move(move)
        for pos in move.path[:-1]:
            self.move_to(pos, "beamstop")
        self.move_to_backlash(move.path[-1])
        self.updater.set_current_move(None)
        self.move_gripper(0)

        move.finish_move()

    def move_gripper(self, pos):
        self.lg.debug("moving gripper to %s", str(pos))
        self._gripper.value = pos
        self.updater.set_gripper_moving()
        self.wait(self.config.PeakAbsorber.timeout_ms, self.updater.gripperFinished)

    def move_to_backlash(self, pos, slewrate="beamstop"):
        """ moves to and over a point by [backlash]mm, then moves back to the point"""
        cur_pos = np.array([self._motor_x.position, self._motor_y.position])
        move_vector = pos-cur_pos
        if np.sum(move_vector) == 0:
            self.lg.debug("we already are at the target. returning.")
            return
        unit_move = move_vector/absorberfunctions.calc_vec_len(move_vector)
        backlash_target = unit_move*self.config.PeakAbsorber.backlash+pos

        self.move_to(backlash_target, slewrate)
        self.move_to(pos, slewrate)

    def move_to(self, pos, slewrate="beamstop"):
        self.lg.debug("moving to %s with %s speed", str(pos), slewrate)
        # TODO: handle errors
        distance = np.abs([self._motor_x.position - pos[0], self._motor_y.position - pos[1]])
        travel_distance = absorberfunctions.calc_vec_len([distance[0], distance[1]])
        if travel_distance < self.config.PeakAbsorber.epsilon:
            return
        # calculate slewrates at which the motors will reach their target values simultaneously and the total grabber speed matches the set slewrate
        slewrates = None
        if self.config.PeakAbsorber.slewrates[slewrate][0]:
            slewrates = distance * self.config.PeakAbsorber.slewrates[slewrate][0] / travel_distance
        # if no total grabber slewrate was specified or the limit for the individual axises is lower than the calculated slewrates set the axis
        # with the most way to travel to the maximum axis speed and the other to a fraction of the speed so both reach their targets simultaneously
        further_axis = np.argmax(distance)
        if self.config.PeakAbsorber.slewrates[slewrate][1] and (slewrates is None or np.any(slewrates > self.config.PeakAbsorber.slewrates[slewrate][1])):
            slewrates = [0, 0]
            slewrates[further_axis] = self.config.PeakAbsorber.slewrates[slewrate][1]
            slewrates[int(not further_axis)] = distance[int(not further_axis)] * self.config.PeakAbsorber.slewrates[slewrate][1] / distance[further_axis]
        if slewrates is None:
            raise absorberfunctions.ConfigError("slewrates[{}]".format(slewrate), "slewrate limits for any action cannot both be zero")

        # set the accelerations to the maximum values at which the ratio is the same as the ratio of the distances so that the axises reach their target speeds simultanously
        # Similar to the version for the slewrates but without an option for a total acceleration of the grabber because the grabber and beamstops are not very heavy but the individual translations are
        accelerations = [0, 0]
        accelerations[further_axis] = self.config.PeakAbsorber.max_acceleration
        accelerations[int(not further_axis)] = distance[int(not further_axis)] * self.config.PeakAbsorber.max_acceleration / distance[further_axis]

        self._motor_x.slewrate = slewrates[0]
        self._motor_y.slewrate = slewrates[1]
        self._motor_x.acceleration = accelerations[0]
        self._motor_y.acceleration = accelerations[1]
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
        """
        Moves the translations to their negative limit switches and sets the origin just outside of them

        :param boolean precise:  If this is set after initially slamming into the limit switches, possible slightly missing the exact switching point, another slow approach is done to improve repeatability
        :returns: Correction in mm that was done to the origin.
        """
        self.lg.info("homing translations")
        self.move_to_limits("homing")
        correction = np.array(self.get_hardware_status()[0][0:2])
        self.zero_steps()
        self.move_to(self.config.PeakAbsorber.limit_switch_max_hysterisis, "travel")
        self.check_limits_disengaged()
        if precise:
            self.move_to_limits("homing_precise")
            correction += np.array(self.get_hardware_status()[0][0:2])
            self.zero_steps()
            self.move_to(self.config.PeakAbsorber.limit_switch_max_hysterisis, "travel")
            self.check_limits_disengaged()
        correction += np.array(self.get_hardware_status()[0][0:2])
        self.zero_steps()
        if abs(correction[0]) > self.config.PeakAbsorber.max_distance_error or abs(correction[1]) > self.config.PeakAbsorber.max_distance_error:
            self.lg.warning("Homing corrected by %s mm. The correction done by homing was too large to catch beamstops placed before the correction. You should repark all beamstops manually. Failure to do so may result in hardware damage.", str(correction))
        else:
            self.lg.info("homing corrected position by %s mm", str(correction))
        return correction

    def check_limits_disengaged(self):
        """helper function for homing, checks if homing switches are disengaged and raises an error if not"""
        if self.config.PeakAbsorber.zero_limit[0] == "cw":
            xlimit = self._motor_x.cwlimit
        elif self.config.PeakAbsorber.zero_limit[0] == "ccw":
            xlimit = self._motor_x.ccwlimit
        else:
            raise absorberfunctions.ConfigError("PeakAbsorber.zero_limit[0]", "zero_limit isn't cw or ccw")

        if self.config.PeakAbsorber.zero_limit[0] == "cw":
            ylimit = self._motor_y.cwlimit
        elif self.config.PeakAbsorber.zero_limit[0] == "ccw":
            ylimit = self._motor_y.ccwlimit
        else:
            raise absorberfunctions.ConfigError("PeakAbsorber.zero_limit[1]", "zero_limit isn't cw or ccw")

        if xlimit or ylimit:
            raise HardwareError("homing", "homing switches didn't disengage after moving {} out!".format(self.config.PeakAbsorber.limit_switch_max_hysterisis))

    def move_to_limits(self, slewrate):
        """
        Moves the motors to the negative limit switches.
        :param slewrate: Slewrate to move at. Should be "homing" or "homing_precise"
        :return: nothing
        """
        self.lg.debug("moving to cw limits")
        self._motor_x.slewrate = self.config.PeakAbsorber.slewrates[slewrate][1]
        self._motor_y.slewrate = self.config.PeakAbsorber.slewrates[slewrate][1]
        self._motor_x.acceleration = self.config.PeakAbsorber.max_acceleration
        self._motor_y.acceleration = self.config.PeakAbsorber.max_acceleration

        if self.config.PeakAbsorber.zero_limit[0] == "cw":
            self._motor_x.moveToCwLimit()
        elif self.config.PeakAbsorber.zero_limit[0] == "ccw":
            self._motor_x.moveToCcwLimit()
        else:
            raise absorberfunctions.ConfigError("PeakAbsorber.zero_limit[0]", "zero_limit isn't cw or ccw")

        if self.config.PeakAbsorber.zero_limit[0] == "cw":
            self._motor_y.moveToCwLimit()
        elif self.config.PeakAbsorber.zero_limit[0] == "ccw":
            self._motor_y.moveToCcwLimit()
        else:
            raise absorberfunctions.ConfigError("PeakAbsorber.zero_limit[0]", "zero_limit isn't cw or ccw")

        self.updater.set_motor_moving()
        self.wait(self.config.PeakAbsorber.timeout_ms, self.updater.moveFinished)

    def zero_steps(self):
        """helper function for homing, sets the current position to be the coordinate origin"""
        self._motor_x.SetStepPosition(0)
        self._motor_y.SetStepPosition(0)

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
        self.timer.setInterval(1000/self.config.PeakAbsorber.idle_polling_rate)

    def set_motor_moving(self):
        self.motor_moving = True
        self.timer.setInterval(1000/self.config.PeakAbsorber.moving_polling_rate)

    def set_gripper_moving(self):
        self.gripper_moving = True
        self.timer.setInterval(1000/self.config.PeakAbsorber.moving_polling_rate)

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


class HardwareError(Exception):
    """
    Exception if something unexpected happens to the hardware
    """

    def __init__(self, action, message):
        """
        init

        :param str action: action that was performed
        :param str message: error message
        """
        self.action = action
        self.message = message