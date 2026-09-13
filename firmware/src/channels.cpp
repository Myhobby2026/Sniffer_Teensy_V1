#include "channels.h"
#include <Arduino.h>
#include "config.h"

namespace channels {

ChannelConfig cfg[NUM_CHANNELS];
uint16_t enableMask = 0xFFFF;
uint16_t triggerRisingMask = 0;
uint16_t triggerFallingMask = 0;

void init() {
    for (int i = 0; i < NUM_CHANNELS; ++i) {
        uint8_t pin = CHANNEL_PHYS_PINS[i];
        pinMode(pin, INPUT); // no pull by default; host configures
        cfg[i].enabled = true;
        cfg[i].trigger = 0;
    }
    enableMask = 0xFFFF;
    triggerRisingMask = 0;
    triggerFallingMask = 0;

    // Cartridge ID pins as inputs with pullups
    pinMode(PIN_CARTRIDGE_ID0, INPUT_PULLUP);
    pinMode(PIN_CARTRIDGE_ID1, INPUT_PULLUP);
}

void applyMasks(uint16_t en, uint16_t rising, uint16_t falling) {
    enableMask = en;
    triggerRisingMask = rising;
    triggerFallingMask = falling;
    for (int i = 0; i < NUM_CHANNELS; ++i) {
        bool enCh = (en >> i) & 1;
        cfg[i].enabled = enCh;
        // Trigger type: derive from masks
        bool r = (rising >> i) & 1;
        bool f = (falling >> i) & 1;
        if (r && f) cfg[i].trigger = 3;
        else if (r) cfg[i].trigger = 1;
        else if (f) cfg[i].trigger = 2;
        else cfg[i].trigger = 0;
        // Optional: configure pull if needed (not yet)
        // pinMode could be changed here if host sends pull config
    }
}

uint8_t readCartridgeId() {
    uint8_t b0 = digitalRead(PIN_CARTRIDGE_ID0) ? 1 : 0;
    uint8_t b1 = digitalRead(PIN_CARTRIDGE_ID1) ? 1 : 0;
    return (b1 << 1) | b0; // 0..3, but pullups default to 0b11 if floating (no cartridge -> 3)
    // If no cartridge, we treat 3 as 0 (generic 3V3)
}

} // namespace channels
