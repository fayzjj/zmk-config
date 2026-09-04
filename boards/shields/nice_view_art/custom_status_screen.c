/*
 * Piantor Pro BT V1.4 nice!view peripheral slideshow
 * - 9 images
 * - 10 s/image
 * - dynamic battery + split link status in physical top 20 px
 */
#include <zephyr/kernel.h>
#include <zephyr/bluetooth/services/bas.h>
#include <lvgl.h>
#include <string.h>

#include <zmk/display.h>
#include <zmk/display/status_screen.h>
#include <zmk/event_manager.h>
#include <zmk/events/battery_state_changed.h>
#include <zmk/events/split_peripheral_status_changed.h>
#include <zmk/split/bluetooth/peripheral.h>

extern const uint8_t nv_frame_01[1360];
extern const uint8_t nv_frame_02[1360];
extern const uint8_t nv_frame_03[1360];
extern const uint8_t nv_frame_04[1360];
extern const uint8_t nv_frame_05[1360];
extern const uint8_t nv_frame_06[1360];
extern const uint8_t nv_frame_07[1360];
extern const uint8_t nv_frame_08[1360];
extern const uint8_t nv_frame_09[1360];

static const uint8_t *const frames[] = { nv_frame_01, nv_frame_02, nv_frame_03, nv_frame_04, nv_frame_05, nv_frame_06, nv_frame_07, nv_frame_08, nv_frame_09 };
#define FRAME_COUNT 9
#define FRAME_PERIOD_MS 600000

static lv_obj_t *img_obj;
static uint8_t frame_index;
static uint8_t battery_level = 100;
static bool split_connected = false;

/* palette (8 bytes) + 160*68/8 bitmap bytes */
static uint8_t frame_map[8 + 1360] = {
#if CONFIG_NICE_VIEW_WIDGET_INVERTED
    0xff,0xff,0xff,0xff, 0x00,0x00,0x00,0xff,
#else
    0x00,0x00,0x00,0xff, 0xff,0xff,0xff,0xff,
#endif
};

static lv_img_dsc_t frame_dsc = {
    .header.always_zero = 0,
    .header.w = 160,
    .header.h = 68,
    .data_size = sizeof(frame_map),
    .header.cf = LV_IMG_CF_INDEXED_1BIT,
    .data = frame_map,
};

static inline void set_native_px(int x, int y, bool on) {
    if (x < 0 || x >= 160 || y < 0 || y >= 68) return;
    uint8_t *bits = &frame_map[8];
    size_t off = y * 20 + (x >> 3);
    uint8_t mask = (uint8_t)(1u << (7 - (x & 7)));
    if (on) bits[off] |= mask;
    else bits[off] &= (uint8_t)~mask;
}

/* Physical portrait coords sx=0..67, sy=0..19 -> native landscape. */
static inline void set_status_px(int sx, int sy, bool on) {
    int nx = 159 - sy;
    int ny = sx;

    /* Invert ONLY the runtime status strip polarity.
     * The 9 artwork frames are already correct on the physical keyboard.
     */
    set_native_px(nx, ny, !on);
}

static void status_clear(void) {
    for (int sy=0; sy<20; sy++)
        for (int sx=0; sx<68; sx++)
            set_status_px(sx, sy, false);
}

static void line(int x0,int y0,int x1,int y1) {
    int dx = (x1>x0)?1:(x1<x0?-1:0);
    int dy = (y1>y0)?1:(y1<y0?-1:0);
    int x=x0,y=y0;
    while (true) {
        set_status_px(x,y,true);
        if (x==x1 && y==y1) break;
        if (x!=x1) x+=dx;
        if (y!=y1) y+=dy;
    }
}

static void rect(int x0,int y0,int x1,int y1,bool fill) {
    if (fill) {
        for(int y=y0;y<=y1;y++) for(int x=x0;x<=x1;x++) set_status_px(x,y,true);
    } else {
        line(x0,y0,x1,y0); line(x0,y1,x1,y1); line(x0,y0,x0,y1); line(x1,y0,x1,y1);
    }
}

