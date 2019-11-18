import MelfaCmd
from time import sleep

from Coordinate import Coordinate
from TcpClientR3 import TcpClientR3
from typing import *

from refactor import cmp_response


class MelfaRobot(object):
    """
    Class representing the physical robots with its unique routines, properties and actions.
    """
    axes = 'XYZABC'

    def __init__(self, tcp_client, number_axes: int = 6):
        """
        Initialises the robot.
        :param tcp_client: Communication object for TCP/IP-protocol
        :param number_axes: Number of robot axes, declared by 'J[n]', n>=1
        """
        if not hasattr(tcp_client, 'send') or not hasattr(tcp_client, 'receive'):
            raise TypeError('TCP-client does not implement required methods.')
        if not number_axes > 0:
            raise TypeError('Illegal number of axes.')

        self.tcp: TcpClientR3 = tcp_client
        self.joints: Iterable[AnyStr] = set(['J' + str(i) for i in range(1, number_axes + 1)])
        self.servo: bool = False
        self.com_ctrl: bool = False

    # Administration functions
    def start(self, safe_return: bool = True) -> None:
        """
        Starts the robot and initialises it.
        :param safe_return: Flag, whether the robot should return to its safe position
        :return: None
        """
        # Communication & Control on
        self.change_communication_state(True)
        # Servos on
        self.change_servo_state(True)
        # Safe position
        if safe_return:
            self.go_safe_pos()

    def shutdown(self, safe_return: bool = True) -> None:
        """
        Safely shuts down the robot.
        :param safe_return: Flag, whether the robot should return to its safe position
        :return: None
        """
        # Safe position
        if safe_return:
            self.go_safe_pos()
        # Servos off
        self.change_servo_state(False)
        # Communication & Control off
        self.change_communication_state(False)

    def maintenance(self):
        # Communication & Control on
        self.change_communication_state(True)

    # Utility functions
    def change_communication_state(self, activate: bool) -> None:
        """
        Obtain/release communication and control.
        :param activate: Boolean
        :return: None
        """
        if activate:
            # Open communication and obtain control
            self.tcp.send(MelfaCmd.COM_OPEN)
            self.tcp.receive()
            self.tcp.send(MelfaCmd.CNTL_ON)
            self.tcp.receive()
        else:
            # Open communication and obtain control
            self.tcp.send(MelfaCmd.CNTL_OFF)
            self.tcp.receive()
            self.tcp.send(MelfaCmd.COM_CLOSE)
            self.tcp.receive()

        self.com_ctrl = activate

    def change_servo_state(self, activate: bool) -> None:
        """
        Switch the servos on/off.
        :param activate: Boolean
        :return: None
        """
        if activate:
            self.tcp.send(MelfaCmd.SRV_ON)
            self.tcp.receive()
        else:
            self.tcp.send(MelfaCmd.SRV_OFF)
            self.tcp.receive()

        # Wait for servos to finish
        sleep(MelfaCmd.SERVO_INIT_SEC)
        self.servo = activate

    def read_parameter(self, parameter: AnyStr):
        self.tcp.send(MelfaCmd.PARAMETER_READ + parameter)
        response = self.tcp.receive()
        return response

    # Speed functions
    def set_speed_factors(self, factor):
        """
        Set the speed modification factors for joint and interpolation movement.
        :param factor:
        :return:
        """
        pass

    def reset_speed_factors(self):
        """
        Reset the speed modification factors to maximum speed.
        :return:
        """
        # TODO Check whether OVRD can be set as well
        pass

    # Movement functions
    def go_safe_pos(self) -> None:
        """
        Moves the robot to its safe position.
        :return:
        """
        # Read safe position
        self.tcp.send(MelfaCmd.PARAMETER_READ + MelfaCmd.PARAMETER_SAFE_POSITION)
        safe_pos = self.tcp.receive()
        safe_pos_values = [float(i) for i in safe_pos.split(';')[1].split(', ')]
        safe_pos = Coordinate(safe_pos_values, self.joints)

        # Return to safe position
        self.tcp.send(MelfaCmd.MOVE_SAFE_POSITION)
        self.tcp.receive()

        # Wait until position is reached
        cmp_response(MelfaCmd.CURRENT_JOINT, safe_pos.to_melfa_response(), self.tcp)

    def linear_move_poll(self, target_pos: Coordinate, speed: float) -> None:
        """
        Moves the robot linearly to a coordinate.
        :param target_pos: Coordinate for the target position.
        :param speed: Movement speed for tool.
        :return:
        """
        # TODO Set speed accordingly

        # Send move command
        self.tcp.send(MelfaCmd.LINEAR_INTRP + target_pos.to_melfa_point())
        self.tcp.receive()

        # Wait until position is reached
        cmp_response(MelfaCmd.CURRENT_XYZABC, target_pos.to_melfa_response(), self.tcp)

    def circular_move_poll(self, target_pos: Coordinate, center_pos: Coordinate, is_clockwise: bool,
                           speed: float) -> None:
        """
        Moves the robot on a (counter-)clockwise arc around a center position to a target position.
        :param target_pos: Coordinate for the target position.
        :param center_pos: Coordinate for the center of the arc.
        :param is_clockwise: Flag to indicate clockwise|counter-clockwise direction.
        :param speed: Movement speed for tool.
        :return:
        """
        # TODO Set speed accordingly

        # Set direct/indirect movement flag
        if is_clockwise:
            pass
        else:
            pass

        # TODO Send move command with coordinates and direct/indirect flag
        self.tcp.send(MelfaCmd.CIRCULAR_INTRP)

        # Wait until position is reached
        cmp_response(MelfaCmd.CURRENT_XYZABC, target_pos.to_melfa_response(), self.tcp)