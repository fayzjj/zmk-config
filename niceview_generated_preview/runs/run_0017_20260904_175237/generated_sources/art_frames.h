#pragma once
#include <stdint.h>

extern const uint8_t nv_frame_01[1360];
extern const uint8_t nv_frame_02[1360];
extern const uint8_t nv_frame_03[1360];
extern const uint8_t nv_frame_04[1360];
extern const uint8_t nv_frame_05[1360];
extern const uint8_t nv_frame_06[1360];
extern const uint8_t nv_frame_07[1360];
extern const uint8_t nv_frame_08[1360];
extern const uint8_t nv_frame_09[1360];

static const uint8_t *const nv_frames[] = {
    nv_frame_01, nv_frame_02, nv_frame_03, nv_frame_04, nv_frame_05, nv_frame_06, nv_frame_07, nv_frame_08, nv_frame_09
};
#define NV_FRAME_COUNT 9
