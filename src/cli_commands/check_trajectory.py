import sys
from configparser import ConfigParser
from typing import Optional

from src.clients.TcpClientR3 import TcpClientR3
from src.exit_codes import EXIT_INVALID_TRAJECTORY
from src.gcode.GCmd import GCmd
from src.prechecks.configs import melfa_rv_4a
from src.prechecks.exceptions import CartesianLimitViolation, ConfigurationChangesError
from src.prechecks.prechecks import Constraints, check_traj
from src.protocols.R3Protocol import R3Protocol


def check_trajectory(config_f='./../config.ini', gcode_f='./../test.gcode', ip: Optional[str] = None,
                     port: Optional[int] = 0):
    """
    Validate a trajectory for a given robot setup.
    :param config_f: File path for the configuration file
    :param gcode_f: File path for the input G-Code file
    :param ip: Optional host address to be used to resolve robot parameters directly
    :param port: Optional port to be used to resolve robot parameters directly
    :return:
    """
    with open(gcode_f, 'r') as f:
        cmd_raw = f.readlines()

    commands = [GCmd.read_cmd_str(cmd_str.strip()) for cmd_str in cmd_raw]
    robot_config = melfa_rv_4a()

    config_parser = ConfigParser()
    config_parser.read(config_f)

    if ip is not None:
        # Parameters can be read from the robot
        tcp_client = TcpClientR3(host=ip, port=port)
        # TODO Configure setup for reading parameters from robot correctly
        protocol = R3Protocol(tcp_client)
        home_position = protocol.get_safe_pos().values
        cartesian_limits = protocol.get_xyz_borders()
        joint_limits = protocol.get_joint_borders()
    else:
        # Parameters that need to be configured in the config file if they are not read from the robot
        home_pos_str = config_parser.get('prechecks', 'home_joints')
        home_position = [float(i) for i in home_pos_str.split(', ')]
        cartesian_limits_str = config_parser.get('prechecks', 'xyz_limits')
        cartesian_limits = [float(i) for i in cartesian_limits_str.split(', ')]
        joint_limits_str = config_parser.get('prechecks', 'joint_limits')
        joint_limits = [float(i) for i in joint_limits_str.split(', ')]

    # Parameters that always need to be configured within the config file
    max_jnt_speed = config_parser.get('prechecks', 'max_joint_speed')
    joint_velocity_limits = [float(i) for i in max_jnt_speed.split(', ')]
    inc_distance_mm = float(config_parser.get('prechecks', 'ds_mm'))
    urdf_file_path = config_parser.get('prechecks', 'urdf_path')
    default_acc = float(config_parser.get('prechecks', 'default_acc'))

    # Create the constraints
    traj_constraint = Constraints(cartesian_limits, joint_limits, joint_velocity_limits)

    try:
        # Check the trajectory
        check_traj(commands, robot_config, traj_constraint, home_position, inc_distance_mm, default_acc, urdf_file_path)
    except CartesianLimitViolation as e:
        print('Fatal error occured: {}'.format("\n".join(e.args)))
        print('Please verify that the limits are correct and check the positioning of the part.')
        sys.exit(EXIT_INVALID_TRAJECTORY)
    except ConfigurationChangesError as e:
        raise NotImplementedError from e