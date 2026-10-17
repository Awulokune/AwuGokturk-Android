// Host-stub: LiquidCrystal_I2C (gercek degil).
#ifndef AWU_LCD_HOST_STUB_H
#define AWU_LCD_HOST_STUB_H

#include <cstdint>
#include <cstddef>

class LiquidCrystal_I2C {
 public:
  LiquidCrystal_I2C(uint8_t addr, uint8_t cols, uint8_t rows) {}
  void init() {}
  void begin(uint8_t cols, uint8_t rows) {}
  void clear() {}
  void home() {}
  void setCursor(uint8_t col, uint8_t row) {}
  void print(const char *) {}
  void print(int) {}
  void print(double) {}
  void println(const char *) {}
  void backlight() {}
  void noBacklight() {}
  void display() {}
  void noDisplay() {}
  size_t write(uint8_t) { return 1; }
};

#endif
