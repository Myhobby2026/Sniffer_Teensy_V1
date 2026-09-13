#pragma once
#include <stdint.h>
#include <stddef.h>

namespace usb_protocol {

static const uint16_t MAGIC = 0x534E; // "SN"
static const size_t HEADER_SIZE = 7; // MAGIC(2)+TYPE(1)+LEN(2)+SEQ(2)
static const size_t CRC_SIZE = 2;
static const size_t MAX_PAYLOAD = 1024;
static const size_t MAX_FRAME = HEADER_SIZE + MAX_PAYLOAD + CRC_SIZE;

// Packet types (must match Python side & spec)
enum PacketType : uint8_t {
    PT_HELLO            = 0x01,
    PT_HELLO_ACK        = 0x02,
    PT_GET_STATUS       = 0x03,
    PT_STATUS           = 0x04,
    PT_CONFIG_CHANNELS  = 0x05,
    PT_CONFIG_CAPTURE   = 0x06,
    PT_CMD_START        = 0x07,
    PT_CMD_STOP         = 0x08,
    PT_CMD_RESET        = 0x09,
    PT_EVT_STARTED      = 0x0A,
    PT_EVT_STOPPED      = 0x0B,
    PT_DATA_TRANSITION  = 0x0C,
    PT_DATA_SAMPLE      = 0x0D,
    PT_EVT_ERROR        = 0x0E,
    PT_PING             = 0x0F,
    PT_PONG             = 0x10,
};

// Error codes for EVT_ERROR
enum ErrorCode : uint16_t {
    ERR_BUFFER_OVERFLOW = 1,
    ERR_INVALID_CONFIG  = 2,
    ERR_USB_OVERRUN     = 3,
    ERR_TRIGGER_TIMEOUT = 4,
};

// CRC16 CCITT-FALSE poly 0x1021 init 0xFFFF
uint16_t crc16(const uint8_t* data, size_t len, uint16_t init = 0xFFFF);

// Encode a packet into outBuf (must have at least HEADER+len+CRC). Returns total bytes.
size_t encode(uint8_t type, const uint8_t* payload, uint16_t payloadLen, uint16_t seq, uint8_t* outBuf);

// Incremental decoder — call feed() per received byte.
// When a complete valid packet is assembled, returns true and fills outType/outPayload/outLen.
class Decoder {
public:
    Decoder();
    void reset();
    // Feed one byte; if packet complete, returns true
    bool feed(uint8_t byte, uint8_t& outType, uint8_t* outPayload, uint16_t& outLen, uint16_t& outSeq);
    uint32_t getCrcErrors() const { return crcErrors; }
    uint32_t getFramesDecoded() const { return framesDecoded; }
private:
    enum State { S_MAGIC1, S_MAGIC2, S_TYPE, S_LEN1, S_LEN2, S_SEQ1, S_SEQ2, S_PAYLOAD, S_CRC1, S_CRC2 };
    State state;
    uint8_t curType;
    uint16_t curLen;
    uint16_t curSeq;
    uint16_t payloadPos;
    uint8_t payload[MAX_PAYLOAD];
    uint16_t recvCrc;
    uint16_t calcCrc;
    uint32_t crcErrors;
    uint32_t framesDecoded;
    // temp for CRC calc accumulation we recompute at end for simplicity
    uint8_t headerForCrc[1+2+2]; // type+len+seq
};

void sendPacket(uint8_t type, const uint8_t* payload, uint16_t len);
void sendStatus();
void sendError(uint16_t code, const char* text);

extern uint16_t nextTxSeq;
extern uint16_t nextRxSeqExpected;

} // namespace usb_protocol
