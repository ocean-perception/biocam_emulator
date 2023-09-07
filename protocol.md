# Communication protocol BioCam4000

**RS232 setup: 57600/8-N-1**

- Baud rate: 57600
- Length: 8
- Parity: 0
- Stop-bit: 1

Using canonical mode.\
If using termios in C, use the following settings:

```c++
struct termios tty;
memset(&tty, 0, sizeof(tty));
tty.c_iflag = 0; // input modes
tty.c_oflag = 0; // output modes
tty.c_cflag = CS8 \| CREAD \| CLOCAL; // control modes. 8n1.
tty.c_lflag = ISIG \| IEXTEN \| ICANON; // local modes
```

## Commands to BioCam4000

(\\n is the linefeed character)

BioCam4000 will acknowledge receipt of a command by sending back the
same command but starting with a \$ instead of a \*:

| Command to BioCam4000                 | Acknowledgement from BioCam4000       |
| ------------------------------------- | ------------------------------------- |
| \*bc_start_laser_calibration\\n       | \$bc_start_laser_calibration\\n       |
| \*bc_start_mapping\\n                 | \$bc_start_mapping\\n                 |
| \*bc_stop_acquisition\\n              | \$bc_stop_acquisition\\n              |
| \*bc_start_summaries \[i1\] \[i2\]\\n | \$bc_start_summaries \[i1\] \[i2\]\\n |
| \*bc_stop_summaries\\n                | \$bc_stop_summaries\\n                |
| \*bc_shutdown\\n                      | \$bc_shutdown\\n                      |

---

_Note_: If no acknowledgement is received within 1 minute, send command again,
up to 10 times.\
\*bc_start_laser_calibration won't be used with ALR.

## Command from BioCam4000

Time is formatted as epoch in milliseconds.

| BioCam4000 sends | ALR returns             |
| ---------------- | ----------------------- |
| \$time\\n        | \*time system_time\\n   |
| (e.g.)           | \*time 1607105547000\\n |

It is important to treat this without delay (use callback if possible)
as we are using Cristian\'s algorithm
(<https://en.wikipedia.org/wiki/Cristian%27s_algorithm>) to synchronise
clocks.

## Navigation data

_Note_: BioCam4000 does not acknowledge receipt of navigation data
messages.

All nav messages first contain the timestamp when the measurement was
made according to system time, followed by the sensor time timestamp
when the measurement was made. All timestamps are formatted as epoch
time in milliseconds.

### Position (latitude-longitude in decimal degrees, 6 decimal places (fix))

```
nav system_time sensor_time position latitude longitude\n
```

e.g.

```
nav 1607105547123 1607105547000 position 57.123456 -4.450100\n
```

### Depth (in metres, 3 decimal places (fix))

```
nav system_time sensor_time depth value\n
```

e.g.

```
nav 1607105547089 1607105547002 depth 512.580\n
```

### Altitude (in metres, 3 decimal places (fix). If no bottom-lock: 10000.000)

```
nav system_time sensor_time altitude value\n
```

e.g.

```
nav 1607105547189 1607105547102 altitude 6.473\n
```

```
nav 1607105547189 1607105547102 altitude 10000.000\n
```

### Orientation (Euler angles in degrees, 3 decimal places (fix))

```
nav system_time sensor_time orientation roll pitch yaw\n
```

e.g.

```
nav 1607105547889 1607105547042 orientation 2.357 -1.345 45.137\n
```

### Velocities (surge, sway (positive to the right), heave (positive in downwards direction) in m/s, 3 decimal places (fix))

```
nav system_time sensor_time velocities surge sway heave\n
```

e.g.

```
nav 1607105547889 1607105547042 velocities 0.541 -0.045 0.137\n
```

## Operation and health status from BioCam4000

BioCam sends its status at a fixed interval, once every minute.

```
status operation_mode number_images_cam0 number_images_cam1 score_cam0
score_cam1 cpu_temperature cam0_temperature cam1_temperature
available_disk_space\n
```

e.g.

```
status 8 00000312 00010852 55257 09258 42 34 35 0024591674256\n
```

- **operation_mode** is a number between 1 and 8
  - 1: Not acquiring any data, laser reed switch not armed
  - 2: Camera calibration, laser reed switch not armed
  - 3: Laser calibration, laser reed switch not armed
  - 4: Mapping, laser reed switch not armed
  - 5: Not acquiring any data, laser reed switch armed
  - 6: Camera calibration, laser reed switch armed
  - 7: Laser calibration, laser reed switch armed
  - 8: Mapping, laser reed switch armed
  - 9: Computing summaries
  - 10: Sending summaries
- **number_images_cam0** is a number \< 100000000 (probably much smaller,
  but leaving margin in case of 30 day missions). Zero-padded to 8
  digits.
- **number_images_cam1** is a number \< 100000000 (probably much smaller,
  but leaving margin in case of 30 day missions). Zero-padded to 8
  digits.
- **score_cam0** is a number between 0 and 65535. Zero-padded to 5 digits.
- **score_cam1** is a number between 0 and 65535. Zero-padded to 5 digits.
- **cpu_temperature** is an integer expressing the CPU temperature in °C.
  \<105. Zero-padded to 2 digits.
- **cam0_temperature** is an integer expressing the camera 0 temperature
  in °C. \<50. Zero-padded to 2 digits.
- **cam1_temperature** is an integer expressing the camera 1 temperature
  in °C. \<50. Zero-padded to 2 digits.
- **available_disk_space** is an integer expressing the available disk
  space in bytes. For current system \< 2,000,000,000,000 (but might
  be bigger in the future). Zero-padded to 13 digits.

## Summaries

If summaries are requested using the command `*bc_start_summaries\n`, BioCam4000 will change status to 9 and start computing summaries. When summaries are ready, BioCam4000 will change status to 10 and start sending summaries.

The summaries are sent in the following format:

```
summary ID HEX_STRING\n
summary ID+1 HEX_STRING\n
summary ID+2 HEX_STRING\n
...
summary ID+N HEX_STRING\n
summary done
```

The summary ID is a number between 0 and 65535. The HEX_STRING is a string of hexadecimal characters, each representing a byte. The length of the HEX_STRING is 1960 bytes or less. The summary done message is sent when all summaries have been sent.

_Note_: In between summaries, you may receive time requests and/or status messages.