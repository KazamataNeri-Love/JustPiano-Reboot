# Decisions — 极简架构决策记录 (ADR)

> 仅记录不可逆或影响全局工程路线的关键决策。每条 ADR 保持简洁：背景、备选方案、结论与复审触发条件。

---

## ADR-001：改造技术路线 —— Smali 最小补丁 vs 源码级重建

- **状态**：`Proposed（Phase 0 静态体检已完成，待共同拍板）`
- **日期**：`2026-11-25`
- **背景**：目标为《极品钢琴 JustPiano》v4.3（`ly.pp.justpiano`，2016 年构建，单 DEX 1.5 MB），需先在现代安卓 1:1 跑通单机核心玩法（`v0-vanilla-runnable`），再推进全面屏虚拟画布适配与彻底离线化。
- **Phase 0 静态体检决策依据（已核实）**：
  - **Native `.so` 依赖**：**零核心游戏 `.so`**！仅 2 个 32 位第三方库（`libbspatch.so` 友盟增量更新、`liblocSDK3.so` 百度定位），剥离后应用为纯 Java/Dalvik（ABI 无关，可直接上纯 64 位 Android 14/15/16 设备）。
  - **代码规模与混淆度**：全 DEX 1,663 类中超过 70% 为死掉的第三方 SDK（友盟/广点通/腾讯分享/百度定位），**业务代码仅 `ly/pp/justpiano/*` 共 429 类**；Activity/View/SurfaceView 保留原名，内部类与方法为 ProGuard 混淆（`a`..`nk`）。
  - **渲染与触控集中度**：**极高**——游戏主循环与绘制集中在 `PlayView` + `q` + `by` + `KeyBoardView` + `an`；多指触控仅集中在 `jw.onTouch` 与 `am.onTouch` 两个监听器；音频全部集中于 `JPApplication`（`SoundPool` + 77 个 `.ogg`）。
  - **现代系统阻塞点**：v1-only 签名、`targetSdk=17`、32 位第三方 `.so`、Apache `DefaultHttpClient`（Android 9+ 移除）、`Environment.getExternalStorageDirectory()` 首启写 `/JustPiano/Skins/ReadMe.txt`（Scoped Storage）、百度定位/广点通/友盟死 SDK 初始化。
- **备选方案**：
  1. **方案 A：纯 Smali 最小补丁（Apktool 路线）**
     - 优点：最容易达成 Phase 1 的 1:1 行为对齐；无需修复 JADX 反编译语法错误或重构 119 个 XML。
     - 缺点：Phase 2 全面屏虚拟画布改造、多指坐标逆变换与 Phase 3 彻底剥离 1,200+ 死 SDK 类在 smali 层修改极易出错、难以维护与测试。
  2. **方案 B：直接源码级重建（JADX → 现代 Gradle 工程）**
     - 优点：一次到位，便于彻底剔除 70% 垃圾 SDK、升级 `targetSdk`/音频/高刷与虚拟画布。
     - 缺点：前期需先解决 ProGuard 混淆类还原、119 个布局/资源与 429 个业务类编译错误，距离拿到第一个 `v0-vanilla-runnable` 黄金对照版本周期较长，容易在无原版对照下引入逻辑偏差。
  3. **方案 C（推荐）：分阶段混合路线 —— Phase 1 Apktool/Smali 最小补丁快速拿 `v0-vanilla-runnable` 黄金基线 + 截图；Phase 2 起按需切 Gradle 源码级重建（仅保留核心单机链路与资产）**
     - 优点：
       - **Phase 1 极快落地**：用 Apktool 解包，仅做最小手术（剥离 `lib/armeabi/`、禁用百度定位/友盟更新/广点通初始化、补 `org.apache.http.legacy`、修复首启外部存储写入路径、补 `exported`/v2+ 重签），最快在现代真机/模拟器拿到 1:1 可运行基线并采集 `raw/golden/` 黄金对照截图。
       - **Phase 2/3 干净可控**：拿到 `v0-vanilla-runnable` 与黄金截图后，即可评估是“在 Smali 注入独立 Java/DEX 虚拟画布薄层”还是“抽取核心 15–20 个单机类重建干净的现代 Gradle 工程（直接复用原版 4,801 首 `.pm` 谱面 + 77 个 `.ogg` 音色 + 贴图）”。
     - 缺点：需准备 Apktool + Android Build-Tools（`apksigner`/`zipalign`）工具链（当前环境尚未安装，需在 Phase 1 首步就位）。
- **结论**：`待用户拍板（推荐方案 C）`
- **复审条件**：Phase 1 达成 `v0-vanilla-runnable` 并收齐 `raw/golden/` 截图后，结合实际反编译 `PlayView`/`jw`/`am` 的复杂度，复审 Phase 2 是继续薄层注入还是切换纯净 Gradle 源码工程。

---

## ADR-002：项目管理与版本托管方式 —— 本地文档驱动 vs GitHub Issues

- **状态**：`Accepted（已拍板）`
- **日期**：`2026-11-25`
- **背景**：确定本项目是接入 GitHub 仓库与 Issues/Milestones 跟踪，还是仅在本地使用 Git + Markdown 文档驱动。
- **备选方案**：
  1. **方案 A：纯本地 Git + Markdown 文档跟踪**
  2. **方案 B：GitHub 私有仓库 + Issues / Milestones**
- **结论**：**采用方案 A（仅本地管理）**。
  - 初始化本地 Git 单主干 `main`，严格遵守短分支 + 原子提交 + 里程碑 tag 纪律。
  - 通过 `.gitignore` 排除 `raw/*.apk` 与工作区既有 `res/`（避免 14 MB 二进制与受版权保护解包资产进入 Git 历史，原始指纹以 `docs/reverse-map.md` 的 SHA-256 锁定）。
- **复审条件**：若后续需要多人协作或异地云端备份，再评估是否推送纯自研代码/补丁至私有远程仓库。
