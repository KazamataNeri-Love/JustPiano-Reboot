# Reverse Map — 逆向考古地图

> 状态：`Phase 1 核心类反编译与魔数核实完成（Issue #2）` | 更新日期：`2026-11-25`
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
> 已通过 JADX 1.5.7 反编译核心业务源码逐行二次核实，全部条目均已标定证据行号（`decompiled/sources/ly/pp/justpiano/`）。

| 数值 | 出现位置 (`文件:行`) | 语义归属 | 验证状态 | Phase 2 处置策略 |
| :--- | :--- | :--- | :--- | :--- |
| `480` / `540` / `720` | `PlayView.java:342-434` (`a()`) | **屏幕高度 `JPApplication.H()` 分档阈值**，决定加载普清/`_w`/`_qd`/`_hd` 贴图、判定线高度 `O` (`10.0f`/`12.5f`/`15.0f`) 与落速系数 `bi`（非 MIDI PPQN） | **已核实** | 纳入虚拟画布资源选档策略 |
| `160` | `JustPianoView.java:92` (`onDraw`) | **ARGB 颜色绿色分量**：`m.setARGB(255, 12, 160, 251)`（天蓝色文字，非 DPI） | **已核实** | **严禁改动** |
| `250` | `PlayView.java:238, 327` (`<init>`) | **ARGB 颜色绿色分量**：`az.setARGB(100, 200, 250, 100)`（浅绿色进度条底，非白键高度） | **已核实** | **严禁改动** |
| `12f` / `32f` / `62f` / `100f` | `PlayView.java:234-237, 320-323` (`<init>`) | **判定窗口乘数**：`aU`(Perfect) / `aV`(Cool) / `aW`(Great) / `aX`(Bad)，按 `fB * k * 10 * noteHeight / bi / 16` 换算 | **已核实** | Phase 2 在虚拟画布坐标系内等价换算，保持判定手感不变 |
| `100` / `100.0f` | `JPApplication.java:304`、`am.java:29,34,60,65,79,84`、`by.java:167,220`、`PlayView.java:1025`、`JustPiano.java:378,390` | **业务非屏幕常数**：SoundPool 音量百分比 (`0..100`) 与启动加载进度百分比 (`0..100`) | **已核实** | **严禁改动** |
| `35` | `PlayView.java:439`、`KeyBoard.java:234` | `keyboard_long.png` 高度 35px，用于算黑键高 `((H - 35) * 10) / 34` | **已核实** | Phase 2 统一接入虚拟画布高度基准 |
| `320.0f` | `MelodySelect.java:282`（及在线选曲页） | 广点通广告条 `BannerView` 宽度 `320dp × 50dp` | **已核实** | **Phase 1 随广告 SDK 直接剥离** |
| `400` | `SkinListPreference.java:98`（及 `SoundListPreference`） | `LinearLayout.setMinimumWidth(400)`（JADX 折叠为 `ErrorCode.NetWorkError.STUB_NETWORK_ERROR`） | **已核实** | 仅设置弹窗最小宽，Phase 2 改 dp |
| `240` | `UsersInfo.java:76-77` | 在线头像裁剪 `outputX/outputY = 240`（JADX 折叠为 `SocializeConstants.MASK_USER_CENTER_HIDE_AREA`） | **已核实** | 在线资料功能，**Phase 1 直接剥离** |
| `800` | 全业务源码无 `800` 立即数 | 仅作标准贴图固有宽（`800px`）；运行时坐标全部由 `JPApplication.I()`(宽) / `H()`(高) 按比例派生（`I/8`、`I/16`、`I*3/80`、`H/2 - O`、`H*10/34`、`I/120`） | **已核实** | **重大利好**：渲染与触控均集中依赖 `JPApplication.I()/H()`，Phase 2 虚拟画布接管点极干净 |

## 8. Phase 1 核心单机类映射表与重建边界（Issue `#2`）

### 8.1 `.pm` 谱面二进制格式规范（已核实：`kr.java`）
- **首行**：UTF-8 曲名 + `\n`（设 UTF-8 字节长度为 `o`）。
- **头部第 `o + 1` 字节**：速度/节拍系数 `k`（写入 `PlayView.R`，负值按无符号补码 `+256`）。
- **主体 `[o + 2 .. len - 3]`**：每 4 字节为 1 条音符事件（按 `(idx - o) % 4` 分组）：
  - `% 4 == 0`：`f[]` — MIDI 音高（`PlayView.bq`）
  - `% 4 == 1`：`i[]` — 力度/音量（`PlayView.bs`，0..100）
  - `% 4 == 2`：`g[]` — Delta Time 间隔（`PlayView.bp`）
  - `% 4 == 3`：`h[]` — 音轨/手别（`PlayView.br`，与 `PlayView.bn` 比对：0=右手主奏、1=左手）
- **尾部 2 字节**：`len - 2` 为时间步进乘数 `j`（`PlayView.aB`，负值 `+256`）；`len - 1` 除以 `10.0f` 为曲目难度 `p`。
- **现代 Android 修复点**：原版依赖 `AssetInputStream.reset()` 回退流；重建时应直接一次性读入 `byte[]` 再解析，消除不同 Android 版本 `AssetInputStream` 行为差异。

