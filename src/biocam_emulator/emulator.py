#!/usr/bin/env python3

"""
BioCam command simulator

This script simulates the BioCam command interface. It is intended to be used as
a testbed for the BioCam serial interface.
"""

import serial
import time
import threading

import numpy as np

from virtual_serial_ports import VirtualSerialPorts


class BioCamStateMachine:
    def __init__(self, laser_armed=False):
        self.laser_armed = laser_armed
        self.idle()

    @property
    def state(self):
        return self._state + self._laser_state

    @property
    def _laser_state(self):
        if self.laser_armed:
            return 4
        else:
            return 0

    def start_mapping(self):
        self._state = 4

    def camera_calibration(self):
        self._state = 2

    def laser_calibration(self):
        self._state = 3

    def idle(self):
        self._state = 1

    def stop(self):
        self.idle()


class BioCamCommand:
    def __init__(self, command, response=None, has_arguments=False):
        self.command = "*" + command + "\n"
        self.response = "$" + command + "\n"
        self.has_arguments = has_arguments
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
                return self.response
            elif split_command[0] == self.command[:-1]:
                return self.response[:-1] + " " + " ".join(split_command[1:]) + "\n"
            else:
                return None


class BioCamEmulator:
    def __init__(self):
        print("Starting BioCam emulator")

        self.num_images_cam0 = 0
        self.num_images_cam1 = 0
        self.score_cam0 = 0
        self.score_cam1 = 0
        self.cpu_temperature = 0
        self.cam0_temperature = 0
        self.cam1_temperature = 0
        self.available_disk_space = 0
        self.stop_thread = False

        self.message_outbox = []
        self.message_inbox = ""

        self.state_thread = threading.Thread(target=self.state_thread_fn)
        self.report_status_timer = threading.Timer(6.0, self.report_status)
        self.request_time_timer = threading.Timer(6.0, self.request_time)

        self.ports = VirtualSerialPorts(2, loopback=False, debug=True)

        self.commands = [
            BioCamCommand("bc_start_mapping"),
            BioCamCommand("bc_stop_acquisition"),
            BioCamCommand("bc_start_laser_calibration"),
            BioCamCommand("bc_shutdown"),
            BioCamCommand("bc_start_summaries", has_arguments=True),
            BioCamCommand("bc_stop_summaries"),
        ]

        self.mode = BioCamStateMachine()
        self.mode.idle()

        self.state_thread.start()
        self.report_status_timer.start()
        self.request_time_timer.start()

        with VirtualSerialPorts(2) as ports:
            self.port0 = ports[0]
            self.port1 = ports[1]

            print("Please use serial port:")
            # print(self.port0)
            print(self.port1)
            self.serial0 = serial.Serial(
                ports[0],
                baudrate=57600,
                timeout=0.1,
                bytesize=8,
                parity="N",
                stopbits=1,
            )
            self.infinite_loop()

    def infinite_loop(self):
        while True:
            try:
                self.emulate_step()
                time.sleep(1)
            except KeyboardInterrupt:
                print("Exiting")
                self.stop_thread = True
                break

    def emulate_step(self):
        command = self.serial0.readline()
        # print("Received: " + str(command))
        self.message_inbox += command.decode("utf-8")
        # print("Message inbox: " + self.message_inbox)

        if not command.endswith(b"\n"):
            return

        command = self.message_inbox
        self.message_inbox = ""
        if command == "":
            return
        print("Received command: " + str(command))
        response = self.check_command(command)
        if response is not None:
            print("Sending response: " + response)
            self.serial0.write(response.encode("utf-8"))

    def state_thread_fn(self):
        while True:
            if self.mode.state > 1:
                if self.mode.state == 3:
                    self.num_images_cam0 += 1
                else:
                    self.num_images_cam0 += 20
                self.num_images_cam1 += 1
            if self.stop_thread:
                break
            time.sleep(5)

    def report_status(self):
        """BioCam sends its status every 60 seconds
        status operation_mode number_images_cam0 number_images_cam1 score_cam0 score_cam1 cpu_temperature cam0_temperature cam1_temperature available_disk_space\n
        status 8 00000312 00010852 55257 09258 42 34 35 0024591674256\n
        """
        if self.mode.state == 4 or self.mode.state == 8:
            self.score_cam0 = np.random.randint(
                400, 1000
            )  # max 65535, zero padded to 5 digits
            self.score_cam1 = np.random.randint(
                5000, 8000
            )  # max 65535, zero padded to 5 digits
        self.cpu_temperature = np.random.randint(30, 50)
        self.cam0_temperature = np.random.randint(30, 50)
        self.cam1_temperature = np.random.randint(30, 50)
        self.available_disk_space = np.random.randint(
            100000000000, 200000000000  # Zero-padded to 13 digits.
        )  # < 2,000,000,000,000 (but might be bigger in the future).

        msg = (
            "status "
            + str(self.mode.state)
            + " "
            + str(self.num_images_cam0)
            + " "
            + str(self.num_images_cam1)
            + " "
            + str(self.score_cam0)
            + " "
            + str(self.score_cam1)
            + " "
            + str(self.cpu_temperature)
            + " "
            + str(self.cam0_temperature)
            + " "
            + str(self.cam1_temperature)
            + " "
            + str(self.available_disk_space)
            + "\n"
        )
        self.message_outbox.append(msg)

    def request_time(self):
        """BioCam4000 sends
            $time\n
        every 10 minutes. It expects a response of
            *time system_time\n
            e.g.
            *time 1607105547000\n
            in milliseconds since epoch
        """
        self.message_outbox.append("$time\n")

    def check_command(self, msg):
        """Check if the received message is valid. Otherwise, print error in console"""
        if msg.startswith("*time"):
            # Check it's followed by a timestamp (13 digits) milliseconds since epoch
            if len(msg) != 19:
                print("Invalid timestamp received")
        if msg.startswith("nav"):
            """nav message update
            Starts with 'nav' and followed by to millisecond timestamps (13 digits) and
            a list of data that can either be:
            position: (latitude-longitude in decimal degrees, 6 decimal places (fix))
            orientation: (Euler angles in degrees, 3 decimal places (fix))
            altitude: (in metres, 3 decimal places (fix). If no bottom-lock: 10000.000)
            depth:  (in metres, 3 decimal places (fix))
            velocities: (surge, sway (positive to the right), heave (positive in downwards direction) in m/s, 3 decimal places (fix))

            Check that data is valid and print error if not
            """
            parts = msg.split(" ")
            ts1 = parts[1]
            ts2 = parts[2]
            datatype = parts[3]
            data = parts[4:]
            data[-1] = data[-1].replace("\n", "")
            if len(ts1) != 13:
                print("Invalid nav first timestamp received")
            if len(ts2) != 13:
                print("Invalid nav second timestamp received")
            if datatype == "altitude":
                if len(data) != 1:
                    print("Invalid altitude nav data received")
            if datatype == "depth":
                if len(data) != 1:
                    print("Invalid depth nav data received")
            if datatype == "position":
                if len(data) != 2:
                    print("Invalid position nav data received")
            if datatype == "orientation":
                if len(data) != 3:
                    print("Invalid orientation nav data received")
            if datatype == "velocities":
                if len(data) != 3:
                    print("Invalid velocity nav data received")
        for command in self.commands:
            response = command.check_and_reply(msg)
            if response is not None:
                return response


def main():
    BioCamEmulator()


if __name__ == "__main__":
    main()
