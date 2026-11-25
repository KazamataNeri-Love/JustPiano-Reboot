# Decisions — 极简架构决策记录 (ADR)

> 仅记录不可逆或影响全局工程路线的关键决策。每条 ADR 保持简洁：背景、备选方案、结论与复审触发条件。

---

## ADR-001：改造技术路线 —— Smali 最小补丁 vs 源码级重建

- **状态**：`Accepted（已拍板：方案 B 源码级重建）`
- **日期**：`2026-11-25`
- **背景**：目标为《极品钢琴 JustPiano》v4.3（`ly.pp.justpiano`，2016 年构建，单 DEX 1.5 MB），需先在现代安卓 1:1 跑通单机核心玩法（`v0-vanilla-runnable`），再推进全面屏虚拟画布适配与彻底离线化。
- **Phase 0 静态体检决策依据（已核实）**：
  - **Native `.so` 依赖**：**零核心游戏 `.so`**！仅 2 个 32 位第三方库（`libbspatch.so` 友盟增量更新、`liblocSDK3.so` 百度定位），剥离后应用为纯 Java/Dalvik（ABI 无关，可直接上纯 64 位 Android 14/15/16 设备）。
  - **代码规模与混淆度**：全 DEX 1,663 类中超过 70% 为死掉的第三方 SDK（友盟/广点通/腾讯分享/百度定位），**业务代码仅 `ly/pp/justpiano/*` 共 429 类**；Activity/View/SurfaceView 保留原名，内部类与方法为 ProGuard 混淆（`a`..`nk`）。
  - **渲染与触控集中度**：**极高**——游戏主循环与绘制集中在 `PlayView` + `q` + `by` + `KeyBoardView` + `an`；多指触控仅集中在 `jw.onTouch` 与 `am.onTouch` 两个监听器；音频全部集中于 `JPApplication`（`SoundPool` + 77 个 `.ogg`）。
  - **现代系统阻塞点**：v1-only 签名、`targetSdk=17`、32 位第三方 `.so`、Apache `DefaultHttpClient`（Android 9+ 移除）、`Environment.getExternalStorageDirectory()` 首启写 `/JustPiano/Skins/ReadMe.txt`（Scoped Storage）、百度定位/广点通/友盟死 SDK 初始化。
- **备选方案**：
  1. **方案 A：纯 Smali 最小补丁（Apktool 路线）**
     - 优点：最容易达成 Phase 1 的 1:1 行为对齐；无需处理反编译语法错误。
     - 缺点：Phase 2 全面屏虚拟画布与多指逆变换、Phase 3 剥离 1,200+ 死 SDK 类在 Smali 层维护成本极高。
  2. **方案 B（选定）：源码级重建（JADX 反编译 → 现代 Gradle 工程）**
     - 优点：直接剔除 70%+ 死第三方 SDK 与 2 个 32 位 `.so`；现代 Android Gradle/SDK 构建与单元测试体验最佳，便于 Phase 2 虚拟画布解耦与 Phase 3 音频/高刷现代化，且天然适配 Public 仓库（源码与原版资产彻底分离）。
     - 缺点：Phase 1 需完成核心单机类的反编译清理、去混淆命名与编译修复，拿到首个 `v0-vanilla-runnable` 的初期工作量大于 Smali 补丁。
  3. **方案 C：分阶段混合路线（Phase 1 Smali 基线 + Phase 2 转源码）**
     - 优点：最快拿到 `v0-vanilla-runnable`。
     - 缺点：存在工具链切换与双份维护成本。
- **结论**：**采用方案 B（源码级重建，现代 Gradle 工程）**，并附带以下执行约束：
  1. **Phase 1 范围收敛**：仅重建核心离线单机闭环（`JPApplication` → `JustPiano` → `MainMode` → `PlayModeSelect` → `MelodySelect` → `PianoPlay`/`PlayView`/`q`/`bz`/`ks`/`by`/`jw`/`kr` + `KeyBoard`/`KeyBoardView`/`an`/`am` + `PlayFinish`），**直接剥离**全部广告/统计/定位/分享/已关服联网 SDK，避免浪费精力修复死 SDK 编译错误。
  2. **严守红线 1**：Phase 1 重建过程中**1:1 保留原版渲染坐标系、画布绘制与布局比例**；在真机/模拟器跑通核心演奏并采集本地 `raw/golden/` 黄金对照截图、打 tag `v0-vanilla-runnable` 之前，**严禁**加入全面屏缩放或虚拟画布改动。
  3. **Public 仓库资产解耦**：仓库内严禁提交任何原版受版权保护资产（`.pm`/`.ogg`/原版贴图/APK）；提供本地资产提取脚本，由开发者构建前从 `raw/JustPiano.apk` 按需注入被 `.gitignore` 忽略的构建目录。
- **复审条件**：若 Phase 1 还原 `PlayView`/`kr`/`by` 等混淆类时遇到难以单靠静态分析对齐原版行为的歧义点，允许在本地借助原版 APK 或最小重签样本于模拟器取证对照（仅作黄金参考，不改变源码重建主线）。

---

## ADR-002：项目管理与版本托管方式 —— 本地文档驱动 vs GitHub Issues

- **状态**：`Accepted（已拍板：GitHub Public 仓库 + Issues / Milestones）`
- **日期**：`2026-11-25`
- **背景**：确定本项目是仅在本地以 Git + Markdown 文档驱动，还是托管至 GitHub 仓库并结合 Issues / Milestones 管理四阶段工作项。
- **备选方案**：
  1. **方案 A：纯本地 Git + Markdown 文档跟踪**
  2. **方案 B（选定）：GitHub Public 仓库 + Issues / Milestones**
- **结论**：**采用方案 B**，远程仓库锁定为 `https://github.com/KazamataNeri-Love/JustPiano-Reboot`（Public）。
  - 维持单主干 `main` + 短分支 + PR/1 轮盲审纪律，四阶段门禁映射为 4 个 GitHub Milestone（Phase 0 ~ Phase 3）。
  - **Public 仓库版权红线**：`.gitignore` 严格屏蔽 `raw/*`（仅保留 `raw/README.md` 与 `raw/golden/.gitkeep`）、`res/`、`*.apk`、`*.pm`、`*.ogg`、`*.so`、`*.dex`、`*.arsc` 以及 `raw/golden/` 截图，确保公开仓库**仅包含工程规范、逆向笔记、提取脚本与自研/重建代码**，原版 APK 仅通过 `docs/reverse-map.md` 中的 SHA-256 指纹留证。
- **复审条件**：每次向 `origin` 推送前必须通过 `git status` / `git ls-files` 核查，确保无任何受版权保护的原版二进制、谱面、采样或截图混入提交。
