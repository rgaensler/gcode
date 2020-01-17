import time

from AM_IR import ApplicationExceptions
from AM_IR.Coordinate import Coordinate
from AM_IR.printer_components.MelfaRobot import MelfaRobot
from AM_IR.melfa.TcpClientR3 import TcpClientR3
from AM_IR.speed_profile import draw_speed


def cube(robot: MelfaRobot, speed: float) -> None:
    """
    Demo Example 1 - Cube
    :param robot: Instance of an active robot
    :param speed:
    :return:
    """
    # Base coordinates
    z_vector = Coordinate([0, 0, 5, 0, 0, 0], robot.AXES)
    square_corners = [
        Coordinate([500, 50, 200, 180, 0, 0], robot.AXES),
        Coordinate([500, -50, 200, 180, 0, 0], robot.AXES),
        Coordinate([600, -50, 200, 180, 0, 0], robot.AXES),
        Coordinate([600, 50, 200, 180, 0, 0], robot.AXES)
    ]

    # Go to points
    for _ in range(10):
        # Square
        for point in square_corners:
            robot.linear_move_poll(point, speed)
        # Back to first point
        robot.linear_move_poll(square_corners[0], speed)
        # Increment z
        square_corners = [point + z_vector for point in square_corners]


def cylinder(robot: MelfaRobot, speed: float) -> None:
    """
    Demo Example 2 - Cylinder
    :param robot: Instance of an active robot
    :param speed:
    :return:
    """
    # Base coordinates
    z_vector = Coordinate([0, 0, 15, 0, 0, 0], robot.AXES)
    start = Coordinate([500, 0, 200, 180, 0, 0], robot.AXES)
    target = Coordinate([550, 50, 200, 180, 0, 0], robot.AXES)
    center = Coordinate([550, 0, 200, 180, 0, 0], robot.AXES)
    clockwise = False

    for _ in range(10):
        # Move circle segment
        robot.circular_move_poll(target, center, clockwise, speed, start_pos=start)

        # Increase height and swap start and target
        start, target = target + z_vector, start + z_vector
        center += z_vector
        clockwise = not clockwise


def speed_test(robot: MelfaRobot, speed: float) -> None:
    start = Coordinate([350, -200, 600, 180, 0, 0], robot.AXES)
    vector = Coordinate([200, 400, -300, 0, 0, 0], robot.AXES)
    finish = start + vector

    # Back to start
    robot.reset_speed_factors()
    robot.linear_move_poll(start)

    # Test distance
    start_time = time.clock()
    t, v = robot.linear_move_poll(finish, speed, track_speed=True)
    finish_time = time.clock()

    # Average velocity
    velocity = vector.vector_len() / (finish_time - start_time)

    # Draw speed
    draw_speed(speed, t, v)

    print("Velocity is: " + str(velocity))


def demo_mode(ip=None, port=None, safe_return=False) -> None:
    # Create TCP client
    if ip is not None and port is not None:
        tcp_client = TcpClientR3(host=ip, port=port)
    else:
        tcp_client = TcpClientR3()
    tcp_client.connect()

    # Executing communication
    robot = MelfaRobot(tcp_client, number_axes=6, speed_threshold=10, safe_return=safe_return)
    robot.boot()
    try:
        while True:
            selection = input("Please choose a mode (1=cube, 2=cylinder, 3=speed test): ")
            try:
                if selection == '1':
                    speed = float(input("Please enter the speed (linear: mm/s): "))
                    cube(robot, speed)
                elif selection == '2':
                    speed = float(input("Please enter the speed (linear: mm/s): "))
                    cylinder(robot, speed)
                elif selection == '3':
                    speed = float(input("Please enter the speed (linear: mm/s): "))
                    speed_test(robot, speed)
                else:
                    break
            except ValueError:
                break
    except KeyboardInterrupt:
        pass
    except NotImplementedError:
        pass
    except ApplicationExceptions.MelfaBaseException as e:
        print(str(e))
    finally:
        # Cleaning up
        robot.shutdown()