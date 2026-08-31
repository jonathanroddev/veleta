veleta core - Windows x64 (wired build)
========================================

Version VERSION_PLACEHOLDER. 64-bit Intel/AMD.

An UNSIGNED test build. It is meant for trying the product on a machine you
control, not for giving to a customer: Windows will warn about software from
an unidentified publisher until the release build is code-signed.

This build only supports a USB-cable (or paired classic Bluetooth) sensor.
It deliberately leaves out WiFi and BLE support to stay small and simple -
see WHAT IS NOT IN THIS BUILD.

WHAT THIS IS
    The veleta core, plus its own private copy of Python. Nothing is
    installed, nothing is written outside this folder, and the machine's
    PATH is neither used nor changed. Delete the folder and it is gone.

RUNNING IT
    veleta-core-wired.bat   Start the core on your sensor. This is the one
                            to run.
    veleta-core-demo.bat    Replay the bundled recording instead, on a loop.
                            No sensor needed - use this to check the whole
                            chain end to end (core, protocol, extension,
                            scene) before the sensor is even connected.
    list-ports.bat          List the serial ports Windows can see. This is
                            how you find which COM your sensor was given.

    Both open a console window and keep running until you close it or press
    Ctrl-C. Command line options are passed straight through, e.g.
        veleta-core-wired.bat --serial-port COM5

FIRST RUN
    1. Plug in the sensor (or pair it first, if it is a classic Bluetooth
       module rather than a cable - it then appears as a virtual COM port,
       exactly like a cable).
    2. Run list-ports.bat and note the COM number. Windows assigns it, so
       do not guess it - and pairing a Bluetooth module can create TWO
       ports, one outgoing and one incoming. The outgoing one is the one to
       use.
    3. Edit config.wired.env:
           SERIAL_PORT=COM5          <- whatever list-ports.bat showed
           BAUD_RATE=115200          <- must match the sketch
    4. Double-click veleta-core-wired.bat.

    Or, without editing anything:
        veleta-core-wired.bat --serial-port COM5

    A serial link carries exactly one sensor, so its frames have no device
    id. The core names it from SERIAL_DEVICE_ID in config.wired.env, and
    that is the name to map to an object in the extension.

    Symptom of the wrong COM port or an unpowered/unplugged sensor:
    "could not open port...". Symptom of a config pointed at the wrong
    layout: every frame reported UNPARSED.

WITH BLENDER
    Install the extension zip (veleta-<version>.zip) from
    Edit > Preferences > Add-ons > Install from Disk. Start the core first,
    then press Connect in the Veleta tab of the 3D viewport sidebar.

    The extension and the core must report the SAME version number. They
    ship together; if they disagree, the panel says so.

ABOUT THE FIREWALL PROMPT
    A wired sensor talks to the core over the USB cable, not the network, so
    this build should not need a firewall prompt for the sensor itself. The
    port consumers use (1400, for Blender) is bound to 127.0.0.1 and never
    leaves the machine either. If Windows still prompts, allow it on private
    networks.

CONFIGURATION
    config.wired.env, beside this file. Plain KEY=value, no quotes. The
    values worth knowing:
        SERIAL_PORT     the COM port your sensor was given
        BAUD_RATE       must match the sketch (115200 for the bench sketch)
        IDX_*           where each field sits in the sensor's CSV line
        AUTO_CALIBRATE  capture a reference pose a few seconds after start

    A sensor whose numbers land in the wrong place is a config change - the
    IDX_* keys - never a code change.

WHAT IS NOT IN THIS BUILD
    - No code signature. See above.
    - No WiFi support and no BLE support, on purpose: this is the wired-only
      build, smaller and simpler because it carries nothing either path
      would need. If you need WiFi or BLE, that is a different package.
    - 64-bit Intel/AMD only. Not ARM.

LICENCES
    LICENSE                    the core, proprietary.
    runtime\LICENSE.txt        Python, redistributed under the PSF licence.
    PYSERIAL-LICENSE.txt       pyserial, redistributed under its BSD licence.

    The Blender extension is a separate program under GPL v3 or later and is
    not in this package. It talks to this core over a documented network
    protocol; it does not contain it.
