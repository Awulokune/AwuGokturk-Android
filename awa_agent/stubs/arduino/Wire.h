// Host-stub: I2C (Wire) kutuphanesi (gercek degil).
#ifndef AWU_WIRE_HOST_STUB_H
#define AWU_WIRE_HOST_STUB_H

#include <cstdint>
typedef uint8_t byte;

class TwoWire {
 public:
  void begin() {}
  void begin(int sda, int scl) {}
  void begin(int sda, int scl, uint32_t freq) {}
  void setClock(uint32_t) {}
  void beginTransmission(uint8_t address) {}
  void beginTransmission(int address) {}
  uint8_t endTransmission() { return 0; }
  uint8_t endTransmission(bool) { return 0; }
  uint8_t requestFrom(uint8_t address, uint8_t quantity) { return 0; }
  uint8_t requestFrom(int address, int quantity) { return 0; }
  size_t write(uint8_t) { return 1; }
  size_t write(const uint8_t *, size_t) { return 0; }
  int available() { return 0; }
  int read() { return -1; }
};
extern TwoWire Wire;

#endif
