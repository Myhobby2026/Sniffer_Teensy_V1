#include "diagnostics.h"
#include <Arduino.h>
#include "config.h"

namespace diagnostics {

static uint32_t overruns = 0;
static uint32_t crcErrs = 0;
static uint8_t currentState = 0;
static uint32_t lastBlinkMs = 0;
static bool ledOn = false;

void init() {
    pinMode(PIN_LED, OUTPUT);
    digitalWrite(PIN_LED, LOW);
    overruns = 0;
    crcErrs = 0;
    currentState = 0;
}

void setState(uint8_t s) { currentState = s; }

void heartbeat() {
    uint32_t now = millis();
    uint32_t interval = 1000;
    switch (currentState) {
        case 0: interval = 1000; break; // IDLE slow
        case 1: interval = 200; break;  // ARMED blink fast
        case 2: interval = 80; break;   // CAPTURING very fast
        case 3: interval = 500; break;  // OVERFLOW solid? we blink
        case 4: digitalWrite(PIN_LED, HIGH); return; // ERROR solid on
    }
    if (now - lastBlinkMs >= interval) {
        lastBlinkMs = now;
        ledOn = !ledOn;
        digitalWrite(PIN_LED, ledOn ? HIGH : LOW);
    }
}

Stats getStats() {
    Stats s;
    s.transitionsCaptured = 0; // filled by capture module via globals
    extern uint32_t g_transitions;
    // Actually we fetch via capture namespace? Use extern
    // We'll just return generic
    s.bytesStreamed = 0;
    s.crcErrors = crcErrs;
    s.overruns = overruns;
    s.maxLoopUs = 0;
    s.uptimeMs = millis();
    return s;
}

void incOverrun() { overruns++; }
void incCrcError() { crcErrs++; }

} // namespace diagnostics
