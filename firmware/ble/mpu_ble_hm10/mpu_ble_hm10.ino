/*
  mpu_ble_hm10.ino
  ----------------
  A 5V ATmega328P Arduino + MPU-6500/6050 (I2C) + HM-10 (CC2541, Bluetooth
  Low Energy) on SoftwareSerial. Sends the wired form of the frame protocol
  (see ../../../docs/protocol.md) over the HM-10's transparent UART:

      ax,ay,az,gx,gy,gz\r\n

  NO deviceId ON THE WIRE, and that is deliberate. One BLE connection
  carries exactly one sensor, so the transport already identifies it —
  the same argument the wired bench makes. The core names the device from
  the peripheral's advertised BLE name, which is set once with `AT+NAME`
  (see hm10_config/). Spending ~7 bytes per frame on a constant string
  would cost real frames per second on a link this narrow.

  BOARD-AGNOSTIC 328P CODE, like mpu_wifi_avr_esp01 next door: D2/D3, A4/A5
  and Serial are the same on a Nano and on an Uno. The bench board is an
  original Nano, which needs `arduino:avr:nano:cpu=atmega328old` — its
  bootloader syncs at 57600, so the plain FQBN will not upload to it.

  WIRING
    MPU  VCC -> 5V     (GY-521 style breakout, on-board 3.3V regulator)
    MPU  GND -> GND
    MPU  SCL -> A5
    MPU  SDA -> A4
    HM-10 TX -> D2     (Arduino RX)
    HM-10 RX -> D3     (Arduino TX)
    HM-10 VCC/GND -> 5V/GND on the module's breakout board

  THE ONE RULE THIS SKETCH EXISTS TO ENFORCE: NEVER OUT-RUN THE LINK.
  Measured on 2026-08-24, HM-10 UART at 38400, 45-byte frames:

      link capacity            ~1990 B/s   =>  ~45 frames/s
      paced at 40 Hz           39.7 Hz delivered, 0.3% loss, 1194/1196
                               frames well formed and physically plausible
      free running at 66 Hz    45.2 Hz delivered, but only 388/1364 frames
                               well formed

  Over-running the link does NOT drop whole frames. The HM-10 drops BYTES
  mid-line, and the debris still parses: a truncated "-0.3044" arrives as
  "44", the line still has six numeric fields, and the core would happily
  feed 44 g into the filter. That is why TX_PERIOD_MS is a safety limit and
  not a performance knob. If you raise the frame rate, re-measure the
  ceiling first.

  HM-10 SETUP: the module must be at 38400 (`AT+BAUD2`). At the factory
  9600 the ceiling is only ~21 Hz, because the UART, not the radio, becomes
  the bottleneck. Use hm10_config/ to set it.
*/

#include <Wire.h>
#include <SoftwareSerial.h>

// HM-10 on D2/D3, same pins the ESP-01 sketch uses for its radio.
SoftwareSerial ble(2, 3);          // RX <- module TX, TX -> module RX

const int  MPU_ADDR   = 0x68;      // AD0 to GND
const long BLE_BAUD   = 38400;     // module must match: AT+BAUD2
const long USB_BAUD   = 115200;    // diagnostics only, not the data path

// 40 Hz. See the header: this is a safety limit against byte-level
// corruption, not a performance setting.
const unsigned long TX_PERIOD_MS = 25;

// Default full-scale sensitivities (+/-2 g, +/-250 deg/s). Identical on the
// MPU-6050 and the MPU-6500; the bench part is a 6500 (WHO_AM_I 0x70).
const float ACCEL_SENS = 16384.0;  // LSB/g
const float GYRO_SENS  = 131.0;    // LSB/(deg/s)

unsigned long nextTx = 0;

void writeReg(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.write(val);
  Wire.endTransmission(true);
}

void setup() {
  Wire.begin();
  Serial.begin(USB_BAUD);
  ble.begin(BLE_BAUD);

  writeReg(0x6B, 0x00);   // PWR_MGMT_1: wake (it boots asleep)
  writeReg(0x1B, 0x00);   // GYRO_CONFIG:  FS_SEL=0  -> +/-250 deg/s
  writeReg(0x1C, 0x00);   // ACCEL_CONFIG: AFS_SEL=0 -> +/-2 g
  delay(100);

  // Over USB only, never over the radio: the link is paced to a measured
  // ceiling and a banner is not a frame. Commaless either way, so a core
  // reading it would drop it.
  Serial.println(F("# veleta mpu_ble_hm10 0.1.0"));
  Serial.println(F("mpu_ble_hm10: HM-10 on (2,3) @38400, 40 Hz"));
  nextTx = millis();
}

void loop() {
  unsigned long now = millis();
  if ((long)(now - nextTx) < 0) return;
  // Advance by one period, but never accumulate a debt: if a frame ran
  // long, resync instead of firing a catch-up burst. A burst is exactly
  // the over-run this sketch exists to prevent.
  nextTx += TX_PERIOD_MS;
  if ((long)(now - nextTx) > 0) nextTx = now + TX_PERIOD_MS;

  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 14, true);

  int16_t ax = (Wire.read() << 8) | Wire.read();
  int16_t ay = (Wire.read() << 8) | Wire.read();
  int16_t az = (Wire.read() << 8) | Wire.read();
  Wire.read(); Wire.read();                     // temperature, discarded
  int16_t gx = (Wire.read() << 8) | Wire.read();
  int16_t gy = (Wire.read() << 8) | Wire.read();
  int16_t gz = (Wire.read() << 8) | Wire.read();

  // dtostrf, not Serial.print(v, 4): the whole frame must reach the radio
  // as one write, so its size is known and the pacing above means anything.
  char f[6][12], line[80];
  dtostrf(ax / ACCEL_SENS, 0, 4, f[0]);
  dtostrf(ay / ACCEL_SENS, 0, 4, f[1]);
  dtostrf(az / ACCEL_SENS, 0, 4, f[2]);
  dtostrf(gx / GYRO_SENS,  0, 4, f[3]);
  dtostrf(gy / GYRO_SENS,  0, 4, f[4]);
  dtostrf(gz / GYRO_SENS,  0, 4, f[5]);
  snprintf(line, sizeof(line), "%s,%s,%s,%s,%s,%s",
           f[0], f[1], f[2], f[3], f[4], f[5]);

  ble.println(line);
}
