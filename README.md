# BioCam Emulator

This python package is a simple serial emulator. It is intended to be used as a testbed
for BioCam's serial communication. It is not intended to be used as a replacement for
the actual BioCam device.

## NOTES

- Iridium queue has 4 retries before dropping the message (5 min) it can be increased
- We can use -1 -1 as indexes for the summaries. (add documentation)
- `*bc_get_summaries X [Y Z ...]\n` to request multiple, non correlative summaries.
- Encode the message number somewhere so that we know which ones we've received.
- Check the messages received contain the same info as the ones sent
- Prepare a quick display GUI
- Update BioCam firmware

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

The protocol description is in the file [protocol.md](protocol.md).
