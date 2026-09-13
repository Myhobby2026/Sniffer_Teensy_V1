#include "buffers.h"
#include <string.h>

namespace buffers {

// Statically allocated buffers — placed in DTCM by default (fast)
// For Teensy 4.1, DMAMEM would place in OCRAM; we keep in DTCM for now.

static TransitionRecord bufA[TRANSITION_BUFFER_ENTRIES];
static TransitionRecord bufB[TRANSITION_BUFFER_ENTRIES];
static TransitionRecord ringBuf[PRE_TRIGGER_RING_ENTRIES];

static Buffer buffers[2] = {
    {bufA, TRANSITION_BUFFER_ENTRIES, 0, 0, false},
    {bufB, TRANSITION_BUFFER_ENTRIES, 0, 0, false}
};
static int activeIdx = 0; // capture writes to this
static int readyIdx = -1; // buffer ready for USB (-1 none)

static RingBuffer ring = {ringBuf, PRE_TRIGGER_RING_ENTRIES, 0, 0, 0};

static uint32_t overflowCount = 0;
static uint32_t totalPushed = 0;

void init() {
    for (int i = 0; i < 2; ++i) {
        buffers[i].count = 0;
        buffers[i].full = false;
        buffers[i].baseCycles = 0;
    }
    activeIdx = 0;
    readyIdx = -1;
    ringInit();
    overflowCount = 0;
    totalPushed = 0;
}

void ringInit() {
    ring.head = 0;
    ring.size = 0;
    ring.baseCycles = 0;
}

bool pushTransition(uint16_t sample, uint32_t delta, uint64_t baseIfFirst) {
    Buffer &b = buffers[activeIdx];
    if (b.count == 0) {
        b.baseCycles = baseIfFirst;
    }
    if (b.count >= b.capacity) {
        // Buffer full — try to swap
        if (readyIdx == -1) {
            // Other buffer free, swap
            b.full = true;
            readyIdx = activeIdx;
            activeIdx = 1 - activeIdx;
            Buffer &nb = buffers[activeIdx];
            nb.count = 0;
            nb.full = false;
            nb.baseCycles = baseIfFirst;
            // Now push into new active
            nb.data[0] = {sample, delta};
            nb.count = 1;
            totalPushed++;
            return true;
        } else {
            // Both buffers full → overflow
            overflowCount++;
            return false;
        }
    } else {
        b.data[b.count++] = {sample, delta};
        totalPushed++;
        // If this write filled buffer, mark ready but don't swap yet — swap on next push to keep baseCycles correct
        if (b.count >= b.capacity) {
            b.full = true;
            // Don't swap immediately; next push will swap.
        }
        return true;
    }
}

bool isBufferFull() {
    return buffers[activeIdx].full;
}

void swapBuffers() {
    Buffer &b = buffers[activeIdx];
    if (b.count > 0 && readyIdx == -1) {
        b.full = true;
        readyIdx = activeIdx;
        activeIdx = 1 - activeIdx;
        buffers[activeIdx].count = 0;
        buffers[activeIdx].full = false;
    }
}

Buffer* getReadyBuffer() {
    if (readyIdx == -1) return nullptr;
    // If active buffer also full (edge case), we have two full — prioritize readyIdx
    return &buffers[readyIdx];
}

void releaseReadyBuffer() {
    if (readyIdx != -1) {
        buffers[readyIdx].count = 0;
        buffers[readyIdx].full = false;
        readyIdx = -1;
    }
}

void ringPush(uint16_t sample, uint32_t delta) {
    ring.data[ring.head] = {sample, delta};
    ring.head = (ring.head + 1) % ring.capacity;
    if (ring.size < ring.capacity) ring.size++;
    // baseCycles not tracked per entry for ring; caller manages base for flush
}

uint32_t ringSize() { return ring.size; }

void ringFlushToBuffers() {
    if (ring.size == 0) return;
    // Oldest entry index
    uint32_t start = (ring.head + ring.capacity - ring.size) % ring.capacity;
    for (uint32_t i = 0; i < ring.size; ++i) {
        uint32_t idx = (start + i) % ring.capacity;
        // delta is already relative; base for flush we use first entry delta=0 synthetic base
        // For simplicity, we push with delta as stored, and caller ensures baseCycles is set on first push.
        // The deltas in ring are already deltas from previous sample in ring capture, so replay is valid.
        // We use a dummy base 0 for first; second phase will fix timestamps to be contiguous.
        uint64_t base = (i == 0) ? 0 : 0; // base handled by pushTransition on first entry
        if (!pushTransition(ring.data[idx].sample, ring.data[idx].delta, base)) {
            overflowCount++;
            break;
        }
    }
    ring.size = 0;
    ring.head = 0;
}

uint32_t getOverflowCount() { return overflowCount; }
uint32_t getTotalPushed() { return totalPushed; }

void reset() {
    init();
}

} // namespace buffers
