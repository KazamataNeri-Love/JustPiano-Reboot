# Reverse Map — 逆向考古地图

> 状态：`Phase 0 静态体检完成（只读分析）` | 更新日期：`2026-11-25`
> 原则：所有结论均基于对冻结原版 APK 的只读静态提取，未修改任何源码或执行重打包。

## 1. APK 基础指纹
| 字段 | 值 | 证据来源 |
| :--- | :--- | :--- |
| 原版文件路径 | `raw/JustPiano.apk`（只读冻结，源复制自 `res/JustPiano.apk`） | PowerShell `Get-Item` |
| 文件大小 (Bytes) | `14,715,397` Bytes (≈ 14.03 MB) | PowerShell `Get-Item` |
| SHA-256 | `FCCF7EE9816601F4833D5BB5A2419CFD3FA9782C6DFDA3003D4CC2B9781F9D66` | PowerShell `Get-FileHash` |
| Package Name | `ly.pp.justpiano`（实为国产经典安卓钢琴音游《极品钢琴 JustPiano》） | `AndroidManifest.xml` AXML 解码 |
| `versionCode` / `versionName` | `41` / `4.3` | `AndroidManifest.xml` AXML 解码 |
| 签名方案与证书摘要 | **仅 v1 JAR 签名**（无 `APK Sig Block 42` v2/v3 签名块）；`CN=tlypp, OU=b.n, O=Big Nose, L=潍坊, ST=山东, C=86`；算法 `SHA1withRSA` / 1024-bit RSA；证书 SHA-256：`85:65:8E:66:1B:D9:82:06:AC:89:54:9F:78:3A:0B:E4:81:95:67:FE:E2:A0:85:BE:C4:70:61:E9:2B:70:EB:AC` | `keytool -printcert` + ZIP 二进制检测 |
| 构建时间线索 | 证书签发 `2011-09-12`；ZIP 条目跨度 `2010-01-02` ~ `2016-06-06 08:16:12`；`classes.dex` 时间 `2016-06-06 08:16:06` | ZIP 中央目录 + `CERT.RSA` |

## 2. 技术栈与打包结构
- **开发框架 / 引擎**：**100% 纯 Java/Dalvik 原生 Android**（`SurfaceView` + 2D `Canvas` 游戏主渲染 + 传统 Android `View`/XML 布局），**无任何游戏核心 Native 引擎（无 Unity/Cocos/OpenGL）**。
- **DEX 概况**：单 DEX（`classes.dex`，`dex\n035`，1,516,728 Bytes；10,321 字符串 / 2,361 类型 / 12,192 方法 / 1,663 类）。
  - 业务代码：`ly/pp/justpiano/*` 共 **429 个类**（约占 25.8%）。
  - 混淆特征：**ProGuard 部分混淆**——所有 `Activity`/`Service`/`Application`/`View`/`SurfaceView`/`R$*` 保留原名，内部辅助类与非生命周期方法/字段混淆为 `a`..`nk`；无加固壳、无反调试加密。
- **关键第三方库（占 DEX 超 70%，均已过时/停服）**：
  - 友盟全套：`com.umeng.socialize` (443 类)、`common`/`socom`/`analytics`/`fb`/`update` (207 类)
  - 腾讯系：`com.qq.e` 广点通广告 (105 类 + `assets/gdt_plugin/gdtadv2.jar`)、`com.tencent.weibo`/`mm`/`open`/`stat`/`plus`/`tauth`/`qqconnect` (276 类)
  - 百度定位：`com.baidu.location` (44 类)
  - 旧支持库：`android.support.v4` (146 类)、`org.apache.http`（Apache HTTP 客户端）
- **资源与资产分布（共 5,640 个 ZIP 条目）**：
  - `assets/songs/`：**4,801 首内置 `.pm` 钢琴谱面**（离线可玩核心资产）
  - `assets/sound/`：**77 个内置 `.ogg` 钢琴单音采样**（`32.ogg` ~ `108.ogg` 连续无缺口）
  - `assets/drawable/`：59 张核心贴图（键盘、音符、判定图、背景、进度条）
  - `assets/mod/`：189 张换装/人物装扮 PNG
  - `res/`：492 个资源文件，含 119 个布局 XML（分布在 `layout`、`layout-h500dp-normal`、`layout-sw550dp-large`、`layout-v9`）