### 8.2 核心单机类映射（仅 ~48 个业务类，剔除 97% 死 SDK 与联网大厅）
| 分层 | 原类名 | 语义角色 | 关键依赖 / 布局 | Phase 1 处置 |
| :--- | :--- | :--- | :--- | :--- |
| 全局与音频 | `JPApplication` | 全局屏参 (`I()`/`H()`)、键位几何 (`u/v/w/x/y/z`)、`SoundPool` 音频引擎、设置项与贴图加载 | `assets/sound/32..108.ogg`、`assets/drawable/*.png` | **剥离** `com.baidu.location.*`、`UMSocialService`、`ConnectionService` 与 `j.a()` |
| 数据与谱面 | `is` / `i` / `kr` | SQLite (`jp_data` v36) / 分类与排序常量表 / `.pm` 谱面解析器 | `assets/songs/` (4,801 `.pm`) | 保留表结构与 1:1 解析逻辑；`kr` 改内存缓冲读取 |
| 启动与主菜单 | `JustPiano` / `al` / `JustPianoView` / `MainMode` / `PlayModeSelect` | 启动建库+载入 77 采样 → 主菜单 → 单机模式选择（演奏/练习/自由/试听/双排键盘） | `main_mode.xml`、`play_select.xml` | **剥离** `InterstitialAD`、`MobclickAgent`、`FeedbackAgent`、`UmengUpdateAgent`；将 `/JustPiano/Skins/ReadMe.txt` 改为 `getExternalFilesDir()` 并加容错 |
| 本地选曲 | `MelodySelect` / `bn` / `bo` / `mg` / `iq` / `jv` + 监听内部类 | 分类浏览、拼音/名称/难度/分数排序、搜索、后台试听线程 (`jv`) | `melodylist1`、`f_view`、`c_view`、`options`、`page_list`、`message_send` | **剥离** 广点通 `BannerView`（`320dp×50dp`）；修正原版 `S`/`T` 复选框误绑到 `R` 的反编译笔误核查（1:1 对照原版行为） |
| 核心演奏 | `PianoPlay` / `PlayView` / `KeyBoardView` / `q` / `bz` / `ks` / `kq` / `by` / `jw` / `jf` / `js` / `jb` / `jc` / `jd` | `SurfaceView` 主画布 + 渲染线程 `q` + 落键推进 `bz` + 判定动画 `ks`/`kq` + 音符 `by` + 触控 `jw` + 键盘高亮覆盖层 `KeyBoardView` | `pusedplay.xml` | **严守红线 1**：1:1 保留全部绘制坐标与触控逻辑；仅移除在线模式 `head=2/3`、`ConnectionService` 与 `MobclickAgent`；`PianoPlay` 继承 `Activity`（不再依赖 `BaseActivity`） |
| 自由双排键盘 | `KeyBoard` / `an` / `am` | 双排 8+8 白键自由弹奏 + 顶部八度滑条 + 2 指多点触控 (`0xFF00`) | 纯 Canvas 绘制 | 1:1 保留绘制与多指触控；仅移除 `MobclickAgent` |
| 结算与弹窗 | `PlayFinish` / `SettingsMode` / `m`/`l` / `ke`/`kf` / `ScrollText` | 结算写本地最高分至 SQLite / 偏好设置 / 自定义弹窗与加载框 | `finish.xml`、`mydialog.xml`、`prgdialog.xml` | 移除友盟分享与在线分数上传 (`head=1`) |

### 8.3 JADX 第三方常量折叠清单（Issue `#3` 剥离死 SDK 时必须还原）
| JADX 误折叠符号 | 实际字面量 | 出现位置 |
| :--- | :--- | :--- |
| `com.umeng.common.util.g.b` | `256` | `PlayView.aF`（无符号字节补码） |
| `com.umeng.socialize.bean.StatusCode.ST_CODE_SUCCESSED` | `200` | `PlayView.java:238,327`、`q.java:38`、`KeyBoard.java:174,253`（ARGB 颜色） |
| `com.umeng.socialize.common.SocializeConstants.PLATFORM_ID_TWITTER` | `12` | `JPApplication.java:173,475`、`an.java:77,163`（高音 C 键号 `12`） |
| `com.umeng.socialize.common.SocializeConstants.MASK_USER_CENTER_LOGIN_VERIFY` | `15` | `an.java:86,172`（下排黑键 C# 键号 `15`） |
| `com.umeng.socialize.a.b.b.as` | `"name"` | `JustPiano`、`MelodySelect`、`PianoPlay`、`PlayFinish`（SQLite 列名与 Intent key） |
| `com.qq.e.comm.constants.ErrorCode.InitError.INIT_AD_ERROR` | `500` | `JustPiano.m`（扫描计数步进） |
| `com.qq.e.comm.constants.ErrorCode.NetWorkError.STUB_NETWORK_ERROR` | `400` | `SkinListPreference.java:98`（弹窗最小宽） |

