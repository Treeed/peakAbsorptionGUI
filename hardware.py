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

def wait_move(motor):
    while motor.state() == tango.DevState.MOVING:
        time.sleep(0.01)

