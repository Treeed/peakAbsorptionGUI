import time
import tango
import absorberfunctions

class PeakAbsorberHardware:
    def __init__(self):
        #configurables
        _motor_x_path = 'p02/motor/elab.01'  # x_motor
        _motor_y_path = 'p02/motor/elab.02'  # y_motor
        _gripper_path = 'p02/register/elab.out08'  # io_register
        self._backlash_mm = 3  # backlash
        self._slewrates = {
            "travel" : 1000,
            "beamstop" : 1000,
            "homing" : 1000,
        }


        self._gripper = tango.DeviceProxy(_gripper_path)
        self._motor_x = tango.DeviceProxy(_motor_x_path)
        self._motor_y = tango.DeviceProxy(_motor_y_path)

        self.active_beamstops = []
        self.inactive_beamstops = []

    def rearrange(self):
        ch_list = []
        ch_ind = self.list_cmp(self.roiPos, self.roiPosOld)
        for i in range(0, len(ch_ind)):
            ch_list.append(self.roiPosOld[ch_ind[i]])
        for i in range(0, len(ch_list)):
            self._gripper.value = 0
            self._motor_x.position = ch_list[i][0]
            self.wait_move(self._motor_x)
            self._motor_y.position = ch_list[i][1]
            self.wait_move(self._motor_y)
            self._gripper.value = 1
            time.sleep(2)
            self._motor_x.position = self.roiPos[i][0]
            self.wait_move(self._motor_y)
            self._motor_y.position = 400 - self.roiPos[i][1]
            self.wait_move(self._motor_y)
            self._gripper.value = 0
            time.sleep(2)
            self._motor_x.position = 0
            self.wait_move(self._motor_x)
            self._motor_y.position = 0
            self.wait_move(self._motor_y)
        self.roiPosOld = self.roiPos


    def move_all(self):
        self._gripper.value = 0
        time.sleep(2)
        self.roiPosOld = self.roiPos
        bs_list = self.make_bs_list(self.amount)
        self.roiPos = self.calc_ind(self.roiPos)
        self.roiPos = self.sort_ind(self.roiPos, 2)

        for i in range(0, len(self.roiPos)):
            self._motor_x.position = bs_list[i][0]
            self.wait_move(self._motor_x)
            self._motor_y.position = bs_list[i][1]
            self.wait_move(self._motor_y)
            self._gripper.value = 1
            time.sleep(2)
            self._motor_x.position = self.roiPos[i][0]
            self.wait_move(self._motor_x)
            self._motor_y.position = 400 - self.roiPos[i][1]
            self.wait_move(self._motor_y)
            self._gripper.value = 0
            time.sleep(2)
        self._motor_x.position = 0
        self._motor_y.position = 0
        self.roi_pos_old = self.roiPos


    def calibrate(self):
        slew_buf_x = self._motor_x.slewrate
        slew_buf_y = self._motor_x.slewrate
        self._motor_x.slewrate = 400
        self._motor_y.slewrate = 400
        self._motor_x.moveToCwLimit()
        self.wait_move(self._motor_x)
        self._motor_x.calibrate(0)
        self._motor_y.moveToCwLimit()
        self.wait_move(self._motor_x)  # TODO: sure you wait for x again?
        self._motor_y.calibrate(0)  # TODO: don't use calibrate
        self._motor_x.slewrate = slew_buf_x
        self._motor_y.slewrate = slew_buf_y

    def move_to(self, pos, slewrate = "beamstop"):
        traveldistance = absorberfunctions.calc_vec_len(self._motor_x.position, pos[0], self._motor_y.position, pos[1])
        self._motor_x.slewrate = pos[0] * self._slewrates[slewrate] / traveldistance
        self._motor_y.slewrate = pos[1] * self._slewrates[slewrate] / traveldistance
        self._motor_x.position = pos[0]
        self._motor_y.position = pos[1]
        self.wait_move(self._motor_x)
        self.wait_move(self._motor_y)

    def wait_move(self, motor):
        while motor.state() == tango.DevState.MOVING:
            time.sleep(0.01)


