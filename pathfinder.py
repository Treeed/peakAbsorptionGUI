import absorberfunctions
import numpy as np


def find_path(starting_point, final_destination, obstacles, radius, absorber_limits):
    """
    Always finds an optimal path around a set of circular obstacles if there is one. (Except: see to do in docstring)

    Because no circular paths are supported the obstacles are treated like circles for the collision detection but as squares for the circumventing paths.

    The principle is to start with a path which contains only the start and a destination which is only the final destination,
    then draw a path between start and end, check for obstacles and add the corners of the obstacles if any are found as possible destinations.
    If no obstacles are detected save path with the new endpoint "end" as a new path.
    Repeat with each start and end where start is the last point of any found path and end is any destination.

    TODO: 1. performance is very poor due to the principle of the algorithm but it might be possible to make some improvements
    TODO: 2. in an edge case where there is space between two circles but the corners of a corresponding rectangle intersects
    TODO:       with the other circle the path may not be found because the circumvention around the rectangle will go through the nearby circle. One could increase to hexa/octagons or higher if needed

    :param starting_point: point from which the path should start. There may not be an obstacle within "radius" of this point. Format [x, y]
    :param final_destination: point to which the path should go. There may not be an obstacle within "radius" of this point. Format [x, y]
    :param obstacles: List of points which may not be approached to less than "radius" by the path. Format [[x, y], [x, y], ...]
    :param radius: radius of the circular obstacles to circumvent. single skalar
    :param absorber_limits: limits over which the path should not go. Lower limits are always 0,0. Format [max_x, max_y]
    :return: list of points which form a path which does not come within radius of any of the obstacles. Including start and end point. Format [[x, y], [x, y] ...] if a path was found, [None] otherwise
    """
    # lists with point cascade and length
    paths = [[[starting_point], 0]]
    # lists with destination and shortest path to it
    destinations = [[final_destination, [None]]]
    # list of start/end combos that were already checked
    checked = []
    # always contains the shortest path found to final_destination
    to_destination = destinations[0][1]
    progress = True

    while progress:
        # breaks the while loop if no new destinations or paths could be found in the last round
        progress = False

        for path_index, path in enumerate(paths):
            # if the path we're looking at is already longer than the shortest one to destination we don't care
            if to_destination[0] is not None and path[1] >= to_destination[1]:
                continue

            start = np.array(path[0][-1])
            for destination_index, destination in enumerate(destinations):
                end = np.array(destination[0])

                # fancy way of writing "if end in path[0] or [start, end] in checked" to make numpy happy which doesnt like the "in" operator
                if np.any(np.equal(end, path[0]).all(1)) or (checked and np.any(np.equal(checked, [start, end]).all((1, 2)))):
                    continue
                checked.append([start, end])

                # if this destination was already reached with a shorter pathlength we don't care
                new_pathlength = path[1] + absorberfunctions.calc_vec_len(end-start)
                if destination[1][0] is not None and destination[1][1] < new_pathlength:
                    continue

                progress = True

                obstacle_corners = find_obstacle_corners([start, end], obstacles, radius, absorber_limits)

                # if we found an obstacle on the line we just add the corners of the obstacle to the destinations (if it's not already in there)
                for corner in obstacle_corners:
                    for destination_contained in destinations:
                        if np.all(destination_contained[0] == corner):
                            break
                    else:
                        destinations.append([corner, [None]])

                if not obstacle_corners.size:
                    # if we found a path to a destination that has been reached before with a longer path we overwrite the values in that path with our better ones
                    # the reason to overwrite the values rather than the whole list is to keep any references to this list intact
                    if destination[1][0] is not None:
                        destination[1][0] = path[0]+[end]
                        destination[1][1] = new_pathlength
                    # if this is a not previously reached destination we add our new path and insert a reference to it into the destination
                    else:
                        paths.append([path[0]+[end], new_pathlength])
                        destination[1][0] = paths[-1][0]
                        destination[1].append(paths[-1][1])
    return to_destination[0]


def find_obstacle_corners(line, obstacles, radius, absorber_limits):
    """
    Checks which obstacles are crossed by the line and returns corners of the squares around them

    Obstacles are circles with the center at their point and a radius of radius.
    The output contains all square corners inside the specified absorber limits and above zero.

    @:param line: the line which should be checked in the format [[startx, starty], [endx, endy]]
    @:param obstacles: points of the obstacles in the format [[obstacle1x, obstacle1y], [obstacle2x, obstacle2y],... ]
    @:param radius: the radius of the obstacles, single scalar value
    @:param absorber_limits: limits of the absorber in x and y direction as [limitx, limity]
    """
    # first check for intersections after https://codereview.stackexchange.com/questions/86421/line-segment-to-circle-collision-algorithm
    line_vector = line[1] - line[0]
    a = np.dot(line_vector, line_vector)
    b = 2 * np.dot(line[0] - obstacles, line_vector)
    c = np.dot(line[0], line[0]) + (obstacles * obstacles).sum(1) - 2 * np.dot(obstacles, line[0]) - radius ** 2
    sqrt_disc = np.sqrt(b ** 2 - 4 * a * c)
    t1 = (-b + sqrt_disc) / (2 * a)
    t2 = (-b - sqrt_disc) / (2 * a)
    tt = np.any([np.all([0 <= t1, t1 <= 1], axis=0), np.all([0 <= t2, t2 <= 1], axis=0)], axis=0)
    in_the_way = obstacles[tt]
    # compile a list of corners of a square around the circle with edge length 2radius
    radius += .2  # TODO: find solution for this
    obstacle_corners = np.concatenate([in_the_way+[radius, radius], in_the_way+[radius, -radius], in_the_way+[-radius, radius], in_the_way+[-radius, -radius]])
    # return all corners that are within the peakabsorber limits
    return obstacle_corners[np.all([obstacle_corners[:, 0] > 0, obstacle_corners[:, 1] > 0, obstacle_corners[:, 0] < absorber_limits[0], obstacle_corners[:, 1] < absorber_limits[1]], axis=0)]
