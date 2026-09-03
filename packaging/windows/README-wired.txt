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

    Guia-de-instalacion.pdf, beside the zip you unzipped rather than
    inside it, is the same walkthrough in Spanish with pictures of where
    things are. Start there if you would rather follow steps than read a
    reference.

RUNNING IT
    veleta-sensor.bat is the one to run. It is the only thing in this
    folder you need for normal use: it starts the core on your sensor,
    opens a console window and keeps running until you close it or press
    Ctrl-C. Command line options are passed straight through, e.g.
        veleta-sensor.bat --serial-port COM5

    Everything else lives in the diagnostico folder, and is only for when
    something is wrong or the sensor is not here yet:

    diagnostico\veleta-demo.bat
        Replay a bundled recording instead of a sensor, on a loop. No
        sensor needed - it checks the whole chain end to end (core,
        protocol, extension, scene) and is how you find out whether a fault
        is the sensor's or the software's. See SEEING IT WORK WITHOUT THE
        SENSOR.
    diagnostico\ver-puertos.bat
        List the serial ports Windows can see. Only needed when the core
        asks you to choose between them.

FIRST RUN
    1. Plug in the sensor (or pair it first, if it is a classic Bluetooth
       module rather than a cable - it then appears as a virtual COM port,
       exactly like a cable).
    2. Double-click veleta-sensor.bat.

    That is all of it when the sensor is the only USB-serial device on the
    machine: the core finds the port by itself and prints "(auto-detected)"
    beside the one it chose.

    With several such devices connected it will not guess. It lists what it
    found and stops, and you settle it either for one run:

        veleta-sensor.bat --serial-port COM5

    ...or for good, by opening ajustes-sensor.txt - it is a .txt, so a
    double-click opens it - and filling in:

        SERIAL_PORT=COM5          <- one of the ports it listed
        BAUD_RATE=115200          <- must match the sketch

    diagnostico\ver-puertos.bat lists those ports on their own. That is
    how you find which COM a paired Bluetooth module was given: pairing can
    create TWO ports, one outgoing and one incoming, and the outgoing one
    is the one that works.

    A serial link carries exactly one sensor, so its frames have no device
    id. The core names it from SERIAL_DEVICE_ID in ajustes-sensor.txt, and
    that is the name to map to an object in the extension.

    Symptom of an unplugged or unpowered sensor: "none could be found", or
    "could not open port..." if it went away after the core started.
    Symptom of a config pointed at the wrong layout: every frame reported
    UNPARSED.

WITH BLENDER
    Install the extension zip (veleta-extension-blender-<version>.zip)
    from
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
    ajustes-sensor.txt, beside this file. Plain KEY=value, no quotes. The
    values worth knowing:
        SERIAL_PORT     the COM port your sensor was given. Leave it EMPTY
                        and the core finds it, which is the normal case.
        BAUD_RATE       must match the sketch (115200 for the bench sketch)
        IDX_*           where each field sits in the sensor's CSV line
        AUTO_CALIBRATE  capture a reference pose a few seconds after start

    A sensor whose numbers land in the wrong place is a config change - the
    IDX_* keys - never a code change.

    diagnostico\ajustes-demo.txt belongs to the demo: it is the field
    layout of the bundled recording, not of your sensor. Nothing in it
    needs editing.

SEEING IT WORK WITHOUT THE SENSOR
    Two ways, and they check different halves. Which one you want depends
    on what you are trying to find out.

    diagnostico\veleta-demo.bat replays a recording through the real core -
    parsing, fusion, calibration, the network - so it checks everything
    except the sensor itself. Connect from Blender exactly as usual.

    The "Play demo" button in the Veleta panel replays a recording that
    lives inside the extension, with no core and no network at all, so it
    checks only Blender, the extension and your object mapping.

    Together they say where a fault is. If Play demo moves the object and
    veleta-demo.bat does not, it is the core or the connection. If both
    move it and your sensor does not, it is the sensor or its cable. If
    neither moves it, it is Blender, the extension or the object name.

WHAT IS NOT IN THIS BUILD
    - No code signature. See above.
    - No WiFi support and no BLE support, on purpose. This package is for
      the cable kit and carries nothing either other path would need.
      There is no package with every mode in it: a WiFi or Bluetooth kit
      comes with its own, holding only what that kit uses.
    - 64-bit Intel/AMD only. Not ARM.

LICENCES
    LICENSE                    the core, proprietary.
    runtime\LICENSE.txt        Python, redistributed under the PSF licence.
    PYSERIAL-LICENSE.txt       pyserial, redistributed under its BSD licence.

    The Blender extension is a separate program under GPL v3 or later and is
    not in this package. It talks to this core over a documented network
    protocol; it does not contain it.
