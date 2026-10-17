// AwuGokturk host-stub: Arduino cekirdek API'sinin taklidi.
// DIKKAT: Bu gercek Arduino/AVR basligi DEGILDIR. Yalnizca host uzerinde
// `g++ -fsyntax-only` ile sozdizimi dogrulamasi icin kullanilir. Avalon/gercek
// kutuphane davranisi yoktur.
#ifndef AWU_ARDUINO_HOST_STUB_H
#define AWU_ARDUINO_HOST_STUB_H

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <string>

typedef uint8_t byte;
typedef bool boolean;

#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define INPUT_PULLUP 2
#define RISING 3
#define FALLING 4
#define CHANGE 5
#define LSBFIRST 0
#define MSBFIRST 1
#define LED_BUILTIN 13
#define DEC 10
#define HEX 16
#define OCT 8
#define BIN 2

// Uno degerleri; sozdizimi icin yeterli (Mega icin de derlenir).
#ifndef A0
#define A0 14
#define A1 15
#define A2 16
#define A3 17
#define A4 18
#define A5 19
#define A6 20
#define A7 21
#define A8 22
#define A9 23
#define A10 24
#define A11 25
#define A12 26
#define A13 27
#define A14 28
#define A15 29
#endif

class String {
 public:
  String() {}
  String(const char *) {}
  String(int) {}
  String(long) {}
  String(unsigned long) {}
  String(double) {}
  String(const std::string &) {}
  const char *c_str() const { return ""; }
  unsigned int length() const { return 0; }
  int toInt() const { return 0; }
  double toDouble() const { return 0; }
  String &operator+=(const String &) { return *this; }
  bool operator==(const String &) const { return false; }
  bool operator!=(const String &) const { return true; }
  char operator[](int) const { return 0; }
};
inline String operator+(const String &, const String &) { return String(); }
inline String operator+(const String &, const char *) { return String(); }
inline String operator+(const char *, const String &) { return String(); }

class SerialClass {
 public:
  void begin(unsigned long) {}
  void end() {}
  void print(const char *) {}
  void print(const String &) {}
  void print(char) {}
  void print(int) {}
  void print(unsigned int) {}
  void print(long) {}
  void print(unsigned long) {}
  void print(double, int = 2) {}
  void println() {}
  void println(const char *) {}
  void println(const String &) {}
  void println(char) {}
  void println(int) {}
  void println(unsigned int) {}
  void println(long) {}
  void println(unsigned long) {}
  void println(double, int = 2) {}
  void printf(const char *, ...) {}
  template <typename T> void print(const T &) {}
  template <typename T> void println(const T &) {}
  int available() { return 0; }
  int read() { return -1; }
  String readStringUntil(char) { return String(); }
  void flush() {}
  operator bool() const { return true; }
};
extern SerialClass Serial;
extern SerialClass Serial1;
extern SerialClass Serial2;
extern SerialClass Serial3;

// ESP32 ek API'leri (Uno/Mega derlemesinde kullanilmaz; ortak stub'da tanimli).
void ledcSetup(int channel, double freq, int resolution_bits);
void ledcAttachPin(int pin, int channel);
void ledcWrite(int channel, int duty);
void ledcDetachPin(int pin);
void dacWrite(int pin, int value);
void analogSetWidth(int bits);
void analogSetAttenuation(int atten);

void pinMode(int pin, int mode);
void digitalWrite(int pin, int value);
int digitalRead(int pin);
int analogRead(int pin);
void analogWrite(int pin, int value);
void analogReference(int);
void analogReadResolution(int);
void delay(unsigned long ms);
void delayMicroseconds(unsigned int us);
unsigned long millis(void);
unsigned long micros(void);
long map(long x, long in_min, long in_max, long out_min, long out_max);
long constrain(long amt, long a, long b);
double constrain(double amt, double a, double b);
void tone(int pin, unsigned int frequency);
void tone(int pin, unsigned int frequency, unsigned long duration);
void noTone(int pin);
unsigned long pulseIn(int pin, int value);
unsigned long pulseIn(int pin, int value, unsigned long timeout);
int digitalPinToInterrupt(int pin);
void attachInterrupt(int interrupt, void (*isr)(void), int mode);
void detachInterrupt(int interrupt);
void interrupts(void);
void noInterrupts(void);
long random(long max);
long random(long min, long max);
void randomSeed(unsigned long seed);
int min(int, int);
long min(long, long);
int max(int, int);
long max(long, long);
void setup(void);
void loop(void);

#endif  // AWU_ARDUINO_HOST_STUB_H
