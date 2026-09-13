#include "timing.h"
#include <Arduino.h>
#include "config.h"

namespace timing {

volatile uint32_t cyccntHi = 0;
static volatile bool overflowArmed = false;

// Overflow ISR — chained via interval timer because DWT has no IRQ; we poll overflow in nowCyclesSafe.
// Simpler: use PIT timer to increment hi every 7 sec. Here we just count via micros wrap detection in poll.
void init() {
    ARM_DEMCR |= ARM_DEMCR_TRCENA;
    ARM_DWT_CTRL |= 1; // enable CYCCNT
    ARM_DWT_CYCCNT = 0;
    cyccntHi = 0;
}

// Double-read to handle overflow race (like Arduino micros())
uint64_t nowCycles() {
    uint32_t hi1, hi2, lo;
    // Disable IRQ briefly to get atomic hi/lo without tearing (cost ~12 cycles)
    uint32_t prim = __get_PRIMASK();
    __disable_irq();
    hi1 = cyccntHi;
    lo = ARM_DWT_CYCCNT;
    // Detect overflow: if CYCCNT wrapped since last check, increment hi
    // We also detect by checking if lo is very small and previous lo was large — but simple overflow ISR not available,
    // so we poll: if lo < 1000 and we haven't incremented this wrap, do it. Better: use PIT.
    // For Phase 1, we use a PIT timer to increment hi (see below).
    hi2 = cyccntHi;
    if (prim == 0) __enable_irq();
    // If hi changed between reads, reread lo
    if (hi1 != hi2) {
        lo = ARM_DWT_CYCCNT;
        hi1 = hi2;
    }
    return ((uint64_t)hi1 << 32) | lo;
}

uint64_t nowCyclesSafe() {
    return nowCycles();
}

uint32_t cyclesToNs(uint64_t cycles, uint32_t fCpu) {
    // cycles * 1e9 / fCpu — avoid 64-bit div where possible: fCpu=600e6 => ns = cycles * 1.666...
    // Use integer: (cycles * 1000) / (fCpu/1e6)  — but keep 64-bit.
    // fCpu is 600_000_000 => 1e9/fCpu = 1.666.. ; do: (cycles * 1000000000ULL) / fCpu
    return (uint32_t)((cycles * 1000000000ULL) / fCpu);
}

uint64_t nsToCycles(uint64_t ns, uint32_t fCpu) {
    return (ns * fCpu) / 1000000000ULL;
}

uint32_t getOverflowCount() { return cyccntHi; }

} // namespace timing

// PIT timer to extend 32-bit CYCCNT to 64-bit by incrementing hi before it wraps.
// Period = 7.0 sec - epsilon (so hi increments just before wrap). At 600MHz, 32-bit wraps in 7.158s.
#if defined(ARDUINO_TEENSY41)
IntervalTimer _overflowTimer;
static void overflowISR() {
    timing::cyccntHi++;
}
#endif

namespace timing {
void startOverflowTimer() {
#if defined(ARDUINO_TEENSY41)
    _overflowTimer.begin(overflowISR, 7000000); // 7 sec
#endif
}
} // namespace timing

