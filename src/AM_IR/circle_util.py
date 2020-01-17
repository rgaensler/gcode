from math import atan2, pi
from typing import *

import numpy

from AM_IR.ApplicationExceptions import UnknownPlaneError
from AM_IR.Coordinate import Coordinate
from AM_IR.MelfaCoordinateService import Plane

# Global coordinate system

_RIGHTHAND_CS = [numpy.array([1, 0, 0]), numpy.array([0, 1, 0]), numpy.array([0, 0, 1])]


def get_circle_cs(veca, vecb, plane: Plane, normal_vec=None):
    """
    Calculates the coordinate system fitting into a given circle. All axes may be tilted so that the z-axis is
    perpendicular to the plane of the circle. However, the system will not be twisted around the z-axis.
    """
    # Z-axis
    if plane is Plane.XY:
        z_axis = numpy.array([0, 0, 1])
    elif plane is Plane.YZ:
        z_axis = numpy.array([-1, 0, 0])
    elif plane is Plane.XZ:
        # Get z-axis perpendicular to plane of circle (can be any)
        z_axis = numpy.cross(veca, vecb)
        z_axis[2] = abs(z_axis[2])
        z_len = numpy.sqrt(numpy.sum(z_axis ** 2))
    elif plane is Plane.FREE:
        # Get z-axis perpendicular to plane of circle (can be any)
        z_axis = numpy.cross(veca, vecb)
        z_axis[2] = abs(z_axis[2])

        z_len = numpy.sqrt(numpy.sum(z_axis ** 2))

        # Normalise z-axis, fallback to preferred plane if angle is 180°
        if z_len != 0:
            z_axis = z_axis / z_len
        else:
            try:
                assert numpy.dot(normal_vec, veca) == 0 and numpy.dot(normal_vec, vecb)
            except TypeError:
                raise ValueError("Normal vector must be supplied if vectors are collinear.")
            except AssertionError:
                raise ValueError("Normal vector supplied is not normal to circle.")
            else:
                z_axis = normal_vec
    else:
        raise UnknownPlaneError

    # Normal vector of any circle can be tilted in two directions but does not need to be twisted
    # TODO Consider z axis parallel y axis
    y_axis_r = numpy.array([0, 1, 0])
    x_axis = numpy.cross(y_axis_r, z_axis)
    # Get corresponding y-axis for right-hand system
    y_axis = numpy.cross(z_axis, x_axis)
    y_axis = y_axis / numpy.sqrt(numpy.sum(y_axis ** 2))

    return x_axis, y_axis, z_axis


def get_np_vectors(start: Coordinate, target: Coordinate, center: Coordinate, normal_vec: Coordinate):
    # Get vectors from center
    cs = start - center
    ct = target - center

    # Convert to numpy arrays
    veca = numpy.array(list(cs.coordinate.values()))
    vecb = numpy.array(list(ct.coordinate.values()))

    if normal_vec is not None:
        normal_vec = numpy.array(normal_vec.coordinate.values())

    return normal_vec, veca, vecb


def project_vector(vec, *axes):
    proj = []
    for axis in axes:
        proj.append(numpy.dot(axis, vec))
    return proj


def get_angle(start: Coordinate, target: Coordinate, center: Coordinate, plane: Plane,
              normal_vec: Union[Coordinate, None] = None) -> float:
    if normal_vec is not None:
        normal_vec.reduce_to_axes('XYZ')
    start.reduce_to_axes('XYZ')
    target.reduce_to_axes('XYZ')
    center.reduce_to_axes('XYZ')

    normal_vec, veca, vecb = get_np_vectors(start, target, center, normal_vec)

    # Get the new coordinate system
    x_axis_c, y_axis_c, _ = get_circle_cs(veca, vecb, plane, normal_vec)

    # Projections onto a and y axis
    x_b, y_b = project_vector(vecb, x_axis_c, y_axis_c)
    x_a, y_a = project_vector(veca, x_axis_c, y_axis_c)

    # Get the angle
    return atan2(y_b, x_b) - atan2(y_a, x_a)


def get_intermediate_points(angle: float, start: Coordinate, target: Coordinate, center: Coordinate,
                            plane: Plane, normal_vec: Union[Coordinate, None] = None) -> Coordinate:
    # Point in the middle of start and target on a direct line
    middle = 0.5 * (target - start) + start
    cm = middle - center

    # todo Full circle
    if abs(angle) == 2 * pi:
        # Get second intermediate point
        sc = center - start
        i2 = sc + center

        # Recursive call
        # i1 = get_intermediate_points(angle / 2, start, i2, center, plane, normal_vec)[0]
        # i3 = get_intermediate_points(angle / 2, i2, target, center, plane, normal_vec)[0]

        # Compose all intermediate points
        # intermediate = [i1, i2, i3]
        if angle < 0:
            pass
            # intermediate.reverse()
    # Half circle
    elif abs(angle) == pi:
        # TODO Consider planes
        normal_r = (target - center).cross(normal_vec)
        if angle < 0:
            normal_r *= -1
        intermediate = center + normal_r
    else:
        cm_rescaled = cm / (cm.vector_len()) * (center - start).vector_len()
        if pi > abs(angle) > 0:
            intermediate = center + cm_rescaled
        elif pi < abs(angle) < 2 * pi:
            intermediate = center - cm_rescaled
        else:
            raise NotImplementedError
    return intermediate