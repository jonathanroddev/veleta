veleta core - Windows x64
=========================

Version VERSION_PLACEHOLDER. 64-bit Intel/AMD.

An UNSIGNED test build. It is meant for trying the product on a machine you
control, not for giving to a customer: Windows will warn about software from
an unidentified publisher until the release build is code-signed.

WHAT THIS IS
    The veleta core, plus its own private copy of Python. Nothing is
    installed, nothing is written outside this folder, and the machine's
    PATH is neither used nor changed. Delete the folder and it is gone.

RUNNING IT
    veleta-sensor.bat
        Start the core on a USB-cable sensor, or on a paired classic
        Bluetooth module. This is the one to run for the wired kit - see
        below.
    veleta-sensor-bluetooth.bat
        Start the core on the BLE (battery) sensor.
    veleta-sensor-wifi.bat
        Start the core on the WiFi layout in ajustes-wifi.txt: it listens
        on UDP, and with a wired or BLE sensor it waits forever.
    diagnostico\veleta-demo.bat
        Replay the bundled recording instead, on a loop. No sensor and no
        network needed - use this to check the whole chain end to end, and
        to tell a sensor fault apart from a software one.
    diagnostico\ver-puertos.bat
        List the serial ports Windows can see. Only needed when the core
        asks you to choose between them, or to find which COM a paired
        Bluetooth module was given.

    The diagnostico folder holds everything that is not a sensor launcher,
    so the launchers are the only .bat files beside this README.

    Both open a console window and keep running until you close it or press
    Ctrl-C. Command line options are passed straight through, e.g.
        veleta-sensor-wifi.bat --listen-port 1400

THE FIREWALL PROMPT MATTERS
    The first time it runs, Windows asks whether to allow it on the network.
    ALLOW IT on private networks. Blocked, the sensor frames never arrive and
    the symptom is simply that nothing moves - with no error anywhere. This
    is the most common thing to go wrong on a fresh Windows machine.

    Only the sensor port is exposed. The port consumers use (1400) is bound
    to 127.0.0.1 and never leaves the machine.

WITH BLENDER
    Install the extension zip (veleta-extension-blender-<version>.zip)
    from
    Edit > Preferences > Add-ons > Install from Disk. Start the core first,
    then press Connect in the Veleta tab of the 3D viewport sidebar.

    The extension and the core must report the SAME version number. They
    ship together; if they disagree, the panel says so.

A BLE SENSOR (THE BATTERY KIT)
    Run veleta-sensor-bluetooth.bat. That is the whole procedure: it
    already points at ajustes-bluetooth.txt, which carries the 6-field
    layout BLE needs.

    Running veleta-sensor-wifi.bat instead is the easy mistake - that one
    listens for WiFi sensors over UDP and will wait forever.

    With one module it connects to the first peripheral advertising the
    HM-10 service. With several, set BLE_NAME in ajustes-bluetooth.txt to
    the name you gave the module with AT+NAME.

A SENSOR ON A SERIAL PORT (USB CABLE, OR A CLASSIC BLUETOOTH MODULE)
    A classic Bluetooth module is a serial link over the air: pair it in
    Windows settings and it appears as a virtual COM port, exactly like a
    USB cable. Both are the same path as far as the core is concerned, and
    both use veleta-sensor.bat.

    1. If it is a Bluetooth module (not a cable), pair it first
       (Windows Settings > Bluetooth & devices).
    2. Double-click veleta-sensor.bat.

    With exactly one USB-serial device connected that is the whole of it:
    the core finds the port itself and prints "(auto-detected)" beside the
    one it chose. A paired Bluetooth module is usually not that case -
    pairing can create TWO ports, one outgoing and one incoming, and only
    the outgoing one works - so there the core will list them and stop.

    Settle it for one run:
        veleta-sensor.bat --serial-port COM5

    ...or for good, in ajustes-sensor.txt:
        SERIAL_PORT=COM5          <- one of the ports it listed
        BAUD_RATE=115200          <- must match the sketch

    diagnostico\ver-puertos.bat lists the same ports on their own if you
    would rather look first. And note that ajustes-sensor.txt already carries the field
    layout a wired/serial sensor needs (6 fields, no device id):
    ajustes-wifi.txt's is the WiFi layout and reports every frame UNPARSED
    if used instead.

    A serial link carries exactly one sensor, so its frames have no device
    id. The core names it from SERIAL_DEVICE_ID in ajustes-sensor.txt, and
    that is the name to map to an object in the extension.

CONFIGURATION
    One file per sensor path, beside this one: ajustes-sensor.txt for a
    cable or a paired Bluetooth module, ajustes-bluetooth.txt for a BLE
    module, ajustes-wifi.txt for WiFi. diagnostico\ajustes-demo.txt
    belongs to the demo - it is the bundled recording's layout, not a
    sensor's, and needs no editing.

    Plain KEY=value, no quotes. The values worth knowing:
        SOURCE          udp (WiFi) | serial (USB or Bluetooth) | file
        LISTEN_PORT     the port WiFi sensors send to (must match the sensor)
        SERIAL_PORT     the COM port, when SOURCE=serial. Leave it EMPTY and
                        the core finds it, which is the normal case.
        IDX_*           where each field sits in the sensor's CSV line
        AUTO_CALIBRATE  capture a reference pose a few seconds after start

    A sensor whose numbers land in the wrong place is a config change - the
    IDX_* keys - never a code change.

WHAT IS NOT IN THIS BUILD
    - No code signature. See above.
    - Nothing is missing for BLE: bleak, the WinRT bindings and
      typing_extensions ship inside this package. But this half is
      developed against macOS CoreBluetooth, and WinRT is a different
      implementation, so treat the first run as a test.

      A BLE module never appears in ver-puertos.bat and cannot be paired
      in Windows settings: it is not a serial port and never becomes one.
      That is normal. Classic Bluetooth modules (HC-05, HC-06) DO pair as
      a COM port, and work through --source serial.
    - 64-bit Intel/AMD only. Not ARM.

LICENCES
    LICENSE                    the core, proprietary.
    runtime\LICENSE.txt        Python, redistributed under the PSF licence.
    PYSERIAL-LICENSE.txt       pyserial, redistributed under its BSD licence.
    BLEAK-LICENSE.txt          bleak and the winrt-* bindings, MIT.
    TYPING-EXTENSIONS-LICENSE.txt  typing_extensions, PSF licence.

    The Blender extension is a separate program under GPL v3 or later and is
    not in this package. It talks to this core over a documented network
    protocol; it does not contain it.
