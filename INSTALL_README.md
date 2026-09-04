这个包是 NiceView 自动出图仓库增强版：

- 改成支持任意张图片
- 不再只有固定 9 张
- 每次生成都保留历史结果，不覆盖以前的输出
- 最新结果在 `niceview_generated_preview/latest/`
- 历史结果在 `niceview_generated_preview/runs/`

如果你要直接替换到自己的仓库：
1. 用这个包里的 `scripts/build_niceview_art.py` 覆盖旧文件
2. 用这个包里的 `NICEVIEW_AUTO_ART_README.md` 覆盖说明文档
3. 保留原本 workflow 即可（当前 workflow 已兼容）

看图最方便的入口：
`niceview_generated_preview/latest/CONTACT_SHEET.png`
