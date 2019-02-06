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

    # speeds at which the beamstops are moved in steps per second. This is first a limit on the total gripper speed and second a limit on the speed of each individual axis.
    # when moving a beamstops the diagonal gripper speed is important so it doesn't loose its magnet but when traveling only the individual axises have speed limits
    # 0 means unlimited. When homing only the individual speed limits are used
    slewrates = {
        "travel": (0, 70000),
        "beamstop": (30000, 50000),
        "homing": (0, 1000),
        "homing_precise": (0, 100),
    }
    # maximum acceleration to be set on the motors in steps/s^2
    # the acceleration needs to be set by the gui to match the motor movements to each other. Make sure to set the Baserate to zero or this will not work and collisions between beamstops may occur because the exact trajectory is not known by the software
    max_acceleration = 10000

    # positive limits of the drive mechanism (negative limits are always zero)
    limits = np.array([500, 495])
    # radius of one beamstop for display and collision detection
    beamstop_radius = 1.5
    # time it takes the gripper to fully extend or retract after the corresponding bit as been set on the tango server
    gripper_time_ms = 2000
    # radius which needs to be free of obstacles around the gripper when it is down.
    # Not considering the magnets this would be the distance of the outermost part to the center of the gripper
    # but because the magnets attract each other on a bigger radius this is the safe distance that needs to be kept between magnets so they don't snap together minus 1.5 (radius of a beamstop)
    gripper_radius = 15
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
    # manipulations to apply to the image in order. Any number of manipulations can be inserted. Available are "rot90" "rot180" "rot270" "mir_horiz" "mir_vert"
    image_manipulations = []


class Gui:
    # colors can be given in any pyqtgraph compatible format
    # common ones are just letters for the starting letter of the color, pg.hsvColor() setting the hue in a scale from 0 to 1 and rgb values in the format [r, g, b]
    color_absorber_geometry = 'w'
    color_beamstops = 'r'
    color_handle = 'b'
    color_trajectory = 'w'
    # this is the color map used to change the crosshair color depending on the height of the gripper
    # 0 is gripper disengaged and 1 is gripper engaged
    color_crosshair = pg.ColorMap([0, 1], [[0, 255, 0], [255, 0, 0]])
    #default radius of a handle
    radius_handle = 2


class ParkingPositions:
    parking_positions = np.array([
        [ 10,  15],
        [ 10,  30],
        [ 10,  45],
        [ 10,  60],
        [ 10,  75],
        [ 10,  90],
        [ 10, 105],
        [ 10, 120],
        [ 10, 135],
        [ 10, 150],
        [ 10, 165],
        [ 10, 180],
        [ 10, 195],
        [ 10, 210],
        [ 10, 225],
        [ 10, 240],
        [ 10, 255],
        [ 10, 270],
        [ 10, 285],
        [ 10, 300],
        [ 10, 315],
        [ 10, 330],
        [ 10, 345],
        [ 10, 360],
        [ 10, 375],
        [ 10, 390],
        [ 10, 405],
        [ 10, 420],
        [ 10, 435],
        [ 10, 450],
        [ 10, 465],
        [ 15, 480],
        [ 30, 480],
        [ 45, 480],
        [ 60, 480],
        [ 75, 480],
        [ 90, 480],
        [105, 480],
        [120, 480],
        [135, 480],
        [150, 480],
        [165, 480],
        [180, 480],
        [195, 480],
        [210, 480],
        [225, 480],
        [240, 480],
        [255, 480],
        [270, 480],
        [285, 480],
        [300, 480],
        [315, 480],
        [330, 480],
        [345, 480],
        [360, 480],
        [375, 480],
        [390, 480],
        [405, 480],
        [420, 480],
        [435, 480],
        [450, 480],
        [465, 480],
        [480, 480],
        [485,  15],
        [485,  30],
        [485,  45],
        [485,  60],
        [485,  75],
        [485,  90],
        [485, 105],
        [485, 120],
        [485, 135],
        [485, 150],
        [485, 165],
        [485, 180],
        [485, 195],
        [485, 210],
        [485, 225],
        [485, 240],
        [485, 255],
        [485, 270],
        [485, 285],
        [485, 300],
        [485, 315],
        [485, 330],
        [485, 345],
        [485, 360],
        [485, 375],
        [485, 390],
        [485, 405],
        [485, 420],
        [485, 435],
        [485, 450],
        [485, 465]])
