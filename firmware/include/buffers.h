#pragma once
#include <stdint.h>
#include "config.h"

namespace buffers {

// Transition record (6 bytes packed, but aligned to 8 for speed)
struct TransitionRecord {
    uint16_t sample;    // packed 16-ch state after transition
    uint32_t delta;     // delta cycles since previous (first delta=0)
    // For file ordering, base timestamp stored per batch elsewhere
};

struct Buffer {
    TransitionRecord* data;
    uint32_t capacity;
    uint32_t count;
    uint64_t baseCycles; // absolute cycles of first record in this buffer
    bool full;
};

void init();

// Called from capture fast path — must be fast, no malloc.
bool pushTransition(uint16_t sample, uint32_t delta, uint64_t baseIfFirst);
bool isBufferFull();
void swapBuffers(); // capture side: swap active buffer
Buffer* getReadyBuffer(); // USB side: buffer ready to send (or nullptr)
void releaseReadyBuffer();

// Pre-trigger ring (circular, overwrites oldest)
struct RingBuffer {
    TransitionRecord* data;
    uint32_t capacity;
    uint32_t head; // next write
    uint32_t size; // number valid (≤capacity)
    uint64_t baseCycles; // not used per entry, global base
};
void ringInit();
void ringPush(uint16_t sample, uint32_t delta);
uint32_t ringSize();
void ringFlushToBuffers(); // on trigger: copy ring into main buffers

// Stats
uint32_t getOverflowCount();
uint32_t getTotalPushed();
void reset();

} // namespace buffers
