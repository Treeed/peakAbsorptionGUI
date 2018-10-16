import time
import tango


class PeakAbsorberHardware:
    def __init__(self):

        motor_x_path = 'p02/motor/elab.01'  # x_motor
        motor_y_path = 'p02/motor/elab.02'  # y_motor
        gripper_path = 'p02/register/elab.out08'  # io_register
        self.backlash_mm = 3  # backlash
        self.amount = 5  # number of beamstops


        self.gripper = tango.DeviceProxy(gripper_path)
        self.motor_x = tango.DeviceProxy(motor_x_path)
        self.motor_y = tango.DeviceProxy(motor_y_path)

    def rearrange(self):
        ch_list = []
        ch_ind = self.list_cmp(self.roiPos, self.roiPosOld)
        for i in range(0, len(ch_ind)):
            ch_list.append(self.roiPosOld[ch_ind[i]])
        for i in range(0, len(ch_list)):
            self.gripper.value = 0
            self.motor_x.position = ch_list[i][0]
            self.wait_move(self.motor_x)
            self.motor_y.position = ch_list[i][1]
            self.wait_move(self.motor_y)
            self.gripper.value = 1
            time.sleep(2)
            self.motor_x.position = self.roiPos[i][0]
            self.wait_move(self.motor_y)
            self.motor_y.position = 400 - self.roiPos[i][1]
            self.wait_move(self.motor_y)
            self.gripper.value = 0
            time.sleep(2)
            self.motor_x.position = 0
            self.wait_move(self.motor_x)
            self.motor_y.position = 0
            self.wait_move(self.motor_y)
        self.roiPosOld = self.roiPos


    def move_all(self):
        self.gripper.value = 0
        time.sleep(2)
        self.roiPosOld = self.roiPos
        bs_list = self.make_bs_list(self.amount)
        self.roiPos = self.calc_ind(self.roiPos)
        self.roiPos = self.sort_ind(self.roiPos, 2)

        for i in range(0, len(self.roiPos)):
            self.motor_x.position = bs_list[i][0]
            self.wait_move(self.motor_x)
            self.motor_y.position = bs_list[i][1]
            self.wait_move(self.motor_y)
            self.gripper.value = 1
            time.sleep(2)
            self.motor_x.position = self.roiPos[i][0]
            self.wait_move(self.motor_x)
            self.motor_y.position = 400 - self.roiPos[i][1]
            self.wait_move(self.motor_y)
            self.gripper.value = 0
            time.sleep(2)
        self.motor_x.position = 0
        self.motor_y.position = 0
        self.roi_pos_old = self.roiPos


    def calibrate(self):
        slew_buf_x = self.motor_x.slewrate
        slew_buf_y = self.motor_x.slewrate
        self.motor_x.slewrate = 400
        self.motor_y.slewrate = 400
        self.motor_x.moveToCwLimit()
        self.wait_move(self.motor_x)
        self.motor_x.calibrate(0)
        self.motor_y.moveToCwLimit()
        self.wait_move(self.motor_x)  # TODO: sure you wait for x again?
        self.motor_y.calibrate(0)  # TODO: don't use calibrate
        self.motor_x.slewrate = slew_buf_x
        self.motor_y.slewrate = slew_buf_y

    def wait_move(self, motor):
        while motor.state() == tango.DevState.MOVING:
            time.sleep(0.01)
