// Host-stub: ESP32 WebServer (arduino-esp32). Gercek degil.
#ifndef AWU_ESP32_WEBSERVER_HOST_STUB_H
#define AWU_ESP32_WEBSERVER_HOST_STUB_H

#include <Arduino.h>
#include <WiFi.h>

#define HTTP_GET 1
#define HTTP_POST 2
#define HTTP_ANY 3

class WebServer {
 public:
  WebServer(uint16_t port) {}
  void begin() {}
  void handleClient() {}
  void on(const char *uri, int method, void (*fn)(void)) {}
  void on(const String &uri, int method, void (*fn)(void)) {}
  void send(int code, const char *content_type, const String &content) {}
  void send(int code, const char *content_type, const char *content) {}
  void stop() {}
};
typedef WebServer WiFiServer;

#endif
