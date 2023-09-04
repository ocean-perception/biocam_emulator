# BioCam Emulator

This python package is a simple serial emulator. It is intended to be used as a testbed
for BioCam's serial communication. It is not intended to be used as a replacement for
the actual BioCam device.

## Installation

You can install this package with pip:

```
pip install git+https://github.com/ocean-perception/biocam_emulator.git
```

## Usage

The emulator can be run with the following command:

```
biocam_emulator
```

The emulator will create a virtual serial port at (usually at `/dev/pts/5`, but it's
not always the case!). You can connect to this port with any serial terminal of your
choice. For example, you can use picocom:

```
picocom -b 57600 -c --omap crlf /dev/pts/5
```

## BioCam Serial Protocol

The BioCam serial protocol is a simple ASCII-based protocol. Each message is terminated
with a line feed (`\n`). For more details on the protocol, see the [BioCam Serial Protocol
Documentation](https://sotonac.sharepoint.com/:w:/r/teams/OPLab/Shared%20Documents/General/2%20Research/Projects/BioCam/procedures%20and%20checklists/Communication%20protocol%20BioCam4000.docx?d=wa513dffc53854c12adeb3d02e6a4e072&csf=1&web=1&e=ecOUYl).
