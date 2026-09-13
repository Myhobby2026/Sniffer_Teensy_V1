#pragma once
#include <stdint.h>

// ─────────────────────────────────────────────
// Compile-time defaults — host can override at runtime via CONFIG_*
// ─────────────────────────────────────────────

#define NUM_CHANNELS 16

// Buffer sizing (tuned for Teensy 4.1 RAM: 512K DTCM + 512K OCRAM)
// Double buffer for streaming; ring for pre-trigger (OCRAM)
#define TRANSITION_BUFFER_ENTRIES 8192   // per buffer (entries of TransitionRecord)
#define USB_TX_BUFFER_BYTES       32768
#define PRE_TRIGGER_RING_ENTRIES  16384
#define MAX_BATCH_PAYLOAD         512    // bytes, fits within USB frame
#define MAX_FRAME_PAYLOAD         1024

// Timing
#ifndef F_CPU
#define F_CPU 600000000UL
#endif
#define TIMESTAMP_TICKS_PER_SEC F_CPU

// State enumeration
enum DeviceState : uint8_t {
    STATE_IDLE = 0,
    STATE_ARMED = 1,
    STATE_CAPTURING = 2,
    STATE_OVERFLOW = 3,
    STATE_ERROR = 4
};

// Capture mode
enum CaptureMode : uint8_t {
    MODE_TRANSITION = 0,
    MODE_CONTINUOUS = 1
};

enum TriggerMode : uint8_t {
    TRIG_IMMEDIATE = 0,
    TRIG_PATTERN   = 1,
    TRIG_PROTOCOL  = 2  // future
};

// ─────────────────────────────────────────────
// Pin map — see docs/02-pin-assignment.md
// Physical Teensy pins for logical CH0..CH15
// ─────────────────────────────────────────────
static const uint8_t CHANNEL_PHYS_PINS[NUM_CHANNELS] = {
    0,  1,  2,  3,  4,  5,  6,  7,   // CH0..CH7
    8,  9,  10, 11, 12, 13, 32, 33  // CH8..CH15 (13 is LED)
};

// Cartridge ID straps (optional)
#define PIN_CARTRIDGE_ID0 30
#define PIN_CARTRIDGE_ID1 31

// LED
#define PIN_LED 13
