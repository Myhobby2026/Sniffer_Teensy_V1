#include <Arduino.h>
#include "version.h"
#include "config.h"
#include "timing.h"
#include "channels.h"
#include "buffers.h"
#include "capture.h"
#include "usb_protocol.h"
#include "diagnostics.h"

// ─────────────────────────────────────────────
// Teensy 4.1 Sniffer — Phase 1 Main
// ─────────────────────────────────────────────

using namespace usb_protocol;

Decoder rxDecoder;
uint32_t lastStatusMs = 0;
uint8_t deviceStateMirror = 0;

void handleHostPacket(uint8_t type, uint8_t* payload, uint16_t len);

void setup() {
    // Teensy serial (USB CDC)
    Serial.begin(115200);
    // Wait a bit for host, but don't block forever (so standalone still works)
    uint32_t start = millis();
    while (!Serial && millis() - start < 1500) { delay(10); }

    timing::init();
    timing::startOverflowTimer();

    channels::init();
    buffers::init();
    capture::init();
    diagnostics::init();
    rxDecoder.reset();
    lastStatusMs = millis();

    // Brief LED hello
    for (int i=0;i<3;i++){ digitalWrite(PIN_LED,HIGH); delay(120); digitalWrite(PIN_LED,LOW); delay(120); }
}

void loop() {
    // ── RX: feed bytes to decoder ──
    while (Serial.available()) {
        uint8_t b = Serial.read();
        uint8_t ptype; uint8_t ppayload[MAX_PAYLOAD]; uint16_t plen, pseq;
        if (rxDecoder.feed(b, ptype, ppayload, plen, pseq)) {
            handleHostPacket(ptype, ppayload, plen);
        }
    }

    // ── Capture poll (fast) ──
    capture::poll();

    // ── USB TX: flush buffers ──
    capture::serviceUsbTx();

    // ── Periodic STATUS (2 Hz) while connected ──
    uint32_t now = millis();
    if (now - lastStatusMs >= 500) {
        lastStatusMs = now;
        // Build status payload
        uint8_t p[16];
        DeviceState st = capture::getState();
        p[0] = (uint8_t)st;
        // fill pct approx: totalPushed % buffer capacity? simplified
        uint32_t total = capture::getTransitionsCaptured();
        p[1] = (total % 100); // placeholder fill
        p[2]=0; p[3]=0;
        uint32_t tc = total;
        p[4]=tc &0xFF; p[5]=(tc>>8)&0xFF; p[6]=(tc>>16)&0xFF; p[7]=(tc>>24)&0xFF;
        uint32_t bs = capture::getBytesStreamed();
        p[8]=bs &0xFF; p[9]=(bs>>8)&0xFF; p[10]=(bs>>16)&0xFF; p[11]=(bs>>24)&0xFF;
        uint32_t crcE = rxDecoder.getCrcErrors();
        p[12]=crcE &0xFF; p[13]=(crcE>>8)&0xFF;
        uint32_t ov = buffers::getOverflowCount();
        p[14]=ov &0xFF; p[15]=(ov>>8)&0xFF;
        // mirror for diagnostics
        g_state = p[0];
        g_transitions = tc;
        g_bytesStreamed = bs;
        sendPacket(PT_STATUS, p, 16);
    }

    diagnostics::heartbeat();

    // Yield to USB stack; on Teensy, yield() pumps USB
    yield();
    // No delay — keep loop tight for polling
}

