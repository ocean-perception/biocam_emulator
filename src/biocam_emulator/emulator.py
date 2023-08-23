#!/usr/bin/env python3

"""
BioCam command simulator

This script simulates the BioCam command interface. It is intended to be used as
a testbed for the BioCam serial interface.
"""

import serial
import time

from virtual_serial_ports import VirtualSerialPorts


class BioCamCommand:
    def __init__(self, command, response=None, has_arguments=False):
        self.command = "*" + command + "\r\n"
        self.response = "$" + command + "\r\n"
        if response is not None:
            self.response = response

    def check_and_reply(self, command):
        if not self.has_arguments:
            if command == self.command:
                return self.response
            else:
                return None
        else:
            split_command = command.split(" ")
            if split_command[0] == self.command:
                return self.response + " ".join(split_command[1:]) + "\r\n"
            else:
                return None


class BioCamEmulator:
    def __init__(self):
        print("Starting BioCam emulator")

        self.ports = VirtualSerialPorts(2, loopback=False, debug=True)

        self.commands = [
            BioCamCommand("bc_start_mapping"),
            BioCamCommand("bc_stop_acquisition"),
            BioCamCommand("bc_start_laser_calibration"),
            BioCamCommand("bc_shutdown"),
            BioCamCommand("bc_start_summaries", has_arguments=True),
            BioCamCommand("bc_stop_summaries"),
        ]

        self.operation_mode = 0
        """ Operation mode
        0: Invalid
        1: Idle, not armed
        2: Camera cal
        3: laser Cal
        4: Mapping
        Adding 4 to the operation mode indicates that the laser is armed.
        """

        with VirtualSerialPorts(2) as ports:
            self.port0 = ports[0]
            self.port1 = ports[1]

            print("Please use serial port:")
            # print(self.port0)
            print(self.port1)
            self.serial0 = serial.Serial(
                ports[0],
                baudrate=56700,
                timeout=0.1,
                bytesize=8,
                parity="N",
                stopbits=1,
            )

            while True:
                try:
                    self.serial0.write(b"hello\r\n")
                    time.sleep(1)
                except KeyboardInterrupt:
                    print("Exiting")
                    break

    def report_status(self):
        """BioCam sends its status every 60 seconds
        status operation_mode number_images_cam0 number_images_cam1 score_cam0 score_cam1 cpu_temperature cam0_temperature cam1_temperature available_disk_space\n
        status 8 00000312 00010852 55257 09258 42 34 35 0024591674256\n
        """
        pass

    def request_time(self):
        """BioCam4000 sends
            $time\n
        every 10 minutes. It expects a response of
            *time system_time\n
            e.g.
            *time 1607105547000\n
        """
        pass


def main():
    BioCamEmulator()


if __name__ == "__main__":
    main()
