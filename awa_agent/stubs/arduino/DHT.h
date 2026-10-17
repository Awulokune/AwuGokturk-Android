// Host-stub: DHT sicaklik/nem sensor kutuphanesi (gercek degil).
#ifndef AWU_DHT_HOST_STUB_H
#define AWU_DHT_HOST_STUB_H

#define DHT11 11
#define DHT22 22

class DHT {
 public:
  DHT(int pin, int type) {}
  void begin() {}
  float readTemperature() { return 0.0f; }
  float readHumidity() { return 0.0f; }
  float readTemperature(bool) { return 0.0f; }
  void readSensor() {}
  float temperature;
  float humidity;
};

#endif