## 3. ABI 与 SDK 兼容性体检
- **SDK 声明**：`minSdkVersion = 7` (Android 2.1) / `targetSdkVersion = 17` (Android 4.2.2)
- **Native `.so` 清单（重大利好：零核心游戏 Native 依赖）**：
  | 库名 | 包含 ABI | 调用方（全 DEX 仅 2 处 `System.loadLibrary`） | 64 位缺口与风险评估 | 职责 |
  | :--- | :--- | :--- | :--- | :--- |
  | `libbspatch.so` (73,780 B) | 仅 `armeabi` (32 位) | `com.umeng.common.util.DeltaUpdate.<clinit>` | 剥离后无任何业务影响 | 友盟增量更新（已停服） |
  | `liblocSDK3.so` (40,319 B) | 仅 `armeabi` (32 位) | `com.baidu.location.Jni.<clinit>` | 剥离后无任何业务影响 | 百度定位 SDK（非游戏核心） |
  > **结论**：移除上述 2 个第三方 32 位 `.so` 及其 SDK 初始化调用后，应用将成为 **纯 Java/Dalvik ABI 无关包**，可在纯 64 位现代真机（Android 14/15/16）直接安装运行。
- **现代 Android（11–15+）安装与运行红旗项**：
  - [x] **v1-only 签名拦截**：无 v2/v3 签名块，Android 11+ 安装必拒，Phase 1 必须重签 v2/v3。
  - [x] **`targetSdkVersion=17` 过低拦截**：Android 14+ 要求 `targetSdk >= 23`（或通过 `adb install --bypass-low-target-sdk-block` 临时安装）。
  - [x] **32 位 `armeabi` `.so` 拦截**：现代纯 64 位设备拒绝加载 `armeabi` 包，必须剥离 `lib/armeabi/`（并阻断 `DeltaUpdate` / `baidu.location` 触发）。
  - [x] **Apache `DefaultHttpClient` 移除**：Android 9+ 默认移除 `org.apache.http`，需声明 `<uses-library android:name="org.apache.http.legacy" android:required="false"/>` 或在离线化阶段移除相关调用。
  - [x] **外部存储硬编码（Scoped Storage 冲突）**：`JustPiano.run()`、`JPApplication.b()`、`PianoPlay.a()/e()`、`RecordFiles` 等 11 个类直接调用 `Environment.getExternalStorageDirectory()` 读写 `/JustPiano/Skins`、`/JustPiano/Sounds/sound/`、`/JustPiano/Record/`。首启写 `/JustPiano/Skins/ReadMe.txt` 在 Android 10+ 可能异常。
  - [x] **Manifest 过期项**：`targetSdk >= 31` 时含 `<intent-filter>` 组件需显式声明 `android:exported`；此外原 `AndroidManifest.xml` 中 `OLSongsPage` 后存在游离 `<intent-filter>` 与重复权限声明（`ACCESS_FINE_LOCATION`/`ACCESS_COARSE_LOCATION`、`user-permission` 拼写错）。
  - [x] **强制横屏与权限膨胀**：所有游戏 Activity 锁定 `screenOrientation="0"`（横屏）；声明了定位、通话状态（`READ_PHONE_STATE`）、后台杀进程等大量广告/统计冗余权限。

## 4. 渲染与输入入口
- **核心离线游玩链路**：
  `JustPiano`（Launcher，首启建库/读屏参） → `MainMode`（主菜单） → `PlayModeSelect`（模式选择） → `MelodySelect`（本地曲库选歌） → `PianoPlay`（游玩宿主，装载 `PlayView` + `KeyBoardView`） → `PlayFinish`（结算）；另有自由弹奏入口 `KeyBoard`（装载 `KeyBoardView` + `an`）。
