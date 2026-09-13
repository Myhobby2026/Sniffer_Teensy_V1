#include "usb_protocol.h"
#include <Arduino.h>
#include <string.h>

namespace usb_protocol {

uint16_t nextTxSeq = 0;
uint16_t nextRxSeqExpected = 0;

uint16_t crc16(const uint8_t* data, size_t len, uint16_t init) {
    uint16_t crc = init;
    for (size_t i = 0; i < len; ++i) {
        crc ^= (uint16_t)data[i] << 8;
        for (int j = 0; j < 8; ++j) {
            if (crc & 0x8000) crc = (crc << 1) ^ 0x1021;
            else crc <<= 1;
        }
    }
    return crc;
}

size_t encode(uint8_t type, const uint8_t* payload, uint16_t payloadLen, uint16_t seq, uint8_t* outBuf) {
    outBuf[0] = (MAGIC & 0xFF);
    outBuf[1] = (MAGIC >> 8) & 0xFF;
    outBuf[2] = type;
    outBuf[3] = payloadLen & 0xFF;
    outBuf[4] = (payloadLen >> 8) & 0xFF;
    outBuf[5] = seq & 0xFF;
    outBuf[6] = (seq >> 8) & 0xFF;
    if (payloadLen && payload) memcpy(outBuf + HEADER_SIZE, payload, payloadLen);
    // CRC over TYPE+LEN+SEQ+PAYLOAD
    uint16_t crc = crc16(outBuf + 2, 1 + 2 + 2 + payloadLen);
    outBuf[HEADER_SIZE + payloadLen] = crc & 0xFF;
    outBuf[HEADER_SIZE + payloadLen + 1] = (crc >> 8) & 0xFF;
    return HEADER_SIZE + payloadLen + CRC_SIZE;
}

void sendPacket(uint8_t type, const uint8_t* payload, uint16_t len) {
    uint8_t frame[MAX_FRAME];
    size_t n = encode(type, payload, len, nextTxSeq++, frame);
    // Blocking write with chunking to avoid Serial buffer overflow (Teensy Serial buffer 64+)
    // Use Serial.write with availableForWrite check.
    size_t pos = 0;
    while (pos < n) {
        int avail = Serial.availableForWrite();
        if (avail <= 0) {
            // Yield to USB ISR
            yield();
            continue;
        }
        size_t chunk = n - pos;
        if ((int)chunk > avail) chunk = avail;
        Serial.write(frame + pos, chunk);
        pos += chunk;
    }
}

void sendStatus() {
    // STATUS payload 16B per spec
    uint8_t p[16];
    extern uint8_t g_state;
    extern uint32_t g_transitions;
    extern uint32_t g_bytesStreamed;
    p[0] = g_state;
    // fill pct approx from buffers
    // we estimate via buffers::getTotalPushed etc — caller may fill
    p[1] = 0; // fill pct computed elsewhere? set 0 for now, overwritten by caller wrapper
    // pending bytes not tracked simply → 0
    p[2] = 0; p[3] = 0;
    uint32_t tc = g_transitions;
    p[4] = tc & 0xFF; p[5] = (tc>>8)&0xFF; p[6]=(tc>>16)&0xFF; p[7]=(tc>>24)&0xFF;
    uint32_t bs = g_bytesStreamed;
    p[8]=bs&0xFF; p[9]=(bs>>8)&0xFF; p[10]=(bs>>16)&0xFF; p[11]=(bs>>24)&0xFF;
    // crcErrors/overruns — fetched from diagnostics if available
    p[12]=0; p[13]=0; p[14]=0; p[15]=0;
    sendPacket(PT_STATUS, p, 16);
}

void sendError(uint16_t code, const char* text) {
    uint16_t tlen = text ? strlen(text) : 0;
    if (tlen > 200) tlen = 200;
    uint8_t p[256];
    p[0]=code&0xFF; p[1]=(code>>8)&0xFF;
    p[2]=tlen&0xFF; p[3]=(tlen>>8)&0xFF;
    if (tlen) memcpy(p+4, text, tlen);
    sendPacket(PT_EVT_ERROR, p, 4+tlen);
}

// ── Decoder ──

Decoder::Decoder() { reset(); }
void Decoder::reset() {
    state = S_MAGIC1;
    curType=0; curLen=0; curSeq=0; payloadPos=0; recvCrc=0; crcErrors=0; framesDecoded=0;
}

bool Decoder::feed(uint8_t byte, uint8_t& outType, uint8_t* outPayload, uint16_t& outLen, uint16_t& outSeq) {
    switch (state) {
        case S_MAGIC1:
            if (byte == (MAGIC & 0xFF)) state = S_MAGIC2;
            break;
        case S_MAGIC2:
            if (byte == ((MAGIC>>8)&0xFF)) state = S_TYPE;
            else if (byte == (MAGIC & 0xFF)) state = S_MAGIC2; // stay
            else state = S_MAGIC1;
            break;
        case S_TYPE:
            curType = byte;
            state = S_LEN1;
            break;
        case S_LEN1:
            curLen = byte;
            state = S_LEN2;
            break;
        case S_LEN2:
            curLen |= (uint16_t)byte << 8;
            if (curLen > MAX_PAYLOAD) { crcErrors++; reset(); break; }
            state = S_SEQ1;
            break;
        case S_SEQ1:
            curSeq = byte;
            state = S_SEQ2;
            break;
        case S_SEQ2:
            curSeq |= (uint16_t)byte << 8;
            if (curLen == 0) state = S_CRC1;
            else { payloadPos = 0; state = S_PAYLOAD; }
            break;
        case S_PAYLOAD:
            payload[payloadPos++] = byte;
            if (payloadPos >= curLen) state = S_CRC1;
            break;
        case S_CRC1:
            recvCrc = byte;
            state = S_CRC2;
            break;
        case S_CRC2:
            recvCrc |= (uint16_t)byte << 8;
            {
                uint8_t crcData[1+2+2+MAX_PAYLOAD];
                crcData[0]=curType;
                crcData[1]=curLen &0xFF;
                crcData[2]=(curLen>>8)&0xFF;
                crcData[3]=curSeq &0xFF;
                crcData[4]=(curSeq>>8)&0xFF;
                if (curLen) memcpy(crcData+5, payload, curLen);
                uint16_t calc = crc16(crcData, 1+2+2+curLen);
                if (calc == recvCrc) {
                    outType = curType;
                    outLen = curLen;
                    outSeq = curSeq;
                    if (curLen && outPayload) memcpy(outPayload, payload, curLen);
                    framesDecoded++;
                    reset();
                    return true;
                } else {
                    crcErrors++;
                    reset();
                }
            }
            break;
    }
    return false;
}

// globals for status
uint8_t g_state = 0;
uint32_t g_transitions = 0;
uint32_t g_bytesStreamed = 0;

} // namespace usb_protocol