static void circle5(int cx,int cy) {
    set_status_px(cx-2,cy,true); set_status_px(cx+2,cy,true);
    set_status_px(cx,cy-2,true); set_status_px(cx,cy+2,true);
    set_status_px(cx-1,cy-2,true); set_status_px(cx+1,cy-2,true);
    set_status_px(cx-1,cy+2,true); set_status_px(cx+1,cy+2,true);
    set_status_px(cx-2,cy-1,true); set_status_px(cx-2,cy+1,true);
    set_status_px(cx+2,cy-1,true); set_status_px(cx+2,cy+1,true);
}

static const uint8_t digit3x5[10][5] = {
    {7,5,5,5,7}, {2,6,2,2,7}, {7,1,7,4,7}, {7,1,7,1,7}, {5,5,7,1,1},
    {7,4,7,1,7}, {7,4,7,5,7}, {7,1,1,1,1}, {7,5,7,5,7}, {7,5,7,1,7}
};

static void draw_digit(int x,int y,int d) {
    if (d<0 || d>9) return;
    for(int yy=0;yy<5;yy++)
        for(int xx=0;xx<3;xx++)
            if (digit3x5[d][yy] & (1 << (2-xx))) set_status_px(x+xx,y+yy,true);
}

static void draw_status(void) {
    status_clear();

    /* Link icon, left */
    circle5(6,9);
    circle5(11,9);
    line(8,9,9,9);
    if (split_connected) rect(16,8,17,9,true);
    else { line(15,6,18,11); line(18,6,15,11); }

    /* Numeric battery percentage, middle */
    uint8_t level = battery_level > 99 ? 99 : battery_level;
    draw_digit(26,7, level/10);
    draw_digit(31,7, level%10);

    /* Battery shell, right */
    int bx=45, by=5, bw=17, bh=9;
    rect(bx,by,bx+bw,by+bh,false);
    rect(bx+bw+1,by+2,bx+bw+2,by+bh-2,true);
    int fill = (13 * battery_level + 50) / 100;
    if (fill > 13) fill = 13;
    if (fill > 0) rect(bx+2,by+2,bx+1+fill,by+bh-2,true);
}

static void refresh_frame(void) {
    memcpy(&frame_map[8], frames[frame_index], 1360);
    draw_status();
    if (img_obj) {
        lv_img_set_src(img_obj, &frame_dsc);
        lv_obj_invalidate(img_obj);
    }
}

static void slideshow_cb(lv_timer_t *timer) {
    ARG_UNUSED(timer);
    frame_index = (frame_index + 1) % FRAME_COUNT;
    refresh_frame();
}

struct battery_status_state { uint8_t level; };

static void battery_update_cb(struct battery_status_state state) {
    battery_level = state.level;
    refresh_frame();
}

static struct battery_status_state battery_get_state(const zmk_event_t *eh) {
    ARG_UNUSED(eh);
    return (struct battery_status_state){ .level = bt_bas_get_battery_level() };
}

ZMK_DISPLAY_WIDGET_LISTENER(nv_battery, struct battery_status_state,
                            battery_update_cb, battery_get_state)
ZMK_SUBSCRIPTION(nv_battery, zmk_battery_state_changed);

struct link_status_state { bool connected; };

static void link_update_cb(struct link_status_state state) {
    split_connected = state.connected;
    refresh_frame();
}

static struct link_status_state link_get_state(const zmk_event_t *eh) {
    ARG_UNUSED(eh);
    return (struct link_status_state){ .connected = zmk_split_bt_peripheral_is_connected() };
}

ZMK_DISPLAY_WIDGET_LISTENER(nv_link, struct link_status_state,
                            link_update_cb, link_get_state)
ZMK_SUBSCRIPTION(nv_link, zmk_split_peripheral_status_changed);

lv_obj_t *zmk_display_status_screen(void) {
    lv_obj_t *screen = lv_obj_create(NULL);
    lv_obj_clear_flag(screen, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_style_border_width(screen, 0, LV_PART_MAIN);
    lv_obj_set_style_pad_all(screen, 0, LV_PART_MAIN);
    lv_obj_set_style_bg_opa(screen, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_bg_color(screen, lv_color_black(), LV_PART_MAIN);

    img_obj = lv_img_create(screen);
    lv_obj_set_pos(img_obj, 0, 0);

    battery_level = bt_bas_get_battery_level();
    split_connected = zmk_split_bt_peripheral_is_connected();
    frame_index = 0;
    refresh_frame();

    nv_battery_init();
    nv_link_init();

    lv_timer_create(slideshow_cb, FRAME_PERIOD_MS, NULL);
    return screen;
}
