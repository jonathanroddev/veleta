/*
  hm10_config.ino
  ---------------
  Bring-up tool for the HM-10. It answers the two questions that cost the
  most time when a module arrives, then gets out of the way:

    1. WHICH PINS IS IT ON?  It sweeps every ordered (RX,TX) pair, sends a
       bare "AT" and reports which pair answers "OK".
    2. WHAT BAUD IS IT AT?   It tries the sweep at 9600 (factory) and at
       38400 (what this project needs).

  Then it becomes a transparent bridge between USB serial and the module,
  so AT commands can be typed straight into the serial monitor.

  DIALECT WARNING. The HM-10 is NOT an HC-05, and telling them apart saves
  hours: it answers `OK+Get:...`, takes commands with **no CR/LF
  terminator**, and its service/characteristic are 0xFFE0/0xFFE1. An HC-05
  answers `+NAME:...` + `OK` and wants a terminator. If you send AT with a
  terminator to an HM-10, half the commands come back empty and it looks
  broken. Set the serial monitor to "No line ending".

  It also answers slowly: a 150 ms wait finds nothing, 260 ms finds it.

  WHAT THIS PROJECT NEEDS
      AT+BAUD2      -> 38400. At the factory 9600 the UART, not the radio,
                       caps the link at ~21 frames/s instead of ~45.
      AT+NAME<name> -> the deviceId the core will use for this sensor.
                       No commas, no spaces.
    Check them with AT+BAUD? and AT+NAME?. AT+BAUD2 is persistent; revert
    with AT+BAUD0. Note that it breaks any other sketch still bridging at
    9600.

  AT only works while NOTHING is connected to the module over BLE.
*/

#include <SoftwareSerial.h>

const uint8_t PINS[] = {2,3,4,5,6,7,8,9,10,11,12,13,A0,A1,A2,A3};
const uint8_t N = sizeof(PINS)/sizeof(PINS[0]);
const long BAUDS[] = {38400, 9600};     // project baud first, then factory

uint8_t foundRx = 0, foundTx = 0;
long    foundBaud = 0;

bool probe(uint8_t rx, uint8_t tx, long baud) {
  SoftwareSerial s(rx, tx);
  s.begin(baud);
  delay(40);
  while (s.available()) s.read();
  s.print("AT");
  delay(280);                            // 150 ms is not enough. Measured.
  char buf[24]; uint8_t n = 0;
  while (s.available() && n < 23) buf[n++] = s.read();
  buf[n] = 0;
  s.end();
  return n && strstr(buf, "OK");
}

void setup() {
  Serial.begin(115200);
  delay(800);
  Serial.println();
  Serial.println(F("# veleta hm10_config 0.1.0"));
  Serial.println(F("=== hm10_config: looking for the module ==="));

  for (uint8_t b = 0; b < 2 && !foundBaud; b++) {
    Serial.print(F("-- trying ")); Serial.print(BAUDS[b]); Serial.println(F(" baud"));
    for (uint8_t i = 0; i < N && !foundBaud; i++)
      for (uint8_t j = 0; j < N && !foundBaud; j++)
        if (i != j && probe(PINS[i], PINS[j], BAUDS[b])) {
          foundRx = PINS[i]; foundTx = PINS[j]; foundBaud = BAUDS[b];
        }
  }

  if (!foundBaud) {
    Serial.println(F("NOT FOUND. Check power, wiring, and that nothing is"));
    Serial.println(F("connected to it over BLE (AT is dead while connected)."));
    return;
  }

  Serial.print(F("FOUND: module TX -> Arduino D")); Serial.print(foundRx);
  Serial.print(F(", module RX -> Arduino D")); Serial.print(foundTx);
  Serial.print(F(", at ")); Serial.print(foundBaud); Serial.println(F(" baud"));
  if (foundBaud != 38400)
    Serial.println(F("NOTE: not at 38400. Send AT+BAUD2, then re-run this."));
  Serial.println(F("=== bridge open: type AT commands (no line ending) ==="));
}

void loop() {
  static SoftwareSerial *link = NULL;
  if (!foundBaud) return;
  if (!link) { link = new SoftwareSerial(foundRx, foundTx); link->begin(foundBaud); }
  while (link->available()) Serial.write(link->read());
  while (Serial.available()) link->write(Serial.read());
}