- **渲染管线**：
  - **主游玩画布**：`ly.pp.justpiano.PlayView`（继承 `SurfaceView`），在 `surfaceCreated()` 中启动 3 条线程：
    - `ly.pp.justpiano.q`（渲染线程：`SurfaceHolder.lockCanvas` / `unlockCanvasAndPost`，使用 `System.nanoTime()` + `sleep` 控帧，调用 `PlayView.a/b/c` 与 `Canvas.drawBitmap/drawArc/drawRoundRect`）
    - `ly.pp.justpiano.bz`（推进/节拍线程：`bz.sleep` + `JPApplication.d/E`）
    - `ly.pp.justpiano.ks`（特效/事件列表线程：`ks.sleep`）
    - `ly.pp.justpiano.by`（音符对象绘制器：`Canvas.drawBitmap`）
  - **其他自绘 View**：`JustPianoView.onDraw`（启动加载页）、`KeyBoardView.onDraw`（自由弹奏键盘）、`an.onDraw`（按键高亮/反馈层）。
  - **屏幕宽高获取点**：`JustPiano.onCreate()`、`PianoPlay.m()`、`MelodySelect.onCreate()` 调用 `getWindowManager().getDefaultDisplay().getMetrics(DisplayMetrics)`，写入 `JPApplication` 全局宽/高字段（由 `JPApplication.H()`/`I()` 供全应用读取）。
- **多指触控入口（高度集中，仅 2 处核心监听器）**：
  - 游玩界面：`ly.pp.justpiano.jw.onTouch`（在 `PlayView.surfaceCreated()` 通过 `setOnTouchListener` 绑定），读取 `MotionEvent.getAction()/getX()/getY()` 并回调 `PlayView.a()`。
  - 自由键盘：`ly.pp.justpiano.am.onTouch`，使用 `65280`（`0xFF00` = `ACTION_POINTER_INDEX_MASK`）解包多指事件，直接触发 `JPApplication.a()` 发声与 `an.a()` 刷新。
- **原版黄金分辨率基准（贴图实测证据）**：
  - 横屏基准分档：标准版按 **800px 宽** 设计（`background.png` 800×220、`bar.png` 800×16、`keyboard_long.png` 800×35、`progress_bar.png` 800×12、白键 `white_l/m/r.png` 100×250 × 8 键 = 800px、黑键 `black.png` 60×142）；HD 版按 **1280×720** 设计（`ground.png` 1280×720、`key_board_hd.png` 1280×400）。
  - 音符分档贴图：`*_note.png` (20×10)、`*_note_w.png` (32×16)、`*_note_qd.png` (36×18)、`*_note_hd.png` (48×24)。

## 5. MIDI / 谱面与音频后端
- **谱面格式（非标准 `.mid`，为自定义 `.pm` 钢琴谱格式）**：
  - 4,801 首内置谱面位于 `assets/songs/<字母>/<字母>/*.pm`（头行为 UTF-8 曲名 + `\n`，随后为二进制/参数节拍音符流），索引表见 `assets/songs/list`。
  - 解析器：`ly.pp.justpiano.kr`（`kr.i()` / `kr.a()` 通过 `AssetManager.open` + `BufferedReader.readLine` + `InputStream.read` 解析曲名、速度/时序与音符事件），首启由 `JustPiano.a()` 批量扫描写入 SQLite `data`/`jp_data`。
- **发声与音频管线**：
  - **纯 Android `SoundPool`**，全部封装在 `ly.pp.justpiano.JPApplication`（`onCreate`/`f` 初始化、`b`/`g` 加载、`a` 播放/停止、`e`/`f` 释放）。
  - 内置 77 个钢琴单音采样：`assets/sound/32.ogg` ~ `assets/sound/108.ogg`（连续对应 MIDI 音高 32–108）；亦支持读取外部扩展音色目录 `/JustPiano/Sounds/sound/*.ogg`。
- **录音功能**：`PianoPlay` 可选将麦克风录为 `/JustPiano/Record/buf.raw` 并转 `.wav`（`RECORD_AUDIO` 权限，非核心游玩必需）。
- **同步时钟源**：渲染线程 `q` 使用 `System.nanoTime()` + `Thread.sleep`；推进线程 `bz` 与特效线程 `ks` 各自使用 `Thread.sleep`（Phase 3 低延迟与高刷适配重点关注点）。

