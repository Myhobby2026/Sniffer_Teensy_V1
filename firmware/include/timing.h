#pragma once
#include <stdint.h>

namespace timing {

// Call once in setup()
void init();
void startOverflowTimer();

// Return 64-bit extended DWT cycle counter (nanosecond-ish: 1 tick = 1/600MHz)
uint64_t nowCycles();

// Safe read of cycle counter register (handles overflow race)
uint64_t nowCyclesSafe();

uint32_t cyclesToNs(uint64_t cycles, uint32_t fCpu);
uint64_t nsToCycles(uint64_t ns, uint32_t fCpu);

// For diagnostics
uint32_t getOverflowCount();

extern volatile uint32_t cyccntHi;

} // namespace timing

// ARM DWT CYCCNT register (Cortex-M7)
#define ARM_DWT_CYCCNT (*(volatile uint32_t*)0xE0001004)
#define ARM_DWT_CTRL   (*(volatile uint32_t*)0xE0001000)
#define ARM_DEMCR      (*(volatile uint32_t*)0xE000EDFC)
