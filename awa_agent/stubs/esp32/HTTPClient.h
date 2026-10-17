// Host-stub: ESP32 HTTPClient (arduino-esp32). Gercek degil.
#ifndef AWU_ESP32_HTTPCLIENT_HOST_STUB_H
#define AWU_ESP32_HTTPCLIENT_HOST_STUB_H

#include <Arduino.h>
#include <WiFi.h>

class HTTPClient {
 public:
  bool begin(const String &url) { return true; }
  bool begin(const char *url) { return true; }
  bool begin(WiFiClient &client, const String &url) { return true; }
  int GET() { return 200; }
  int POST(const String &payload) { return 200; }
  int POST(uint8_t *payload, size_t size) { return 200; }
  String getString() { return String(); }
  void addHeader(const String &name, const String &value) {}
  void setTimeout(uint16_t ms) {}
  void end() {}
  void setReuse(bool) {}
};
typedef HTTPClient HTTPClientClass;

#endif
