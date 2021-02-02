import logging
from time import sleep, time
from typing import Tuple, Optional

import serial
import serial.tools.list_ports
from serial import SerialException

from src.clients.ThreadedClient import ThreadedClient
from src.clients.IClient import ClientNotAvailableError, ClientOpenError, AmbiguousHardwareError


def validate_id(id_number: int) -> bool:
    """
    Validates the USB IDs individually.
    :param id_number: Can be any of vendor ID or product ID.
    :return: Flag to indicate whether the ID is valid.
    """
    return 0 <= id_number < 65536


class ComClient(ThreadedClient):
    """
    Implements a reusable client side for serial communication.
    """

    BAUD_RATE = 250000
    BOOT_TIME_SECONDS = 8.0
    MAX_TIME_WITHOUT_NEW_BIT = 5.0
    PARITY = serial.PARITY_NONE
    STOP_BIT = serial.STOPBITS_ONE
    BYTE_SIZE = serial.EIGHTBITS
    DEFAULT_WRITE_ENCODING = 'ascii'
    DEFAULT_READ_ENCODING = 'utf-8'

    def __init__(self, ids: Optional[Tuple[int, int]] = None, encodings: Tuple[str, str] = None, baud=BAUD_RATE,
                 parity=PARITY, stopbits=STOP_BIT, byte=BYTE_SIZE, port: str = None):
        """
        Create a client for the serial communication.

        :param ids: Tuple, containing vendor id and product id to be used for device identification.
                    Both IDs are usually 16-bit integers.
        :param encodings: Encoding to be used for data transformations, defaults to ASCII (write) | UTF-8 (read).
        :param baud: Baudrate to be used for the communication, defaults to 115200.
        :param parity: Paritiy bit, defaults to none.
        :param stopbits: Number of stop bits, defaults to one.
        :param byte: Byte size, defaults to eight bits.
        :param port: Pass the actual port if it is known and static.
        :raises: ValueError if the IDs cannot be converted to int.
        """
        # Get features of threaded client
        super().__init__(kind='Serial')

        # Serial port parameters (blocking)
        self._ser = serial.Serial(baudrate=baud, parity=parity, stopbits=stopbits, bytesize=byte, dsrdtr=None)
        self.port = port
        self.send_encoding, self.read_encoding = encodings or (self.DEFAULT_WRITE_ENCODING, self.DEFAULT_READ_ENCODING)
        self.terminator = '\n'
        self.buffer = bytes()

        # Unpack and transform IDs (port has precedence)
        if self.port is None:
            self.vid, self.pid = map(int, ids)
        else:
            if ids is None:
                self.vid, self.pid = None, None
            else:
                self.vid, self.pid = ids

    def hook_thread_name(self) -> Optional[str]:
        """
        Client-specific thread-naming. Can be overriden. Defaults to standard thread naming.
        :return: Thread name mentioning the port and the client type
        """
        return f'Serial Client ({self._ser.port})'

    def hook_pre_connect(self) -> None:
        """
        Identify the port to be used.
        :return: None
        """
        # Choose manner of port identification
        if self.port is not None:
            self._ser.setPort(self.port)
            logging.info(f'Attempting connection to port {self.port}...')
        else:
            self._resolve_ids()

    def hook_connect(self) -> Optional[str]:
        """
        Attempt to open the serial port connected to the device.
        :return: None
        :raises: ClientOpenError if there was any error while opening the port, e.g. port already open
        """
        # Attempt to open the port
        try:
            self._ser.open()
            return self._ser.port
        except serial.SerialException as e:
            print(e)
            raise ClientOpenError(e) from e

    def hook_post_successful_connect(self) -> None:
        """
        Ensure that the hardware is setup right after connection was established.
        :return: None
        :raises: ClientOpenError if an error occurred or the startup message is not as expected.
        """
        # Wait for device to start up (measured was ~5.5 seconds)
        sleep(self.BOOT_TIME_SECONDS)

        if self._ser.in_waiting > 0:
            # Attempt to read the current byte buffer
            try:
                startup_message = self._ser.read_all()
                startup_message = startup_message.decode(encoding=self.read_encoding)
            except serial.SerialException as e:
                raise ClientOpenError from e

            # Verify message
            if startup_message.endswith(self.terminator):
                logging.info('Startup message:')
                for line in startup_message.split(self.terminator):
                    logging.info(line)
            else:
                raise ClientOpenError('Message was not terminated correctly.')

    def _resolve_ids(self) -> None:
        """
        Attempts to find the correct device by given PID and VID. On success the serial port is configured accordingly.
        :return: None
        :raises: AmbiguousHardwareError if multiple devices have the same VID:PID.
        :raises ClientNotAvailableError if the specified VID:PID was not found.
        """
        # Search for ports matching the desired IDs
        matches = [usb for usb in serial.tools.list_ports.comports() if usb.vid == self.vid and usb.pid == self.pid]
        # Cases ordered by estimated occurence
        if len(matches) == 0:
            # Could not find desired client
            raise ClientNotAvailableError(self.vid, self.pid)
        if len(matches) == 1:
            # Configure the serial port accordingly
            self._ser.port = matches[0].device
            logging.info(f'Attempting connection to {matches[0].description} - {matches[0].hwid}...')
        else:
            # Found multiple clients
            raise AmbiguousHardwareError

    def hook_close(self) -> None:
        """
        Close the serial port.
        :return: None
        """
        # Client specific closing
        self._ser.close()

    def hook_handle_msg(self, msg: str) -> str:
        """
        Hook for execution in the worker thread for each message queued.
        :param msg: Message string to be sent
        :return: Response string
        """
        self.serial_send(msg)
        return self._receive()

    def _receive(self) -> str:
        """
        Receive data sent on the serial port.
        :return: Message string
        :raises:
        """
        response = ''

        got_terminator = False
        terminators = [b'ok\n', b'//action:disconnect\n', b'action:disconnect\n', b'Thermal Runaway Protection Reset\n']

        t0 = time()
        initial_bits = len(self.buffer)

        # Wait for timeout or terminator
        while not got_terminator:
            # Update bit count
            if len(self.buffer) != initial_bits:
                initial_bits = len(self.buffer)
                t0 = time()

            try:
                # Attempt to read new bits
                self.buffer += self._ser.read_all()
            except SerialException as e:
                logging.error(e)

            # Check terminators
            for term in terminators:
                idx = self.buffer.find(term)
                if idx > -1:
                    response = self.buffer[:idx + 1 + len(term)].decode(encoding=self.read_encoding)
                    self.buffer = self.buffer[idx + 2:]
                    got_terminator = True

            # Check timeout
            if time() - t0 > self.MAX_TIME_WITHOUT_NEW_BIT:
                # Timeout occurred
                response = self.buffer.decode(encoding=self.read_encoding)
                self.buffer = bytes()
                break

        return response

    def serial_send(self, msg: str):
        """
        Sends data on the serial port.
        :param msg: Message to be sent, will be terminated by newline character if not present.
        :return: Number of bytes written
        :raises: IOError when a specified timeout occurs
        :raises: UnicodeError if the message cannot be encoded in the specified encoding
        """
        # Send the message
        data = msg.encode(encoding=self.send_encoding)
        total_sent_bytes = 0
        total_bytes = len(data)

        # Ensure that all the data is sent
        while total_sent_bytes < total_bytes:
            # Send only the remaining data
            sent_bytes = self._ser.write(data[total_sent_bytes:])
            total_sent_bytes += sent_bytes

    def hook_pre_send(self, msg: str) -> str:
        """
        Ensure that the message is terminated properly
        :return: Processed response string
        """
        return msg if msg.endswith(self.terminator) else (msg + self.terminator)
