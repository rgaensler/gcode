from enum import unique, Enum
from typing import Optional

from src.Coordinate import Coordinate


@unique
class Plane(Enum):
    """
    Define enums for each available plane.
    """

    XY = 1
    XZ = 2
    YZ = 3
    ANY = 4


class MelfaCoordinateService:
    @staticmethod
    def from_response(melfa_str: str, number_axes: int) -> Coordinate:
        segments = melfa_str.split(";")
        values = [float(i) for i in segments[1: 2 * number_axes: 2]]
        axes = segments[0: 2 * number_axes: 2]
        return Coordinate(values, axes)

    @staticmethod
    def to_cmd(c: Coordinate, pose_flag: Optional[int] = 7):
        """
        Convert a coordinate to the point format used in R3 protocol
        :param c:
        :param pose_flag:
        :return:
        """
        txt = ("{:.{d}f}".format(i, d=c.digits) if i is not None else "" for i in c.values)
        return f'({",".join(txt)}) ({pose_flag},0)'
