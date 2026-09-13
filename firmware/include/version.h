#pragma once
#include <stdint.h>

#define FW_VERSION_MAJOR 1
#define FW_VERSION_MINOR 0
#define FW_VERSION_PATCH 0
#define FW_VERSION ((uint32_t)(FW_VERSION_MAJOR << 16 | FW_VERSION_MINOR << 8 | FW_VERSION_PATCH))
#define FW_VERSION_STR "1.0.0"

#define HW_VERSION_MAJOR 1
#define HW_VERSION_MINOR 0
#define HW_VERSION ((uint32_t)(HW_VERSION_MAJOR << 16 | HW_VERSION_MINOR))

#define FW_BUILD_DATE __DATE__
#define FW_BUILD_TIME __TIME__

// Capability bitmask reported in HELLO_ACK
#define CAP_TRANSITION  (1u << 0)
#define CAP_CONTINUOUS  (1u << 1)
#define CAP_DMA         (1u << 2)
#define CAP_FLEXIO      (1u << 3)

#define FW_CAPABILITIES (CAP_TRANSITION | CAP_CONTINUOUS)
