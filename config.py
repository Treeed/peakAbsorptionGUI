import numpy as np
import pyqtgraph as pg


# everything in millimeters, milliseconds, unless otherwise specified

class PeakAbsorber:
    # address of the tango server and paths to the motors
    tango_server = 'haspp02oh1:10000/'
    motor_x_path = 'p02/motor/elab.01'
    motor_y_path = 'p02/motor/elab.02'
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
    # the acceleration needs to be set by the gui to match the motor movements to each other.
    # Also make sure to set the Baserate to zero on the tango server or this will not work and collisions between beamstops may occur because the exact trajectory is not known by the software
    max_acceleration = 100000
    # distance a beamstop moves back on its trajectory after being released.
    # This is mostly relevant because of the lower magnet being dragged behind and attracting the top magnet back
    backlash = 1.5

    # positive limits of the drive mechanism (negative limits are always zero)
    limits = np.array([500, 495])
    # radius of one beamstop for display and collision detection
    beamstop_radius = 2.5
    # time it takes the gripper to fully extend or retract after the corresponding bit as been set on the tango server
    gripper_time_ms = 500
    # this is either:
    # -the safe distance that needs to be kept between beamstops so the magnets don't snap together
    # -or the radius of the gripper + beamstop radius + backlash
    # whichever is smaller
    # this radius must be lower than the distance between parking positions
    beamstop_spacing = 14.9
    # time after which a single move is aborted and considered failed
    timeout_ms = 100000
    # distance in mm we need to move out of the limit switch to make sure it definitely turns off
    limit_switch_max_hysterisis = [1, 1]
    # motor direction in which the coordinate values decrease / side on which the limit switch that represents the origin is for axes [x, y]
    # each axis can be "cw" or "ccw"
    zero_limit = ["ccw", "ccw"]
    # distance error above which you can't catch a beamstop anymore / below which a beamstop is succesfully centered in the gripper
    max_distance_error = 0.5
    # distance below which differences are considered insignificant and position of a beamstop does not have to be corrected.
    # must be larger than the increments the tango server is counting in
    epsilon = 0.1
    # virtual penalty distance added to parked beamstops to avoid moving them into the active area
    # this is used during the beamstop assignment to make sure all active beamstops are used up before parked ones get moved in
    # set this to the maximum possible movement distance of the peak absorber
    beamstop_inactive_cost = 1000


class Detector:
    # size of the active area of the detector. This is only used for the box shown in the gui
    active_area = np.array([409.6, 409.6])
    # position of the lower left corner of the detector relative to the minimum position of the drive mechanism
    detector_origin = np.array([65, -10])
    # size of one pixel in x and y
    # this is used to scale the image, so picture-resolution*pixel_size should match the "active area"
    pixel_size = np.array([0.200, 0.200])
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
    parking_positions = np.array([[28.5, 10.5 + 15 * beamstop_nr] for beamstop_nr in range(25)])