void handleHostPacket(uint8_t type, uint8_t* payload, uint16_t len) {
    switch (type) {
        case PT_HELLO: {
            // Respond with HELLO_ACK
            uint8_t ack[64];
            // FW_VERSION 4B
            ack[0]=FW_VERSION &0xFF; ack[1]=(FW_VERSION>>8)&0xFF; ack[2]=(FW_VERSION>>16)&0xFF; ack[3]=(FW_VERSION>>24)&0xFF;
            uint32_t hw = HW_VERSION;
            ack[4]=hw &0xFF; ack[5]=(hw>>8)&0xFF; ack[6]=(hw>>16)&0xFF; ack[7]=(hw>>24)&0xFF;
            uint32_t fcpu = F_CPU;
            ack[8]=fcpu &0xFF; ack[9]=(fcpu>>8)&0xFF; ack[10]=(fcpu>>16)&0xFF; ack[11]=(fcpu>>24)&0xFF;
            uint32_t ram = 1024*1024; // 1M approx
            ack[12]=ram &0xFF; ack[13]=(ram>>8)&0xFF; ack[14]=(ram>>16)&0xFF; ack[15]=(ram>>24)&0xFF;
            ack[16]=NUM_CHANNELS &0xFF; ack[17]=(NUM_CHANNELS>>8)&0xFF;
            ack[18]=channels::readCartridgeId();
            ack[19]=FW_CAPABILITIES;
            // device UID: use Teensy serial number area (simulated)
            const char* uid = "TEENSY41-SNIFFER-PH1";
            memset(ack+20, 0, 32);
            strncpy((char*)ack+20, uid, 31);
            sendPacket(PT_HELLO_ACK, ack, 52);
            break;
        }
        case PT_GET_STATUS: {
            uint8_t p[16];
            DeviceState st = capture::getState();
            p[0]=(uint8_t)st;
            p[1]=0; p[2]=0; p[3]=0;
            uint32_t tc=capture::getTransitionsCaptured();
            p[4]=tc&0xFF; p[5]=(tc>>8)&0xFF; p[6]=(tc>>16)&0xFF; p[7]=(tc>>24)&0xFF;
            uint32_t bs=capture::getBytesStreamed();
            p[8]=bs&0xFF; p[9]=(bs>>8)&0xFF; p[10]=(bs>>16)&0xFF; p[11]=(bs>>24)&0xFF;
            p[12]=0; p[13]=0; p[14]=0; p[15]=0;
            sendPacket(PT_STATUS, p, 16);
            break;
        }
        case PT_CONFIG_CHANNELS: {
            if (len < 6) { sendError(ERR_INVALID_CONFIG, "CONFIG_CHANNELS len<6"); break; }
            uint16_t en = payload[0] | (payload[1]<<8);
            uint16_t rising = payload[2] | (payload[3]<<8);
            uint16_t falling = payload[4] | (payload[5]<<8);
            channels::applyMasks(en, rising, falling);
            // ack with status? just ok
            break;
        }
        case PT_CONFIG_CAPTURE: {
            if (len < 20) { sendError(ERR_INVALID_CONFIG, "CONFIG_CAPTURE len<20"); break; }
            capture::CaptureConfig cfg;
            cfg.mode = (CaptureMode)payload[0];
            cfg.triggerMode = (TriggerMode)payload[1];
            cfg.sampleRateHz = payload[2] | (payload[3]<<8) | (payload[4]<<16) | (payload[5]<<24);
            cfg.preTriggerMs = payload[6] | (payload[7]<<8) | (payload[8]<<16) | (payload[9]<<24);
            cfg.postTriggerMs = payload[10] | (payload[11]<<8) | (payload[12]<<16) | (payload[13]<<24);
            cfg.triggerPatternMask = payload[14] | (payload[15]<<8);
            cfg.triggerPatternValue = payload[16] | (payload[17]<<8);
            cfg.triggerEdgeCh = payload[18];
            cfg.triggerEdgeType = payload[19];
            capture::setConfig(cfg);
            break;
        }
        case PT_CMD_START: {
            bool ok = capture::start();
            if (!ok) sendError(ERR_INVALID_CONFIG, "start failed (already capturing)");
            break;
        }
        case PT_CMD_STOP: {
            capture::stop("host_stop");
            break;
        }
        case PT_CMD_RESET: {
            capture::reset();
            rxDecoder.reset();
            break;
        }
        case PT_PING: {
            // echo nonce back as PONG
            sendPacket(PT_PONG, payload, len);
            break;
        }
        default: {
            // unknown — ignore but count?
            break;
        }
    }
}


