#pragma once
#include <stdint.h>

namespace diagnostics {

void init();
void setState(uint8_t state);
void heartbeat(); // call from loop, blinks LED per state

struct Stats {
    uint32_t transitionsCaptured;
    uint32_t bytesStreamed;
    uint32_t crcErrors;
    uint32_t overruns;
    uint32_t maxLoopUs;
    uint32_t uptimeMs;
};

Stats getStats();
void incOverrun();
void incCrcError();

} // namespace diagnostics
