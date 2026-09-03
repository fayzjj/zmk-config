/*
 * Piantor Pro BT - nice!view 12-image test slideshow
 * ZMK v0.3 / LVGL v8 style API
 *
 * The standard `nice_view` shield still provides the display hardware.
 * This companion shield only supplies the custom status-screen function.
 */
#include <zephyr/kernel.h>
#include <lvgl.h>
#include <zmk/display/status_screen.h>

LV_IMG_DECLARE(nv_art_01);
LV_IMG_DECLARE(nv_art_02);
LV_IMG_DECLARE(nv_art_03);
LV_IMG_DECLARE(nv_art_04);
LV_IMG_DECLARE(nv_art_05);
LV_IMG_DECLARE(nv_art_06);
LV_IMG_DECLARE(nv_art_07);
LV_IMG_DECLARE(nv_art_08);
LV_IMG_DECLARE(nv_art_09);
LV_IMG_DECLARE(nv_art_10);
LV_IMG_DECLARE(nv_art_11);
LV_IMG_DECLARE(nv_art_12);

static const lv_img_dsc_t *const slideshow_images[] = {
    &nv_art_01,
    &nv_art_02,
    &nv_art_03,
    &nv_art_04,
    &nv_art_05,
    &nv_art_06,
    &nv_art_07,
    &nv_art_08,
    &nv_art_09,
    &nv_art_10,
    &nv_art_11,
    &nv_art_12
};

#define SLIDESHOW_IMAGE_COUNT (sizeof(slideshow_images) / sizeof(slideshow_images[0]))
#define SLIDESHOW_PERIOD_MS 15000

static lv_obj_t *slideshow_obj;
static size_t slideshow_index;

static void slideshow_timer_cb(lv_timer_t *timer) {
    ARG_UNUSED(timer);

    slideshow_index = (slideshow_index + 1) % SLIDESHOW_IMAGE_COUNT;
    lv_img_set_src(slideshow_obj, slideshow_images[slideshow_index]);
}

lv_obj_t *zmk_display_status_screen(void) {
    lv_obj_t *screen = lv_obj_create(NULL);

    /* Keep the root clean and pure black on the 1-bit panel. */
    lv_obj_clear_flag(screen, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_style_border_width(screen, 0, LV_PART_MAIN);
    lv_obj_set_style_pad_all(screen, 0, LV_PART_MAIN);
    lv_obj_set_style_bg_opa(screen, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_bg_color(screen, lv_color_black(), LV_PART_MAIN);

    slideshow_obj = lv_img_create(screen);
    slideshow_index = 0;
    lv_img_set_src(slideshow_obj, slideshow_images[0]);

    /*
     * Native screen is 160x68 landscape.
     * 140x68 artwork starts at x=0.
     * x=140..159 stays black for the physical portrait top/status strip.
     */
    lv_obj_set_pos(slideshow_obj, 0, 0);

    lv_timer_create(slideshow_timer_cb, SLIDESHOW_PERIOD_MS, NULL);

    return screen;
}
