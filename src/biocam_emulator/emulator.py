#!/usr/bin/env python3

"""
BioCam command simulator

This script simulates the BioCam command interface. It is intended to be used as
a testbed for the BioCam serial interface.
"""

import time
from pathlib import Path
from threading import Event, Thread, Timer

import numpy as np
import serial

from .virtual_serial_ports import VirtualSerialPorts

"""
Maybe use state 9 and 10 as computing and sending.
Did they store the state as a byte or as integer? (e.g. can it be larger than 7?)


summary ID[INT] RAW_DATA\n
summary done\n

ID (int) zero padded to two digits
RAW_DATA is a string of hex formatted bytes.

state 9 for computing the summaries + 4 if laser is armed
state 10 for sending the summaries + 4 if laser is armed
"""


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

    def start_summaries(self):
        self._state = 9

    def sending_summaries(self):
        self._state = 10

    def idle(self):
        self._state = 1

    def stop(self):
        self._state = 0


class RemoteAwarenessData:
    def __init__(self, input_folder):
        self.input_folder = input_folder
        self.load_data()

    def load_data(self):
        # Find all the files starting with "image_summary_XXX.txt" where XXX is a number
        self.image_summary_files = sorted(self.input_folder.glob("image_summary_*.txt"))
        self.representative_image_files = sorted(
            self.input_folder.glob("representative_image_*.txt")
        )
        # Randomly sort the files in self.data
        self.data = np.random.permutation(
            self.image_summary_files + self.representative_image_files
        )

    def len(self):
        return len(self.data)

    def get(self, idx):
        # Try opening the file
        with open(self.data[idx], "r") as f:
            # Read the file
            data = f.read()
        return data


