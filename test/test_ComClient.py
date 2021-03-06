import os
import sys
import unittest.mock as mock
from time import sleep

import pytest
import serial.tools.list_ports

import src.clients.IClient as IClient
from src.clients.ComClient import ComClient, validate_id
from src.clients.SerialEcho import ConfigurableEcho
from src.clients.TcpEchoServer import DummyRobotController
from src.GCmd import GCmd
from src.printer_components.GPrinter import GPrinter


@pytest.fixture(
    params=[
        pytest.param(
            ('ids', 0x0403, 0x6001),
            marks=pytest.mark.slow
        ),
        pytest.param(
            # On Windows Test Systems com0com should be installed to use virtual ports COM5 and COM6
            ('port', 'COM5', 'COM6'),
            marks=pytest.mark.skipif(sys.platform != 'win32', reason='com0com required')
        ),
        pytest.param(
            ('port', 'ttyV0', 'ttyV1'),
            marks=pytest.mark.skipif(os.system('socat -h') != 0, reason='socat required')
        )
    ],
    ids=[
        'Physical Hardware',
        'Virtual Ports (Windows)',
        'Virtual Ports (Linux)'
    ]
)
def valid_com_client(request):
    # Parameterizable COM client
    if request.param[0] == 'ids':
        # Client is identified by USB Vendor ID and Product ID (physical hardware)
        com = ComClient(ids=request.param[1:])
        if com.is_available():
            yield com
        else:
            pytest.skip('Physical device is not available.')
    elif request.param[0] == 'port':
        # Validate ports first
        if sys.platform == 'win32':
            # Windows platform using com0com
            echo_valid = validate_virtual_port_win(request.param[1])
            client_valid = validate_virtual_port_win(request.param[2])

            if not echo_valid or not client_valid:
                pytest.skip('Configured ports for windows where either not present or not virtual.')

        # Client is identified by port name (virtual ports)
        with ConfigurableEcho(port=request.param[1]) as echo:
            echo.reconfigure(post='ok\n', msg='')
            yield ComClient(port=request.param[2])


@pytest.fixture
def duplicate_com_client():
    return ComClient((0x0001, 0x0001))


@pytest.fixture
def non_existing_com_client():
    return ComClient((-1, -1))


def validate_virtual_port_win(port_name) -> bool:
    """
    Ensure that a virtual port is present and has com0com signature.
    :param port_name: String of the port name to be checked
    :return: Flag to indicate whether the specified port is valid.
    """
    for device in serial.tools.list_ports.comports():
        if port_name == device.device and 'com0com' in device.description:
            return True
    return False


class TestComClient:
    """
    Tests for the client layer in case of using a COM client
    """

    def test_connect_client_not_found(self, non_existing_com_client):
        """
        Test that an exception if raised in case the client cannot be found.
        :param non_existing_com_client:
        :return: None
        """
        with pytest.raises(IClient.ClientNotAvailableError):
            with non_existing_com_client:
                pass

    def test_connect_twice(self, valid_com_client):
        """
        Test that an exception is raised on subsequent connection attempts.
        :param valid_com_client: Fixture object for an available client.
        :return: None
        """
        with valid_com_client:
            with pytest.raises(IClient.ClientOpenError):
                # Second try should not work
                valid_com_client.connect()

    def test_connect_duplicate(self, duplicate_com_client):
        """
        Test that an exception is raised if multiple devices are found
        :param duplicate_com_client: Fixture object for an available client.
        :return: None
        """
        # This implementation is strongly tied to the list ports functionality but rather unlikely to ever change
        with mock.patch('serial.tools.list_ports.comports') as mockfunc:
            # Create some fake devices
            fake_device = mock.MagicMock()
            fake_device.pid = duplicate_com_client.pid
            fake_device.vid = duplicate_com_client.vid

            # Create an arbitrary device that is not searched for connection
            fake_device_2 = mock.MagicMock()
            fake_device_2.pid = duplicate_com_client.pid + 1
            fake_device_2.vid = duplicate_com_client.vid + 1

            # Check that duplicate clients are reported
            mockfunc.return_value = [fake_device, fake_device_2, fake_device]
            with pytest.raises(IClient.AmbiguousHardwareError):
                try:
                    duplicate_com_client.connect()
                finally:
                    duplicate_com_client.close()

            # Validate that the mock is working as expected
            mockfunc.return_value = [fake_device_2]
            with pytest.raises(IClient.ClientNotAvailableError):
                try:
                    duplicate_com_client.connect()
                finally:
                    duplicate_com_client.close()

    def test_close_without_open(self, valid_com_client, non_existing_com_client):
        """
        Test that repeatedly closing does not cause an issue.
        :param valid_com_client:
        :return:
        """
        valid_com_client.close()
        non_existing_com_client.close()

    @pytest.mark.timeout(20)
    def test_receive(self, valid_com_client):
        # Responses can be received
        with valid_com_client:
            valid_com_client.send('M114')
            response = valid_com_client.receive()
            print(f'Response: {response}')
            assert 'ok' in response

        # Receiving is not possible afterwards
        with pytest.raises(IClient.ClientError):
            valid_com_client.receive()

    @pytest.mark.timeout(30)
    def test_send(self, valid_com_client):
        # Mock out this annoying wait for startup message
        valid_com_client.hook_post_successful_connect = mock.Mock()
        msg = 'M105'

        with valid_com_client:
            # This time it should not be logged
            valid_com_client.send(msg, silent_send=True)
            sleep(1)

            # This time it should be logged somehow
            valid_com_client.send(msg, silent_send=False)
            sleep(10)

    def test_is_available_not(self, non_existing_com_client):
        """
        Test that for a non existing COM client the result is not available.
        :param non_existing_com_client:
        :return: None
        """
        assert not non_existing_com_client.is_available()

    def test_is_available(self, valid_com_client):
        """
        Test that the valid COM client is available.
        :param valid_com_client:
        :return: None
        """
        assert valid_com_client.is_available()


@pytest.mark.parametrize("value,valid", [(0, True), (-1, False), (2 ** 16 - 1, True), (2 ** 16, False)])
def test_validate_id(value, valid):
    assert validate_id(value) == valid


ROBOT_IP, ROBOT_PORT = 'localhost', 10010


@pytest.fixture
def virtual_environ(dummy_robot_controller, valid_com_client):
    # Starting up server as dummy for printer
    with dummy_robot_controller:
        serial_ids = (valid_com_client.vid, valid_com_client.pid,)
        serial_port = valid_com_client.port
        printer = GPrinter.default_init(ROBOT_IP, ROBOT_PORT, serial_ids=serial_ids, serial_port=serial_port)
        dummy_robot_controller.response_lookup[b'1;1;VALM_SVO'] = b'M_SVO=+0'
        yield printer, dummy_robot_controller


@pytest.fixture
def dummy_robot_controller():
    dummy = DummyRobotController(ROBOT_IP, ROBOT_PORT, 'utf-8')
    dummy.response_lookup[b'1;1;OVRD'] = b'10'
    dummy.response_lookup[b'1;1;VALM_SVO'] = b'M_SVO=+1'
    dummy.reconfigure(pre='QoK')
    return dummy


class TestGPrinter:
    @pytest.mark.parametrize('cmd_str', ['G91', 'G20', 'G21', 'G222'])
    def test_execute(self, virtual_environ, cmd_str):
        """
        Test that commands are sent to all corresponding components
        :return:
        """
        printer, dummy_robot_ctrl = virtual_environ
        cmd = GCmd.read_cmd_str(cmd_str)
        printer.execute(cmd)
        printer.shutdown()
