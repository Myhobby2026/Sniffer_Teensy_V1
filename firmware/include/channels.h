#pragma once
#include <stdint.h>
#include "config.h"

namespace channels {

struct ChannelConfig {
    bool enabled = true;
    uint8_t trigger = 0; // 0 none,1 rising,2 falling,3 both
};

extern ChannelConfig cfg[NUM_CHANNELS];
extern uint16_t enableMask; // bit i = channel i enabled
extern uint16_t triggerRisingMask;
extern uint16_t triggerFallingMask;

void init();
void applyMasks(uint16_t en, uint16_t rising, uint16_t falling);

// Fast packed read: returns uint16 with bit i = logical CHi state (1=HIGH)
// Cost ~8-12 cycles. Must be inline.
inline uint16_t readPacked() {
    // Read port state registers directly.
    // On Teensy 4.1, GPIO6_PSR and GPIO7_PSR are the registers for our pins.
    // When not on Teensy hardware (unit test), fallback to digitalRead path via define.
#ifdef ARDUINO_TEENSY41
    uint32_t psr6 = GPIO6_PSR;
    uint32_t psr7 = GPIO7_PSR;
    // Unrolled extraction — matches pin map in config.h / docs/02
    uint16_t s = 0;
    s |= ((psr6 >> 3)  & 1u) << 0;  // pin 0  -> GPIO6 bit 3
    s |= ((psr6 >> 2)  & 1u) << 1;  // pin 1  -> GPIO6 bit 2
    s |= ((psr6 >> 4)  & 1u) << 2;  // pin 2  -> EMC_04 (GPIO6 bit 4)
    s |= ((psr6 >> 5)  & 1u) << 3;  // pin 3  -> EMC_05
    s |= ((psr6 >> 6)  & 1u) << 4;  // pin 4  -> EMC_06
    s |= ((psr6 >> 8)  & 1u) << 5;  // pin 5  -> EMC_08
    s |= ((psr6 >> 10) & 1u) << 6;  // pin 6  -> B0_10
    s |= ((psr6 >> 17) & 1u) << 7;  // pin 7  -> B1_01
    s |= ((psr6 >> 16) & 1u) << 8;  // pin 8  -> B1_00
    s |= ((psr6 >> 11) & 1u) << 9;  // pin 9  -> B0_11
    s |= ((psr6 >> 0)  & 1u) << 10; // pin 10 -> B0_00
    s |= ((psr6 >> 1)  & 1u) << 11; // pin 11 -> B0_01
    s |= ((psr6 >> 9)  & 1u) << 12; // pin 12 -> EMC_09
    s |= ((psr6 >> 7)  & 1u) << 13; // pin 13 -> EMC_07
    s |= ((psr7 >> 12) & 1u) << 14; // pin 32 -> B0_12 (GPIO7)
    s |= ((psr7 >> 13) & 1u) << 15; // pin 33 -> B0_13
    // Apply enable mask: disabled channels forced to 0 for trigger stability
    // But keep raw for debug? We keep raw and mask only where needed.
    return s & enableMask;
#else
    // Host / test fallback (slow)
    uint16_t s = 0;
    for (int i = 0; i < NUM_CHANNELS; ++i) {
        // In test, this function is stubbed
        (void)i;
    }
    return s;
#endif
}

// Helpers for trigger matching
inline bool matchesRising(uint16_t prev, uint16_t cur) {
    uint16_t rising = (~prev) & cur;
    return (rising & triggerRisingMask) != 0;
}
inline bool matchesFalling(uint16_t prev, uint16_t cur) {
    uint16_t falling = prev & (~cur);
    return (falling & triggerFallingMask) != 0;
}
inline bool matchesPattern(uint16_t sample, uint16_t mask, uint16_t value) {
    return (sample & mask) == value;
}

uint8_t readCartridgeId();

} // namespace channels
