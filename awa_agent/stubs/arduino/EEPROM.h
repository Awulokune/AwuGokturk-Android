// Host-stub: EEPROM kutuphanesi (gercek degil).
#ifndef AWU_EEPROM_HOST_STUB_H
#define AWU_EEPROM_HOST_STUB_H

#include <cstdint>
#include <cstddef>

class EEPROMClass {
 public:
  uint8_t read(int) { return 0; }
  void write(int, uint8_t) {}
  void update(int, uint8_t) {}
  template <typename T> T &get(int, T &t) { return t; }
  template <typename T> const T &put(int, const T &t) { return t; }
};
extern EEPROMClass EEPROM;

#endif