class BioCamCommand:
    def __init__(self, command, response=None, num_arguments=0):
        self.command = "*" + command + "\n"
        self.response = "$" + command + "\n"
        self.num_arguments = num_arguments
        self.arguments = []
        if response is not None:
            self.response = response

    def check_and_reply(self, command):
        if self.num_arguments == 0:
            if command == self.command:
                return self.response
            return None
        split_command = command.split(" ")
        if len(split_command) != (self.num_arguments + 1):
            return None
        self.arguments = split_command[1:]
        return self.response[:-1] + " " + " ".join(split_command[1:]) + "\n"


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

        # Get this file folder
        input_folder = Path(__file__).parent / "data"
        self.remote_awareness_data = RemoteAwarenessData(input_folder)

        self.report_status_period = 60  # every 60 seconds
        self.request_time_period = 600  # every 10 minutes
        self.state_thread_event = Event()

        self.state_thread = Thread(
            target=self.state_thread_fn, args=(self.state_thread_event,)
        )
        self.status_timer_thread = Timer(self.report_status_period, self.report_status)
        self.time_timer_thread = Timer(self.request_time_period, self.request_time)

        self.ports = VirtualSerialPorts(2, loopback=False, debug=True)

        self.commands = [
            BioCamCommand("bc_start_mapping"),
            BioCamCommand("bc_stop_acquisition"),
            BioCamCommand("bc_start_laser_calibration"),
            BioCamCommand("bc_shutdown"),
            BioCamCommand("bc_start_summaries", num_arguments=2),
            BioCamCommand("bc_stop_summaries"),
        ]

        self.mode = BioCamStateMachine()
        self.mode.idle()

        self.state_thread.start()
        self.status_timer_thread.start()
        self.time_timer_thread.start()

        with VirtualSerialPorts(2) as ports:
            self.port0 = ports[0]
            self.port1 = ports[1]

            print("Please use serial port:")
            # print(self.port0)
            print(self.port1)

            print(
                "\nRecommended script to run in a separate terminal:\n\t",
                "picocom -b 57600 -c --omap crlf " + self.port1,
            )
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
                self.state_thread_event.set()
                self.status_timer_thread.cancel()
                self.time_timer_thread.cancel()
                break

    def emulate_step(self):
        if len(self.message_outbox) > 0:
            msg = self.message_outbox.pop(0)
            self.serial0.write(msg.encode("utf-8"))

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

    def state_thread_fn(self, event):
        while True:
            if self.mode.state > 1 and self.mode.state < 9:
                if self.mode.state == 3 or self.mode.state == 7:
                    self.num_images_cam0 += 1
                else:
                    self.num_images_cam0 += 20
                self.num_images_cam1 += 1
            if event.is_set():
                break
            time.sleep(3)

    def report_status(self):
        """BioCam sends its status every 60 seconds
        status operation_mode number_images_cam0 number_images_cam1 score_cam0
        score_cam1 cpu_temperature cam0_temperature cam1_temperature
        available_disk_space\n
        status 8 00000312 00010852 55257 09258 42 34 35 0024591674256\n
        """
        if self.mode.state == 4 or self.mode.state == 8:
            self.score_cam0 = np.random.randint(
                400, 1000
            )  # max 65535, zero padded to 5 digits
            self.score_cam1 = np.random.randint(
                5000, 8000
            )  # max 65535, zero padded to 5 digits
        if self.mode.state in [2, 3, 4, 6, 7, 8]:
            self.cam0_temperature = np.random.randint(30, 50)
            self.cam1_temperature = np.random.randint(30, 50)
        self.cpu_temperature = np.random.randint(30, 50)
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
        print("Reporting state: " + msg)
        self.message_outbox.append(msg)
        self.status_timer_thread = Timer(self.report_status_period, self.report_status)
        self.status_timer_thread.start()

    def request_time(self):
        """BioCam4000 sends
            $time\n
        every 10 minutes. It expects a response of
            *time system_time\n
            e.g.
            *time 1607105547000\n
            in milliseconds since epoch
        """
        print("Requesting time: " + "$time\n")
        self.message_outbox.append("$time\n")
        self.time_timer_thread = Timer(self.request_time_period, self.request_time)
        self.time_timer_thread.start()

    def sending_summaries_timer_thread(self, start_idx, end_idx, idx_list=None):
        self.mode.sending_summaries()

        if idx_list is not None:
            # Send summaries in idx_list
            for idx in idx_list:
                if idx > self.remote_awareness_data.len():
                    continue
                msg = f"summary {idx:02d} " + self.remote_awareness_data.get(int(idx))
                self.message_outbox.append(msg)
                time.sleep(1)
            self.message_outbox.append("summary done\n")
            self.mode.idle()
            return

        # check start and end are within the range of the data
        data_len = self.remote_awareness_data.len()
        if start_idx < 0 or start_idx >= data_len:
            start_idx = 0
        if end_idx < 0 or end_idx > data_len:
            end_idx = data_len

        for i in range(start_idx, end_idx):
            msg = f"summary {i:02d} " + self.remote_awareness_data.get(i)
            self.message_outbox.append(msg)
            time.sleep(1)
        self.message_outbox.append("summary done\n")
        self.mode.idle()

    def check_command(self, msg):
        """Check if the received message is valid. Otherwise, print error in console"""
        if msg.startswith("*time"):
            # Check it's followed by a timestamp (13 digits) milliseconds since epoch
            if len(msg) != 20:
                print("Invalid timestamp received")
        if msg.startswith("nav"):
            """nav message update
            Starts with 'nav' and followed by to millisecond timestamps (13 digits) and
            a list of data that can either be:
            position: (latitude-longitude in decimal degrees, 6 decimal places (fix))
            orientation: (Euler angles in degrees, 3 decimal places (fix))
            altitude: (in metres, 3 decimal places (fix). If no bottom-lock: 10000.000)
            depth:  (in metres, 3 decimal places (fix))
            velocities: (surge, sway (positive to the right), heave (positive in
            downwards direction) in m/s, 3 decimal places (fix))

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
                if command.command.startswith("*bc_start_mapping"):
                    self.mode.start_mapping()
                elif command.command.startswith("*bc_stop_acquisition"):
                    self.mode.idle()
                elif command.command.startswith("*bc_start_camera_calibration"):
                    self.mode.camera_calibration()
                elif command.command.startswith("*bc_start_laser_calibration"):
                    self.mode.laser_calibration()
                elif command.command.startswith("*bc_shutdown"):
                    self.mode.stop()
                elif command.command.startswith("*bc_start_summaries"):
                    self.mode.start_summaries()
                    try:
                        start_idx = int(command.arguments[0])
                        end_idx = int(command.arguments[1])
                        self.start_summarires_timer = Timer(
                            20,
                            self.sending_summaries_timer_thread,
                            args=(start_idx, end_idx),
                        )
                        self.start_summarires_timer.start()
                    except Exception as e:
                        print("Invalid arguments for summaries: ")
                        print("\t - Received start_idx: " + command.arguments[0])
                        print("\t - Received end_idx: " + command.arguments[1])
                        print("Exception message: " + str(e))
                elif command.command == "*bc_stop_summaries\n":
                    self.self.start_summarires_timer.cancel()
                    self.mode.idle()
                return response


def main():
    BioCamEmulator()


if __name__ == "__main__":
    main()
