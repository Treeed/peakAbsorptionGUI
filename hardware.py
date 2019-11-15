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

        self.updater = None
        self.lg = logging.getLogger("main.hardware.hardware")

        self.raise_emergency_stop = False

    def move_beamstop(self, move):
        self.lg.info("moving beamstop %d to %s", move.beamstop_nr, str(move.target_pos))
        self.move_to(move.beamstop_pos, "travel")
        self.move_gripper(1)
        for pos in move.path[:-1]:
            self.move_to(pos, "beamstop")
        self.move_to_backlash(move.path[-1])
        self.move_gripper(0)

        move.finish_move()

    def move_gripper(self, pos):
        self.lg.debug("moving gripper to %s", str(pos))
        self._gripper.write_attribute(self.config.PeakAbsorber.gripper_attribute, pos)
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
        if not self.updater.motors_ready:
            raise HardwareError("move", "move requested but motors not ready")

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
        status = {}
        status["pos"] = self._motor_x.position, self._motor_y.position
        status["gripper_pos"] = self._gripper.read_attribute(self.config.PeakAbsorber.gripper_attribute).value
        status["motor_x_state"] = self._motor_x.state()
        status["motor_y_state"] = self._motor_y.state()
        status["gripper_state"] = self._gripper.state()
        return status

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
        correction = np.array(self.get_hardware_status()["pos"])
        self.zero_steps()
        self.move_to(self.config.PeakAbsorber.limit_switch_max_hysterisis, "travel")
        self.check_limits_disengaged()
        if precise:
            self.move_to_limits("homing_precise")
            correction += np.array(self.get_hardware_status()["pos"])
            self.zero_steps()
            self.move_to(self.config.PeakAbsorber.limit_switch_max_hysterisis, "travel")
            self.check_limits_disengaged()
        correction += np.array(self.get_hardware_status()["pos"])
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

    def wait(self, timeout, signal=None):
        """
        function to wait until either the timeout is reached or the signal is emitted
        while waiting the QEventLoop is run
        :param timeout: time to wait in ms
        :param signal: signal to stop on
        :raises emergencyStop when the raise_emergency_stop flag is set during the waittime
        """
        loop = QEventLoop()
        QTimer.singleShot(timeout, loop.quit)
        if signal is not None:
            signal.connect(loop.quit)
        # because this function is designed to wait for the hardware to move before the next move can be started
        # we need to check if there was an emergency stop and if so keep the next moves from getting executed by raising an exception
        self.raise_emergency_stop = False
        loop.exec()
        if self.raise_emergency_stop:
            self.lg.warning("Stop button was pressed while performing moves, cancelling all further moves")
            raise EmergencyStop("estop was pressed while inside hardware class")

    def stop(self):
        """
        stops any current move (whether started by the program or something else) and sets the raise emergency stop flag
        this flag will cause an exception to be raised only if this function is started inside the eventloop inside the wait function of the hardware
        this allows the stop button to be active at all times but only interrupt the program flow if the program is currently doing something to the hardware
        """
        self._motor_x.StopMove()
        self._motor_y.StopMove()
        self.raise_emergency_stop = True
        self.lg.warning("Stop button was pressed; stopped all movements!")


