# Piantor Pro BT — Gallium + Seniply + Nice!View Art (V1.6)

这版以用户提供的 Claude 新版 Gallium + Seniply 配置为主体，
合并之前已在真机验证过的 Nice!View 右屏 9 图轮播与状态栏修正。

## V1.6 合并内容

### 来自 Claude 新版
- Gallium colstag BASE
- NUM / EXT / Shift / Space / SYM / Backspace 拇指分工
- 右外拇指 Backspace
- 左外下 Ctrl，右外下 RShift
- Caps Word
- Seniply EXT / SYM / NUM / FUN
- QWERTY GAME 层
- RShift 配合 Rime 做中英切换
- RGB underglow 编译期关闭
- 5 分钟 idle，1 小时 sleep
- 不启用 soft-off

### 保留之前已经真机验证的 Nice!View 修改
- 右半边 9 张之前的图片
- 图片位图保持之前真机显示正确的反色极性
- 顶部状态栏单独使用相反极性，保持黑底白色状态信息
- 实时右半边电量
- 实时左右连接状态
- V1.5.1 display listener init 链接修复

### 本版唯一新的显示参数
- 换图间隔：10 分钟（600000 ms）
- 上一测试版：10 秒（10000 ms）
- 定时换图唤醒频率降低到原来的 1/60

## GitHub Actions
为了继续保持编译快，build.yaml 只保留两个正式 target：
- piantor_pro_bt_left
- piantor_pro_bt_right

注意：因此本包没有 settings_reset target。
如果 ZMK Studio 的 settings 覆盖了新键位，可临时使用 Keebart 原仓库的
settings_reset target 清一次 settings，再恢复本 build.yaml。

## 安装
把本包内容覆盖到 Keebart/zmk-config fork 根目录后 push。
GitHub Actions 应生成左右两份 UF2。

## 说明
本包没有在本地完整 Zephyr/ZMK 工具链中实际链接编译；
已进行静态一致性检查。若 GitHub Actions 报错，请把错误末尾发回。
