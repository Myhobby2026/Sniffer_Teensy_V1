#pragma once
#include <stdint.h>
#include "config.h"

namespace capture {

struct CaptureConfig {
    CaptureMode mode = MODE_TRANSITION;
    TriggerMode triggerMode = TRIG_IMMEDIATE;
    uint32_t sampleRateHz = 1000000; // for continuous
    uint32_t preTriggerMs = 0;
    uint32_t postTriggerMs = 0;
    uint16_t triggerPatternMask = 0;
    uint16_t triggerPatternValue = 0;
    uint8_t triggerEdgeCh = 0xFF; // 0..15 or 0xFF none
    uint8_t triggerEdgeType = 0; // 0 none,1 rising,2 falling,3 both
};

void init();
void setConfig(const CaptureConfig& c);
const CaptureConfig& getConfig();

bool start(); // returns false if already capturing or invalid config
void stop(const char* reason = "host");
void reset();

bool isCapturing();
DeviceState getState();

uint32_t getTransitionsCaptured();
uint32_t getBytesStreamed();

// Called from loop() — does polling and buffer management.
// Must be called frequently. Returns true if work done.
void poll();

// Called from main loop to flush USB queue (sends STATUS periodically etc.)
void serviceUsbTx();

// Hook for trigger pattern evaluation (used by poll)
bool evaluateTrigger(uint16_t prev, uint16_t cur);

} // namespace capture
