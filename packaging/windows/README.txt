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
    veleta-core.bat         Start the core, using whatever config.env says.
    veleta-core-demo.bat    Replay the bundled recording instead, on a loop.
                            No sensor and no network needed - use this to
                            check the whole chain end to end.
    list-ports.bat          List the serial ports Windows can see. This is
                            how you find which COM a paired Bluetooth module
                            was given.

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

A SENSOR ON A SERIAL PORT (USB, OR A CLASSIC BLUETOOTH MODULE)
    A classic Bluetooth module is a serial link over the air: pair it in
    Windows settings and it appears as a virtual COM port, exactly like a
    USB cable. Both are the same path as far as the core is concerned.

    1. Pair the module (Windows Settings > Bluetooth & devices).
    2. Run list-ports.bat and note the COM number. Windows assigns it, so
       do not guess it - and pairing can create TWO ports, one outgoing and
       one incoming. The outgoing one is the one to use.
    3. Edit config.env:
           SOURCE=serial
           SERIAL_PORT=COM5          <- whatever list-ports.bat showed
           BAUD_RATE=115200          <- must match the sketch

       A serial sensor that sends 6 fields with no device id (the Arduino
       bench sketch does) needs the other configuration file, because its
       field positions all shift down by one:

           veleta-core.bat --config config.wired.env

       Symptom of using the wrong one: every frame reported UNPARSED.
    4. Double-click veleta-core.bat.

    Or, without editing anything:
        veleta-core.bat --source serial --serial-port COM5

    A serial link carries exactly one sensor, so its frames have no device
    id. The core names it from SERIAL_DEVICE_ID in config.env, and that is
    the name to map to an object in the extension.

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
    - Nothing is missing for BLE: bleak and the WinRT bindings ship
      inside this package. But this half has never run on Windows. It is
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

    The Blender extension is a separate program under GPL v3 or later and is
    not in this package. It talks to this core over a documented network
    protocol; it does not contain it.
