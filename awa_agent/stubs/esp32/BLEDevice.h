// Host-stub: ESP32 BLE (arduino-esp32 BLEDevice). Gercek degil.
#ifndef AWU_ESP32_BLE_HOST_STUB_H
#define AWU_ESP32_BLE_HOST_STUB_H

#include <Arduino.h>

class BLEServer;
class BLECharacteristic;

class BLEDeviceClass {
 public:
  void init(const char *name) {}
  BLEServer *createServer() { return nullptr; }
};
extern BLEDeviceClass BLEDevice;

#endif
