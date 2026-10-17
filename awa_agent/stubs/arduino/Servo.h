// Host-stub: Servo kutuphanesi (gercek degil; sozdizimi icin).
#ifndef AWU_SERVO_HOST_STUB_H
#define AWU_SERVO_HOST_STUB_H

class Servo {
 public:
  Servo() {}
  uint8_t attach(int pin) { return 0; }
  uint8_t attach(int pin, int min, int max) { return 0; }
  void detach() {}
  void write(int angle) {}
  void writeMicroseconds(int us) {}
  int read() { return 0; }
  bool attached() { return true; }
};

#endif
