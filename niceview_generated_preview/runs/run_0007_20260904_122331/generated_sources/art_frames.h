#pragma once
#include <stdint.h>

extern const uint8_t nv_frame_01[1360];
extern const uint8_t nv_frame_02[1360];
extern const uint8_t nv_frame_03[1360];

static const uint8_t *const nv_frames[] = {
    nv_frame_01, nv_frame_02, nv_frame_03
};
#define NV_FRAME_COUNT 3
