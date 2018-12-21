import numpy as np
import pyqtgraph as pg


# everything in millimeters, milliseconds, unless otherwise specified

class PeakAbsorber:
    # address of the tango server and paths to the motors
    tango_server = 'haspp02oh1:10000/'
    motor_x_path = 'p02/motor/elab.03'
    motor_y_path = 'p02/motor/elab.04'
    gripper_path = 'p02/register/elab.out08'

    # rates at which the values of the tango servers are polled, when idle and when moving a beamstop respectively in Hz
    idle_polling_rate = 5
    moving_polling_rate = 60

    # speeds at which the beamstops are moved in steps per second
    slewrates = {
        "travel": 100000,
        "beamstop": 100000,
        "homing": 1000,
        "homing_precise": 100,
    }

    # positive limits of the drive mechanism (negative limits are always zero)
    limits = np.array([500, 495])
    # radius of one beamstop for display and collision detection
    beamstop_radius = 1.5
    # time it takes the gripper to fully extend or retract after the corresponding bit as been set on the tango server
    gripper_time_ms = 2000
    # distance of the outermost part to the center of the gripper for collision detection when the gripper is down
    gripper_radius = 10
    # time after which a single move is aborted and considered failed
    timeout_ms = 100000
    # distance in mm we need to move out of the limit switch to make sure it definitely turns off
    limit_switch_max_hysterisis = [1, 1]
    # motor direction in which the coordinate values decrease / side on which the limit switch that represents the origin is for axes [x, y]
    # each axis can be "cw" or "ccw"
    zero_limit = ["ccw", "ccw"]
    # distance error above which you can't catch a beamstop anymore
    max_distance_error = 1
    # distance below which differences are considered a floating point error
    epsilon = 0.0001
    # virtual penalty distance added to parked beamstops to avoid moving them into the active area
    # this is used during the beamstop assignment to make sure all active beamstops are used up before parked ones get moved in
    # set this to the maximum possible movement distance of the peak absorber
    beamstop_inactive_cost = 1000


class Detector:
    # size of the active area of the detector. This is only used for the box shown in the gui
    active_area = np.array([200, 200])
    # position of the lower left corner of the detector relative to the minimum position of the drive mechanism
    detector_origin = np.array([150, 100])
    # size of one pixel in x and y
    # this is used to scale the image, so picture-resolution*pixel_size should match the "active area"
    # the value is stored in float64, feel free to put some decimal places here
    pixel_size = np.array([0.09765625, 0.09765625])


class Gui:
    # colors can be given in any pyqtgraph compatible format
    # common ones are just letters for the starting letter of the color, pg.hsvColor() setting the hue in a scale from 0 to 1 and rgb values in the format [r, g, b]
    color_absorber_geometry = 'w'
    color_beamstops = 'r'
    # this is the color map used to change the crosshair color depending on the height of the gripper
    # 0 is gripper disengaged and 1 is gripper engaged
    color_crosshair = pg.ColorMap([0, 1], [[0, 255, 0], [255, 0, 0]])


class ParkingPositions:
    parking_positions = np.array([
        [10, 10], [10, 20], [10, 30], [10, 40], [10, 50], [10, 60], [10, 70], [10, 80], [10, 90], [10, 100], [10, 110], [10, 120], [10, 130], [10, 140], [10, 150], [10, 160], [10, 170], [10, 180], [10, 190], [10, 200], [10, 210], [10, 220], [10, 230], [10, 240], [10, 250], [10, 260], [10, 270], [10, 280], [10, 290], [10, 300], [10, 310], [10, 320], [10, 330], [10, 340], [10, 350], [10, 360], [10, 370], [10, 380], [10, 390], 
        [20, 390], [30, 390], [40, 390], [50, 390], [60, 390], [70, 390], [80, 390], [90, 390], [100, 390], [110, 390], [120, 390], [130, 390], [140, 390],[150, 390], [160, 390], [170, 390], [180, 390], [190, 390], [200, 390], [210, 390], [220, 390], [230, 390], [240, 390], [250, 390], [260, 390], [270, 390], [280, 390], [290, 390], [300, 390], [310, 390], [320, 390], [330, 390], [340, 390], [350, 390], [360, 390], [370, 390], [380, 390], [390, 390], [400, 390], [410, 390], [420, 390], [430, 390], [440, 390], [450, 390], [460, 390], [470, 390], [480, 390], [490, 390], 
        [490, 380], [490, 370], [490, 360], [490, 350], [490, 340], [490, 330], [490, 320], [490, 310], [490, 300], [490, 290], [490, 280], [490, 270], [490, 260],[490, 250], [490, 240], [490, 230], [490, 220], [490, 210], [490, 200], [490, 190], [490, 180], [490, 170], [490, 160], [490, 150], [490, 140], [490, 130], [490, 120], [490, 110], [490, 100], [490, 90], [490, 80], [490, 70], [490, 60], [490, 50], [490, 40], [490, 30], [490, 20], [490, 10]
         ])
