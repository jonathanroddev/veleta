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
    veleta-core-wired.bat   Start the core on a USB-cable sensor. This is
                            the one to run for the wired kit - see below.
    veleta-core-ble.bat     Start the core on the BLE (battery) sensor.
    veleta-core.bat         Start the core, using whatever config.env says.
                            That is the WiFi layout: it listens on UDP and
                            with a wired or BLE sensor it waits forever.
    veleta-core-demo.bat    Replay the bundled recording instead, on a loop.
                            No sensor and no network needed - use this to
                            check the whole chain end to end.
    list-ports.bat          List the serial ports Windows can see. This is
                            how you find which COM a wired sensor or a
                            paired Bluetooth module was given.

    Both open a console window and keep running until you close it or press
    Ctrl-C. Command line options are passed straight through, e.g.
        veleta-core.bat --listen-port 1400

THE FIREWALL PROMPT MATTERS
    The first time it runs, Windows asks whether to allow it on the network.
    ALLOW IT on private networks. Blocked, the sensor frames never arrive and
    the symptom is simply that nothing moves - with no error anywhere. This
    is the most common thing to go wrong on a fresh Windows machine.

    Only the sensor port is exposed. The port consumers use (1400) is bound
    to 127.0.0.1 and never leaves the machine.

WITH BLENDER
    Install the extension zip (veleta-<version>.zip) from
    Edit > Preferences > Add-ons > Install from Disk. Start the core first,
    then press Connect in the Veleta tab of the 3D viewport sidebar.

    The extension and the core must report the SAME version number. They
    ship together; if they disagree, the panel says so.

A BLE SENSOR (THE BATTERY KIT)
    Run veleta-core-ble.bat. That is the whole procedure: it already
    points at config.ble.env, which carries the 6-field layout BLE needs.

    Running veleta-core.bat instead is the easy mistake - that one listens
    for WiFi sensors over UDP and will wait forever.

    With one module it connects to the first peripheral advertising the
    HM-10 service. With several, set BLE_NAME in config.ble.env to the
    name you gave the module with AT+NAME.

A SENSOR ON A SERIAL PORT (USB CABLE, OR A CLASSIC BLUETOOTH MODULE)
    A classic Bluetooth module is a serial link over the air: pair it in
    Windows settings and it appears as a virtual COM port, exactly like a
    USB cable. Both are the same path as far as the core is concerned, and
    both use veleta-core-wired.bat.

    1. If it is a Bluetooth module (not a cable), pair it first
       (Windows Settings > Bluetooth & devices).
    2. Run list-ports.bat and note the COM number. Windows assigns it, so
       do not guess it - and pairing a Bluetooth module can create TWO
       ports, one outgoing and one incoming. The outgoing one is the one to
       use.
    3. Edit config.wired.env:
           SERIAL_PORT=COM5          <- whatever list-ports.bat showed
           BAUD_RATE=115200          <- must match the sketch

       This file already carries the field layout a wired/serial sensor
       needs (6 fields, no device id) - config.env's is the WiFi layout and
       will report every frame UNPARSED if used instead.
    4. Double-click veleta-core-wired.bat.

    Or, without editing anything:
        veleta-core-wired.bat --serial-port COM5

    A serial link carries exactly one sensor, so its frames have no device
    id. The core names it from SERIAL_DEVICE_ID in config.wired.env, and
    that is the name to map to an object in the extension.

CONFIGURATION
    config.env, beside this file. Plain KEY=value, no quotes. The values
    worth knowing:
        SOURCE          udp (WiFi) | serial (USB or Bluetooth) | file
        LISTEN_PORT     the port WiFi sensors send to (must match the sensor)
        SERIAL_PORT     the COM port, when SOURCE=serial
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

      A BLE module never appears in list-ports.bat and cannot be paired
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
