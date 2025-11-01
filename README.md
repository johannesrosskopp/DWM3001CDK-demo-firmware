DWM3001CDK Demo Firmware
========================

A heavily-modified version of the [official firmware that runs on the Qorvo DWM3001CDK](https://www.qorvo.com/products/p/DWM3001CDK#documents) (as of 2023-10-30), cleaned up and simplified for easier customization. Features:

* **Reproducible**: built-in Docker development environment automates away most of the fragile and finicky parts of setting up the Qorvo SDK, SEGGER Embedded Studio, SEGGER J-Link, nRF52 SDK, and nRF command line tools.
* **Minimal**: based on the official DWM3001CDK CLI project, but significantly simpler in terms of code size and organization. Many source files and folders have been consolidated to make the project much easier to navigate.
* **Complete**: includes build system, flashing tools, and logging/debugging tools. This is the only repository you need to work with the firmware.
* **Portable**: run `make save-development-environment` to generate a 5GB tar file containing the entire development environment. In 10 years from now, when half of these dependencies disappear off the internet, run `make load-development-environment` and you'll still be able to compile this project.

Note that most of the UCI functionality has been removed, since I didn't end up needing it - only the UART CLI interface remains. Besides that, it has the exact same features as the original version of the firmware, including UWB ranging, calibration features, and more.

**See also:** if you're building a custom firmware for the DWM3001C, check out my [DWM3001C starter firmware repository](https://github.com/Uberi/DWM3001C-starter-firmware/).

Quickstart
----------

```sh
# MANUAL ACTION (OPTIONAL): run this command to use my prebuilt development environment, otherwise it'll be automatically built from scratch: docker pull uberi/qorvo-nrf52833-board

make build

# MANUAL ACTION: connect the lower USB port of the DWM3001CDK (labelled J9) to this computer using a USB cable (this is the J-Link's USB port)

make flash

# MANUAL ACTION: disconnect the lower USB port of the DWM3001CDK, and connect the upper USB port instead (labelled J20) (this is the nRF52833's USB port)

make serial-terminal
```

You should now see a minicom instance connected to the DWM3001CDK, try entering the "help" command to see available options.

Managing Multiple Devices
-------------------------

When working with multiple DWM3001CDK boards, you'll need to specify which device to connect to. The Makefile provides tools to help with this:

### List Available Devices

```sh
make list-devices
```

### Connect to a Specific Device

```sh
make serial-terminal DEVICE=/dev/ttyACM0
```

Replace `/dev/ttyACM0` with the device path you want to connect to.

### Troubleshooting Permission Issues

If you get a "Permission denied" error when trying to connect to a serial device:

```
minicom: cannot open /dev/ttyACM0: Permission denied
```

This happens because your user needs to be in the `dialout` group to access serial devices. Fix it by:

1. **Add your user to the dialout group:**
   ```sh
   sudo usermod -a -G dialout $USER
   ```

2. **Activate the new group membership** (choose one):
   - **Option A:** Start a new shell with updated groups:
     ```sh
     newgrp dialout
     ```
   - **Option B:** Check if you're already in the group and restart your terminal if needed:
     ```sh
     groups  # Should show 'dialout' in the list
     ```
   - **Option C:** Log out and log back in to your system


### Example RTPS (real time positioning system) UWB
TODO: just found this on the Qorvo forums: One initiator, two responders setup:

1. Perform the quickstart steps on three different DWM3001CDK boards, connect them both to power, and open a minicom terminal for each board.
2. Run `initf 4 2400 200 25 2 42 01:02:03:04:05:06:07:08 1 0 0 1 2` on one board, and `respf 4 2400 200 25 2 42 01:02:03:04:05:06:07:08 1 0 0 1` on another, and `respf 4 2400 200 25 2 42 01:02:03:04:05:06:07:08 1 0 0 2` on the last one.
3. In the terminal for the initiator, you should see the distances to each responder.

Developing
----------

You'll need Docker, and many of the hardware-facing commands in the Makefile assume you're using Linux. The `make serial-terminal` command assumes you have `minicom`, `grep`, and `udevadm` installed.

You can develop your custom applications by modifying `Src/main.c` and other files within `Src/`. Note that you'll have to manually edit `DWM3001CDK-DW3_QM33_SDK_CLI-FreeRTOS.emProject` with any file additions/removals/renames. It sounds annoying, and it is, but I still consider it an improvement over directly interacting with the proprietary SEGGER Embedded Studio.

License
-------

Most of the code in this repository comes from the official Qorvo SDKs and examples published on their website. Here's the copyright notice that comes with the SDKs:

> Read the header of each file to know more about the license concerning this file.
> Following licenses are used in the SDK:
> 
> * Apache-2.0 license
> * Qorvo license
> * FreeRTOS license
> * Nordic Semiconductor ASA license
> * Garmin Canada license
> * ARM Limited license
> * Third-party licenses: All third-party code contained in SDK_BSP/external (respective licenses included in each of the imported projects)
> 
> The provided HEX files were compiled using the projects located in the folders. For license and copyright information,
> see the individual .c and .h files that are included in the projects.

Therefore, you should carefully read the copyright headers of the individual source files and follow their licenses if you decide to use them. As for the parts I've built, such as the build environment, I release those under the [Creative Commons CC0 license](https://creativecommons.org/public-domain/cc0/) ("No Rights Reserved").
