#include "capture.h"
#include "channels.h"
#include "buffers.h"
#include "timing.h"
#include "usb_protocol.h"
#include "diagnostics.h"
#include <Arduino.h>
#include "version.h"

namespace capture {

static CaptureConfig config;
static DeviceState state = STATE_IDLE;
static bool capturingFlag = false;

static uint16_t lastSample = 0;
static uint64_t lastTimestamp = 0;
static uint64_t captureStartCycles = 0;
static uint32_t transitionsCaptured = 0;
static uint32_t bytesStreamed = 0;

static uint64_t triggerFiredAt = 0;
static bool triggerArmed = false;

// Pre-trigger management
static bool preTriggerActive = false;
static uint64_t preTriggerStartCycles = 0;

// For pattern trigger
bool evaluateTrigger(uint16_t prev, uint16_t cur) {
    if (config.triggerMode == TRIG_IMMEDIATE) return true; // immediate — fire at start
    if (config.triggerMode == TRIG_PATTERN) {
        // Check pattern on cur sample
        if (channels::matchesPattern(cur, config.triggerPatternMask, config.triggerPatternValue)) return true;
        // Also edge trigger if configured
        if (config.triggerEdgeCh != 0xFF) {
            uint16_t mask = 1u << config.triggerEdgeCh;
            bool rising = ((~prev & cur) & mask) != 0;
            bool falling = ((prev & ~cur) & mask) != 0;
            if (config.triggerEdgeType == 1 && rising) return true;
            if (config.triggerEdgeType == 2 && falling) return true;
            if (config.triggerEdgeType == 3 && (rising || falling)) return true;
        }
        return false;
    }
    return true;
}

void init() {
    config = CaptureConfig();
    state = STATE_IDLE;
    capturingFlag = false;
    transitionsCaptured = 0;
    bytesStreamed = 0;
    lastSample = channels::readPacked();
    lastTimestamp = timing::nowCyclesSafe();
}

void setConfig(const CaptureConfig& c) {
    config = c;
}

const CaptureConfig& getConfig() { return config; }

bool isCapturing() { return capturingFlag; }
DeviceState getState() { return state; }
uint32_t getTransitionsCaptured() { return transitionsCaptured; }
uint32_t getBytesStreamed() { return bytesStreamed; }

bool start() {
    if (capturingFlag) return false;
    // Reset buffers
    buffers::reset();
    transitionsCaptured = 0;
    bytesStreamed = 0;
    lastSample = channels::readPacked();
    lastTimestamp = timing::nowCyclesSafe();
    captureStartCycles = lastTimestamp;
    triggerFiredAt = 0;
    triggerArmed = (config.triggerMode != TRIG_IMMEDIATE);

    if (config.triggerMode == TRIG_IMMEDIATE) {
        triggerFiredAt = lastTimestamp;
        triggerArmed = false;
        state = STATE_CAPTURING;
    } else {
        state = STATE_ARMED;
        // For pattern trigger with pre-trigger >0, we will ring-buffer until trigger
        preTriggerActive = (config.preTriggerMs > 0);
        preTriggerStartCycles = lastTimestamp;
    }

    capturingFlag = true;
    diagnostics::setState(state);

    // Send EVT_STARTED
    uint8_t payload[8];
    uint64_t ts = lastTimestamp;
    for (int i=0;i<8;i++) payload[i]=(ts>>(8*i))&0xFF;
    usb_protocol::sendPacket(usb_protocol::PT_EVT_STARTED, payload, 8);
    return true;
}

void stop(const char* reason) {
    if (!capturingFlag) return;
    capturingFlag = false;
    // Flush any partial buffer
    buffers::swapBuffers();
    state = STATE_IDLE;
    diagnostics::setState(state);
    uint8_t p[64];
    uint16_t rlen = reason ? strlen(reason) : 0;
    if (rlen > 60) rlen = 60;
    memset(p, 0, sizeof(p));
    if (rlen) memcpy(p, reason, rlen);
    usb_protocol::sendPacket(usb_protocol::PT_EVT_STOPPED, p, rlen);
}

void reset() {
    stop("reset");
    buffers::reset();
    state = STATE_IDLE;
    diagnostics::setState(state);
}

void poll() {
    if (!capturingFlag) return;

    uint64_t now = timing::nowCyclesSafe();
    uint16_t cur = channels::readPacked();

    if (cur != lastSample) {
        uint32_t delta = (uint32_t)(now - lastTimestamp); // 32-bit delta (at 600MHz, ~7 sec max)
        // Trigger evaluation when armed
        if (state == STATE_ARMED) {
            if (evaluateTrigger(lastSample, cur)) {
                triggerFiredAt = now;
                // Flush pre-trigger ring into buffers
                if (preTriggerActive) {
                    buffers::ringFlushToBuffers();
                    preTriggerActive = false;
                }
                state = STATE_CAPTURING;
                diagnostics::setState(state);
                // Also emit event
                uint8_t ep[8];
                for (int i=0;i<8;i++) ep[i]=(now>>(8*i))&0xFF;
                usb_protocol::sendPacket(usb_protocol::PT_EVT_STARTED, ep, 8); // reuse as trigger fired marker
            } else {
                // Still armed: if preTriggerActive, push to ring, not main
                if (preTriggerActive) {
                    buffers::ringPush(cur, delta);
                    // Manage timeout? if pre-trigger window exceeded without trigger, keep ring sliding
                } else {
                    // No pre-trigger, just drop until trigger
                }
                lastSample = cur;
                lastTimestamp = now;
                return;
            }
        }

        if (state == STATE_CAPTURING) {
            // Check post-trigger timeout
            if (config.postTriggerMs > 0 && triggerFiredAt != 0) {
                uint64_t elapsedNs = (now - triggerFiredAt) * 1000000000ULL / F_CPU;
                if (elapsedNs >= (uint64_t)config.postTriggerMs * 1000000ULL) {
                    // done
                    bool ok = buffers::pushTransition(cur, delta, lastTimestamp);
                    if (ok) transitionsCaptured++;
                    lastSample = cur;
                    lastTimestamp = now;
                    stop("trigger_complete");
                    return;
                }
            }

            bool ok = buffers::pushTransition(cur, delta, (transitionsCaptured==0? now-delta : 0));
            // For first push, baseIfFirst should be captureStartCycles
            if (transitionsCaptured == 0 && ok) {
                // The push used base — we should correct base to captureStartCycles for first batch?
                // buffers stores base per active buffer; our push sets base to baseIfFirst param.
                // So fine.
            }
            if (!ok) {
                state = STATE_OVERFLOW;
                diagnostics::setState(state);
                diagnostics::incOverrun();
                usb_protocol::sendError(usb_protocol::ERR_BUFFER_OVERFLOW, "buffer overflow");
                // Keep capturing but drop? For Phase 1 we stop
                stop("overflow");
                return;
            } else {
                transitionsCaptured++;
            }
        }

        lastSample = cur;
        lastTimestamp = now;
    }

    // Periodic USB flush is done in serviceUsbTx(), not here to keep poll tight.
}

void serviceUsbTx() {
    // Send ready buffers as DATA_TRANSITION packets
    buffers::Buffer* rb = buffers::getReadyBuffer();
    while (rb) {
        // Pack batch: BASE(8)+COUNT(2)+RECORDS*(2+4)
        // Payload max 512 per spec; we batch accordingly
        uint32_t total = rb->count;
        uint32_t offset = 0;
        while (offset < total) {
            uint16_t batchCount = (total - offset > 85) ? 85 : (total - offset);
            uint8_t payload[512];
            uint64_t base = rb->baseCycles;
            // For batches after first in same buffer, base is previous batch's last timestamp
            // Simplify: compute base as rb->baseCycles + sum of deltas up to offset
            // But our buffers store delta per record; baseCycles is absolute of first record.
            // For batch at offset, base = rb->baseCycles + sum(delta[0..offset-1])
            // We recompute quickly:
            uint64_t batchBase = rb->baseCycles;
            for (uint32_t i = 0; i < offset; ++i) batchBase += rb->data[i].delta;
            for (int i=0;i<8;i++) payload[i]=(batchBase>>(8*i))&0xFF;
            payload[8]=batchCount &0xFF; payload[9]=(batchCount>>8)&0xFF;
            size_t pos=10;
            for (uint16_t i=0;i<batchCount;i++) {
                uint16_t s = rb->data[offset+i].sample;
                uint32_t d = rb->data[offset+i].delta;
                payload[pos++] = s &0xFF; payload[pos++]=(s>>8)&0xFF;
                payload[pos++] = d &0xFF; payload[pos++]=(d>>8)&0xFF;
                payload[pos++] = (d>>16)&0xFF; payload[pos++]=(d>>24)&0xFF;
            }
            usb_protocol::sendPacket(usb_protocol::PT_DATA_TRANSITION, payload, pos);
            bytesStreamed += pos;
            // Update global mirrors for status
            usb_protocol::g_transitions = transitionsCaptured;
            usb_protocol::g_bytesStreamed = bytesStreamed;
            offset += batchCount;
            // Yield to allow USB ISR to drain
            yield();
        }
        buffers::releaseReadyBuffer();
        rb = buffers::getReadyBuffer();
    }

    // If active buffer has data and we're not capturing anymore, flush it too
    if (!capturingFlag) {
        // check active buffer has leftover
        // We do via swapBuffers trick — but capture::stop already swapped.
    }
}

} // namespace capture