class MovementUpdater(QObject):
    # emitted when set_motor_moving was called before and the motors are idle (again)
    moveFinished = pyqtSignal()
    # emitted when the set period of time for the gripper movement estimate was elapsed
    gripperFinished = pyqtSignal()
    # emitted when the position changed.
    # the first tuple contains the position (x,y)
    # the second tuple contains one element which is either the beamstop number if there is a beamstop currently grabbed or None if not
    posChanged = pyqtSignal(tuple, tuple)
    # emitted mutliple times after the position of the gripper changed each time the estimate for the real gripper posiiton changes
    # the float is the estimated gripper position between 0 and 1
    gripperEstimateChanged = pyqtSignal(float)

    def __init__(self, config, absorber_hardware, beamstop_manager):
        super().__init__()
        self.config = config
        self.absorber_hardware = absorber_hardware
        self.beamstop_manager = beamstop_manager
        self.lg = logging.getLogger("main.hardware.movementupdater")

        self.status = {"pos": None, "gripper_pos": 0, "motor_x_state": None, "motor_y_state": None, "gripper_state": None}
        self.motors_ready = False
        self.motor_move_started = False
        self.estimated_real_gripper_pos = 0
        self.grabbed_beamstop_nr = None

        self._timer = QTimer()
        self._timer.timeout.connect(self.update)
        self._timer.start(1000 / self.config.PeakAbsorber.idle_polling_rate)

        self._gripper_timer = QTimer()
        self._gripper_timer.timeout.connect(self.update_gripper_pos)

    def update(self):
        new_status = self.absorber_hardware.get_hardware_status()

        new_motors_ready = new_status["motor_x_state"] == tango.DevState.ON and new_status["motor_y_state"] == tango.DevState.ON

        if self.motor_move_started and new_motors_ready:
            self.moveFinished.emit()
            self.motor_move_started = False

        if self.motors_ready != new_motors_ready:
            if new_motors_ready:
                self.set_polling_rate("idle")
            else:
                self.set_polling_rate("moving")

        if self.status["gripper_pos"] != new_status["gripper_pos"]:
            self._change_gripper(new_status)

        if self.status["pos"] != new_status["pos"]:
            self.posChanged.emit(new_status["pos"], (self.grabbed_beamstop_nr, ))


        self.motors_ready = new_motors_ready
        self.status = new_status

    def set_polling_rate(self, rate):
        if rate == "moving":
            polling_rate = self.config.PeakAbsorber.moving_polling_rate
        elif rate == "idle":
            polling_rate = self.config.PeakAbsorber.idle_polling_rate
        else:
            ValueError("not a polling rate")
        self._timer.setInterval(1000 / polling_rate)

    def set_motor_moving(self):
        self.motor_move_started = True
        self.set_polling_rate("moving")

    def _change_gripper(self, new_status):
        self.lg.debug("gripper changed state")
        if new_status["gripper_pos"] == 1:
            grabbed_beamstop_nr = np.argwhere(absorberfunctions.calc_vec_len(self.beamstop_manager.beamstops - new_status["pos"]) < self.config.PeakAbsorber.max_distance_error)
            if grabbed_beamstop_nr.size:
                self.grabbed_beamstop_nr = grabbed_beamstop_nr[0][0]
            else:
                self.grabbed_beamstop_nr = None
        if new_status["gripper_pos"] == 0:
            if self.grabbed_beamstop_nr is not None:
                self.beamstop_manager.move(self.grabbed_beamstop_nr, new_status["pos"])
            self.grabbed_beamstop_nr = None

        # start estimating the real gripper pos
        self.estimated_real_gripper_pos = float(self.status["gripper_pos"])
        self._gripper_timer.start(1000 / self.config.PeakAbsorber.moving_polling_rate)

    def update_gripper_pos(self):
        if self.status["gripper_pos"]:
            self.estimated_real_gripper_pos += 1/self.config.PeakAbsorber.moving_polling_rate/(self.config.PeakAbsorber.gripper_time_ms/1000)
        elif not self.status["gripper_pos"]:
            self.estimated_real_gripper_pos -= 1/self.config.PeakAbsorber.moving_polling_rate/(self.config.PeakAbsorber.gripper_time_ms/1000)

        if self.estimated_real_gripper_pos >= 1 or self.estimated_real_gripper_pos <= 0:
            self._gripper_timer.stop()
            self.estimated_real_gripper_pos = self.status["gripper_pos"]
            self.gripperFinished.emit()

        self.gripperEstimateChanged.emit(self.estimated_real_gripper_pos)


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


class EmergencyStop(Exception):
    """
    Exception to raise when the user presses the STOP buttton
    """

    def __init__(self, message):
        self.message = message
