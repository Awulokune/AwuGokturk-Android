// Host-stub: SPI kutuphanesi (gercek degil).
#ifndef AWU_SPI_HOST_STUB_H
#define AWU_SPI_HOST_STUB_H

#include <cstdint>
typedef uint8_t byte;

class SPISettings {
 public:
  SPISettings() {}
  SPISettings(uint32_t, uint8_t, uint8_t) {}
};

class SPIClass {
 public:
  void begin() {}
  void end() {}
  void beginTransaction(SPISettings) {}
  void endTransaction() {}
  uint8_t transfer(uint8_t) { return 0; }
  void setBitOrder(uint8_t) {}
  void setDataMode(uint8_t) {}
  void setClockDivider(uint8_t) {}
};
extern SPIClass SPI;

#endif