## 6. 联网与关服阻塞点
| 模块/触发时机 | 目标域名/IP 或接口 | 阻塞级别 | 证据位置 | Phase 1 最小绕过思路 |
| :--- | :--- | :--- | :--- | :--- |
| 在线大厅/对战长连接服务 | TCP NIO `SocketChannel` → `121.199.31.116` | 功能不可用（需确认是否随启即连） | `ConnectionService.run()` | 仅在线模式触发；Phase 1 确认不阻断单机，Phase 3 彻底禁用服务 |
| 在线账号/曲库/排行/换肤 HTTP API（20+ 接口） | `http://121.199.31.116:8910/JustPianoServer/server/*`（`LoginServlet`、`DownloadSong`、`ScoreUpload`、`GetSkinList` 等） | 在线模式不可用；`MainMode.onCreate` 引用 `icon.png` URL | `ag`/`aw`/`ay`/`dm`/`do`/`jt`/`kn`/`mb`/`mu`/`UsersInfo`/`MainMode` 等 | 保留单机离线主流程；声明 `org.apache.http.legacy` 防 Android 9+ `NoClassDefFoundError` |
| 百度定位 `:remote` 服务 | `http://loc.map.baidu.com/sdk.php` + `liblocSDK3.so` | **高危崩溃**（64 位无 `.so` + 定位权限） | `AndroidManifest.xml` (`com.baidu.location.f`) + `JPApplication.onCreate` | Phase 1 优先禁用/移除定位服务与初始化 |
| 广点通广告 / 友盟统计与增量更新 / QQ 分享 | `sdk.e.qq.com`、`au.umeng.com`、`alog.umeng.com`、`mta.qq.com` + `libbspatch.so` | **中危崩溃/卡顿**（明文 HTTP + 动态加载 `gdtadv2.jar` + 32 位 `bspatch`） | `JustPiano.onCreate`、`MainMode`、`bb`/`dh`/`le`/`ln`、`DeltaUpdate` | Phase 1 禁用动态插件/更新触发，防闪退；Phase 3 彻底剥离 |

## 7. 硬编码魔数语义表（严禁未标定即全局替换）
> 已扫描 `ly/pp/justpiano/*` 全部字节码常量；当前标定基于静态上下文，进入 Phase 2 修改前须反编译对应方法逐行二次核实。

| 数值 | 出现位置 (`类.方法`) | 语义归属 | 验证状态 | Phase 2 处置策略 |
| :--- | :--- | :--- | :--- | :--- |
| `480` | `PlayView.a()`（与 `540`、`720`、`key_board_hd`、`background_hd` 同方法） | **屏幕高度分档阈值**（选择普清/HD 贴图档位，非 MIDI PPQN） | 静态初判（待反编译源码二次核实） | 纳入虚拟画布资源选档策略 |
| `540` | `PlayView.a()`（与 `480`、`720` 并列） | **屏幕高度分档阈值**（qHD 960×540 档位） | 静态初判（待核实） | 同上 |
| `720` | `PlayView.a()`（与 `480`、`540` 并列） | **屏幕高度分档阈值**（HD 1280×720 档位） | 静态初判（待核实） | 同上 |
| `160` | `JustPianoView.onDraw()` | 待定（疑似 `Paint.setARGB` 色彩值 `12,160,251` 或基准 DPI） | **未核实**（极可能是 RGB 蓝色分量！） | **严禁误改**；反编译核实是否为颜色常量 |
| `250` | `PlayView.<init>()`（与 `100`、`200` 并列） | 待定（疑似判定窗口/动画时长或白键高度 250px） | **未核实** | 反编译核实语义后再定 |
| `100` / `100.0f` | `PlayView.<init>/c`、`by.a/c`、`am.onTouch`、`JPApplication.a`（SoundPool 音量）、`JustPiano.run`（加载进度 100%） | **多义重合值**：同时出现于音量百分比、加载进度、判定/坐标比例与白键宽度 | **未核实** | 严禁全局替换，必须逐方法拆解 |
| `320.0f` | `MelodySelect`/`OLMelodySelect`/`ShowSongsInfo`/`ShowTopInfo` `.onCreate()` | 疑似列表/侧栏宽度或字体/DPI 基准 | **未核实** | 结合对应 Layout XML 核实 |
| `400` | `SkinListPreference`/`SoundListPreference` `.onPrepareDialogBuilder()` | 弹窗高度或列表宽度像素值 | **未核实** | 仅涉及设置弹窗，Phase 2 改为 dp/约束 |
| `240` | `UsersInfo.a()` | 疑似头像裁剪尺寸（240×240） | **未核实** | 在线资料功能，离线化阶段可忽略 |
| `800` | `ly/pp/justpiano/*` 字节码中**未发现直接 `800` 立即数**（贴图本身宽 `800px`） | 贴图固有像素宽（运行时多通过 `Bitmap.getWidth()`/`JPApplication.H()` 计算） | 静态初判 | Phase 2 核查是否以 `Bitmap` 尺寸隐式驱动布局 |
