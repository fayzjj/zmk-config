# NiceView Auto Art（任意张 + 跳过未改动 + 按源文件分组历史）

这版在上一版基础上又加了两件事：

## 1）自动跳过没变的源图
脚本会按 `niceview_source/` 里的源图计算哈希。

如果某张图这次和上次完全一样：
- 不会重新做一次二值化/反色处理
- 会直接复用上次这张图已经生成好的 68×140 1-bit 结果

所以以后你：
- 改了 1 张图，只会重做那 1 张
- 其他没变的图会直接复用

## 2）历史结果按 source 文件名分组保存
除了按“每次运行”保存历史之外，还会按每张源图分组保存。

目录结构：

```text
niceview_generated_preview/
├── latest/
├── runs/
├── by_source/
│   ├── 01/
│   │   ├── latest_68x140_1bit.png
│   │   ├── latest.json
│   │   ├── history.json
│   │   └── versions/
│   │       ├── 20260904_120000_xxxxxxxx_68x140_1bit.png
│   │       └── ...
│   ├── 02/
│   └── ...
└── index.json
```

### 各目录作用

#### `latest/`
最新一次整批生成结果，方便你直接看：
- 单张 1-bit 图
- `CONTACT_SHEET.png`
- `manifest.json`

#### `runs/`
按“每次运行”保留历史，不覆盖旧结果：
- `run_0001_时间戳/`
- `run_0002_时间戳/`
- ...

每个 run 里都有：
- 当次全部单图
- `CONTACT_SHEET.png`
- `manifest.json`
- `generated_sources/art.c`
- `generated_sources/art_frames.h`

#### `by_source/`
按源文件名分组保存历史，非常适合长期研究单张图的变化：
- `latest_68x140_1bit.png`：当前这张源图最近一次处理后的结果
- `latest.json`：当前版本的元数据
- `history.json`：这张源图所有历史版本
- `versions/`：这张图过去每一次变化产生的 1-bit 图

---

## 现在的工作流

### 输入原图
放到：

```text
niceview_source/
```

支持任意张，按文件名排序。

### 自动生成给固件用的最新结果
输出到：

```text
boards/shields/nice_view_art/art.c
boards/shields/nice_view_art/art_frames.h
```

### 查看预览
直接看：

```text
niceview_generated_preview/latest/CONTACT_SHEET.png
```

如果想研究某一张图自己的历史：

```text
niceview_generated_preview/by_source/<文件名>/
```

如果想回看某一次整批生成：

```text
niceview_generated_preview/runs/
```

---

## RAW 模式
默认仍然是 RAW 模式。

即普通 PNG/JPG 会自动：
1. 裁切到 68×140
2. 提升对比度
3. 阈值二值化
4. 反色
5. 转成适合 NiceView 的数据

---

## 最适合你的用法

1. 往 `niceview_source/` 增删改图片  
2. push  
3. 等 GitHub Action 跑完  
4. 先看 `niceview_generated_preview/latest/CONTACT_SHEET.png`  
5. 满意再刷固件  

这样以后就不用每次都上键盘看第一次效果了。
