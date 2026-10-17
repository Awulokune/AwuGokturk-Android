// Host-stub: ESP32 WiFi kutuphanesi (arduino-esp32). Gercek degil.
#ifndef AWU_ESP32_WIFI_HOST_STUB_H
#define AWU_ESP32_WIFI_HOST_STUB_H

#include <Arduino.h>

#define WL_CONNECTED 3
#define WL_IDLE_STATUS 0
#define WIFI_STA 1
#define WIFI_AP 2

class IPAddress {
 public:
  String toString() const { return String(); }
};

class WiFiClient {
 public:
  int connect(const char *, uint16_t) { return 1; }
  int available() { return 0; }
  int read() { return -1; }
  void stop() {}
  bool connected() { return true; }
};

class WiFiClass {
 public:
  int begin(const char *ssid) { return 0; }
  int begin(const char *ssid, const char *pass) { return 0; }
  int status() { return WL_CONNECTED; }
  IPAddress localIP() { return IPAddress(); }
  void mode(int) {}
  void disconnect() {}
  String macAddress() { return String(); }
  int RSSI() { return -50; }
};
extern WiFiClass WiFi;

#endif
