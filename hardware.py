import time
import tango
import absorberfunctions

class PeakAbsorberHardware:
    def __init__(self):
        #configurables
        _motor_x_path = 'p02/motor/elab.01' # config
        _motor_y_path = 'p02/motor/elab.02' # config
        _gripper_path = 'p02/register/elab.out08' # config
        self._backlash_mm = 3  # config
        self._slewrates = {
            "travel" : 1000,
            "beamstop" : 1000,
            "homing" : 1000,
        } # config
        self.parking_positions  = [[1713.05066106, 2089.98346159],
                                     [1724.1369199,  1762.93882584],
                                     [1718.59379048, 1397.09228415],
                                     [1701.96440222, 1070.04764841],
                                     [1746.30943758,  715.28736556],
                                     [1713.05066106,  349.44082388],
                                     [1502.41174312,    5.76679987],
                                     [1114.39268376,  -10.86258839],
                                     [ 770.71865975,  -27.49197665],
                                     [ 421.50150633,  -21.94884723],
                                     [  44.56870581,  -10.86258839],
                                     [  50.11183522,  299.5526591 ],
                                     [  94.45687058,  654.31294195],
                                     [  61.19809406, 1025.70261305],
                                     [  55.65496464, 1302.85908402],
                                     [  33.48244697, 1663.16249629],
                                     [  11.30992929, 1979.1208732 ]] #config


        self._gripper = tango.DeviceProxy(_gripper_path)
        self._motor_x = tango.DeviceProxy(_motor_x_path)
        self._motor_y = tango.DeviceProxy(_motor_y_path)

        self.beamstops = []
        self.beamstop_active = []

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

    def move_beamstop(self, beamstop, target):
        pass

    def move_to(self, pos, slewrate = "beamstop"):
        traveldistance = absorberfunctions.calc_vec_len(self._motor_x.position, pos[0], self._motor_y.position, pos[1])
        # calculate slewrates at which the motors will reach their target values simultanously and the total grabber speed matches the set slewrate
        self._motor_x.slewrate = pos[0] * self._slewrates[slewrate] / traveldistance
        self._motor_y.slewrate = pos[1] * self._slewrates[slewrate] / traveldistance
        self._motor_x.position = pos[0]
        self._motor_y.position = pos[1]
        self.wait_move(self._motor_x)
        self.wait_move(self._motor_y)

    def wait_move(self, motor):
        while motor.state() == tango.DevState.MOVING:
            time.sleep(0.01)


