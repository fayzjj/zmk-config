# NiceView RAW source images

把 9 张普通图片放在这个目录里，文件名按排序顺序决定轮播顺序，例如：

- `01.png`
- `02.png`
- ...
- `09.png`

支持 PNG / JPG / JPEG / WEBP / BMP。

当前仓库已经保留原来可用的 9 张编译后图片数据，所以仅添加这个目录不会改变屏幕。
当这里真正放入 9 张图片并 push 后，`Generate NiceView Art` workflow 会按 `niceview_art.json` 的 RAW 参数自动生成新的 `boards/shields/nice_view_art/art.c`。
