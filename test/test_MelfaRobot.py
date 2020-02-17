import unittest.mock as mock
from unittest.mock import MagicMock

import pytest

from src.ApplicationExceptions import MelfaBaseException
from src.melfa import MelfaCmd
from src.melfa.TcpClientR3 import TcpClientR3
from src.printer_components.MelfaRobot import MelfaRobot, IllegalAxesCount, SpeedBelowMinimum


@pytest.fixture
def tcp():
    a = MagicMock()
    a.mock_add_spec(TcpClientR3())
    return a


@pytest.fixture
def safe_robot(tcp):
    """
    Test ressource with safe point return activated.
    :param tcp:
    :return:
    """
    return MelfaRobot(tcp, safe_return=True)


@pytest.fixture
def no_safe_robot(tcp):
    """
    Test ressource with safe point return deactivated.
    :param tcp:
    :return:
    """
    return MelfaRobot(tcp, safe_return=False)


class TestMelfaRobot:
    def test_axes_init(self, tcp):
        with pytest.raises(IllegalAxesCount):
            MelfaRobot(tcp, number_axes=0)

        a = MelfaRobot(tcp, number_axes=1)
        assert a.joints == ['J1']

        b = MelfaRobot(tcp, number_axes=2)
        assert b.joints == ['J1', 'J2']

    def test_boot_no_safe(self, no_safe_robot):
        """
        Test that for no safe config the safe return is not called during booting.
        :param no_safe_robot:
        :return:
        """
        with mock.patch.object(no_safe_robot, 'go_safe_pos', autospec=True) as mock_func:
            with mock.patch('src.printer_components.MelfaRobot.sleep', return_value=None):
                no_safe_robot.boot()
        assert not mock_func.called

    def test_boot_safe(self, safe_robot):
        """
        Test that for safe config the safe return is called during booting.
        :param safe_robot:
        :return:
        """
        with mock.patch.object(safe_robot, 'go_safe_pos', autospec=True) as mock_func:
            with mock.patch('src.printer_components.MelfaRobot.sleep', return_value=None):
                safe_robot.boot()
        assert mock_func.called

    def test_shutdown_no_safe(self, no_safe_robot):
        """
        Test that for no safe config the safe return is not called during shutdown.
        :param no_safe_robot:
        :return:
        """
        with mock.patch.object(no_safe_robot, 'go_safe_pos', autospec=True) as mock_func:
            no_safe_robot.shutdown()
        assert not mock_func.called

    def test_shutdown_safe(self, safe_robot):
        """
        Test that for safe config the safe return is called during shutdown.
        :param safe_robot:
        :return:
        """
        with mock.patch.object(safe_robot, 'go_safe_pos', autospec=True) as mock_func:
            with mock.patch('src.printer_components.MelfaRobot.sleep', return_value=None):
                safe_robot.shutdown()
        assert mock_func.called

    def test_activate_work_coordinate(self, no_safe_robot):
        """
        Test that the state variable can be changed accordingly and that the correct commands are delegated/not
        delegated to the tcp.
        :param no_safe_robot:
        :return:
        """
        # Activate
        with mock.patch.object(no_safe_robot.tcp, 'send', spec=mock.Mock()) as mock_func:
            no_safe_robot.activate_work_coordinate(True)
        assert no_safe_robot.work_coordinate_active
        # TODO Decouple this test from the implementation of zero
        mock_func.assert_any_call(MelfaCmd.SET_BASE_COORDINATES + "(-500,0,-250,0,0,0)")

        # Deactivate
        with mock.patch.object(no_safe_robot.tcp, 'send', spec=mock.Mock()) as mock_func:
            no_safe_robot.activate_work_coordinate(False)
        assert not no_safe_robot.work_coordinate_active
        mock_func.assert_any_call(MelfaCmd.RESET_BASE_COORDINATES)

    def test_handle_gcode(self):
        assert True

    def test__prepare_circle(self):
        assert True

    def test_maintenance(self):
        assert True

    def test__change_communication_state(self, no_safe_robot):
        """
        Test that the state variable can be changed accordingly and that the correct commands are delegated/not
        delegated to the tcp.
        :param no_safe_robot:
        :return:
        """
        # Activate
        with mock.patch.object(no_safe_robot.tcp, 'send', spec=mock.Mock()) as mock_func:
            no_safe_robot._change_communication_state(True)
        assert no_safe_robot.com_ctrl
        mock_func.assert_any_call(MelfaCmd.CNTL_ON)
        with pytest.raises(AssertionError):
            mock_func.assert_any_call(MelfaCmd.CNTL_OFF)

        # Deactivate
        with mock.patch.object(no_safe_robot.tcp, 'send', spec=mock.Mock()) as mock_func:
            no_safe_robot._change_communication_state(False)
        assert not no_safe_robot.servo
        mock_func.assert_any_call(MelfaCmd.CNTL_OFF)
        with pytest.raises(AssertionError):
            mock_func.assert_any_call(MelfaCmd.CNTL_ON)

    def test__change_servo_state(self, no_safe_robot):
        """
        Test that the state variable can be changed accordingly and that the correct commands are delegated/not
        delegated to the tcp.
        :param no_safe_robot:
        :return:
        """
        with mock.patch('src.printer_components.MelfaRobot.sleep', return_value=None):
            # Activate
            with mock.patch.object(no_safe_robot.tcp, 'send', spec=mock.Mock()) as mock_func:
                no_safe_robot._change_servo_state(True)
            assert no_safe_robot.servo
            mock_func.assert_any_call(MelfaCmd.SRV_ON)
            with pytest.raises(AssertionError):
                mock_func.assert_any_call(MelfaCmd.SRV_OFF)

            # Deactivate
            with mock.patch.object(no_safe_robot.tcp, 'send', spec=mock.Mock()) as mock_func:
                no_safe_robot._change_servo_state(False)
            assert not no_safe_robot.servo
            mock_func.assert_any_call(MelfaCmd.SRV_OFF)
            with pytest.raises(AssertionError):
                mock_func.assert_any_call(MelfaCmd.SRV_ON)

    def test_read_parameter(self):
        assert True

    def test_set_speed(self, no_safe_robot):
        """
        Check that the speed commands are sent as expected.
        :param no_safe_robot:
        :return:
        """
        with mock.patch.object(no_safe_robot, '_get_ovrd_speed') as ovrd:
            # Error
            with pytest.raises(SpeedBelowMinimum):
                no_safe_robot.set_speed(0, 'linear')

            # Regular setting
            ovrd.return_value = 100
            with mock.patch.object(no_safe_robot.tcp, 'send', spec=mock.Mock()) as mock_func:
                no_safe_robot.set_speed(1, 'linear')
            mock_func.assert_called_with(MelfaCmd.MVS_SPEED + '1.00')

            # Regular setting with different override
            ovrd.return_value = 30
            with mock.patch.object(no_safe_robot.tcp, 'send', spec=mock.Mock()) as mock_func:
                no_safe_robot.set_speed(12, 'linear')
            mock_func.assert_called_with(MelfaCmd.MVS_SPEED + '40.00')

    def test_reset_linear_speed_factor(self):
        assert True

    def test_go_home(self):
        assert True

    def test_go_safe_pos(self):
        assert True

    def test_linear_move_poll(self):
        assert True

    def test_circular_move_poll(self):
        assert True

    def test_set_global_positions(self):
        assert True

    def test_get_pos(self):
        assert True

    def test__check_speed_threshold(self):
        assert True

    def test__get_ovrd(self):
        assert True

    def test__set_ovrd_speed_false(self, no_safe_robot):
        with pytest.raises(MelfaBaseException):
            no_safe_robot._set_ovrd(101)
        with pytest.raises(MelfaBaseException):
            no_safe_robot._set_ovrd(0)

    @pytest.mark.parametrize("factor", [1, 53, 100])
    def test__set_ovrd_speed_okay(self, factor, no_safe_robot):
        with mock.patch.object(no_safe_robot.tcp, 'send', spec=mock.Mock()) as mock_func:
            no_safe_robot._set_ovrd(factor)
        mock_func.assert_called_with(MelfaCmd.OVERRIDE_CMD + "=" + str(factor))

    def test_wait(self):
        assert True

    def test__zero(self):
        assert True
