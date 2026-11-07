# B站 Surge + BoxJS PCDN 兼容版（实验首版）

版本 2026.11.08.1。**实验首版，未在真实 iPhone/Surge 上验证。**
这是独立适配作品，不是 Sukka 或 Sparkle 官方版本。交付形式为一个 Surge 模块、一个 BoxJS 订阅配置和模块依赖的脚本。

## 已实现

- 在 Sparkle 原模块基础上，仅把三个播放接口移交兼容脚本：UGC PlayView、PlayViewUnite、PGC PlayView。
- 原 protobuf 响应规则排除这三个接口；其他去广告、JSON、空降助手等原有路径仍使用上游脚本。**不能与原 Sparkle B站模块同时开启。**
- 用 BoxJS 三个布尔开关控制新增功能总开关、PCDN 地址优化、脱敏诊断。总开关不控制原有去广告/端口规则。
- 默认仅诊断：优化关闭、诊断开启。识别已知 PCDN 后，只从该 DASH 音频/视频表示返回的备用地址中选已识别 HTTPS 镜像；保留完整签名和原主地址，不构造新 CDN URL。
- 原主地址放回 backupUrl，供客户端使用；**这不是已验证的主动失败回退机制**，地址可达性和 App 是否采用回退仍需真机验证。
- 缺少备用源、未知域名、不支持的结构保守放行；不拦视频大包、不加媒体域名 MITM，不添加新的 PCDN REJECT。
- 日志仅有版本、固定接口标签、模式和表示/命中/可替换/已替换/无备用计数。无完整 URL、签名、Cookie、token、视频 ID 或响应内容。每接口每 UTC 日期约100条（并发写非原子，不是严格安全配额）。

## 首版边界

仅普通 DASH 视频和 dash_audio。未实现分段流、Dolby/HiRes 特殊音轨、直播 CDN 优选、网页 DOM 功能、WebRTC SDK 替换、Thread Ripper、App「我的」原生开关；不解锁权限或画质。

Proto 字段以固定提交的社区定义核对，并非当前用户 iOS 抓包。未知字段保留但序列化字节顺序可能变化。播放响应上限2MiB；仅处理单个完整 unary gRPC 消息，gzip 先做头尾及大小预检，再检查解压后大小。这不是对恶意 gzip 的严格峰值内存隔离。异常时 `$done({})` 保留原响应，此时该请求的原 Sparkle 播放提示清理也不会执行。其他动态/评论响应不受新2MiB上限影响。

## 安装链接

- Surge 模块：https://raw.githubusercontent.com/laincat/Rules/main/Surge/Advertising/BilibiliPlus/Bilibili.Compatibility.sgmodule
- BoxJS 订阅：https://raw.githubusercontent.com/laincat/Rules/main/Surge/Advertising/BilibiliPlus/Bilibili.Compatibility.boxjs.json
- 完整对应源码：[Bilibili.Compatibility.Source.tar.gz](Bilibili.Compatibility.Source.tar.gz)
- 文件校验：[Bilibili.Compatibility.SHA256SUMS](Bilibili.Compatibility.SHA256SUMS)

以上为可更新的 main 链接。安装前应确认已停用原 Sparkle B站模块，原 BoxJS 模块保留。GitHub Release 的同名附件由仓库原有工作流发布；若流程尚未完成，以本目录为准。

设备使用：保留原 BoxJS 模块；停用原 Sparkle B站模块；导入此兼容模块（已有 Surge 参数按原设置填入）。在 BoxJS 订阅管理添加配置链接。先保持「地址优化」关闭，播放普通视频/番剧、切换清晰度和拖动，看 Surge 的 `bilibili.compat.playback` 脚本日志；`eligible>0` 只是发现可选镜像，不代表已实测可用。再短时打开优化，对比 `changed` 和播放表现。遇到播放问题先关闭优化；完全回滚则停用兼容模块、恢复原模块。若规则层原本已拦截原 PCDN 地址，保留地址不能绕过该规则。

MITM 复用原模块域名，但并不证明设备已成功解密；本任务没有修改设备网络/证书设置。不得为诊断扩大解密范围而不告知用户。BoxJS 只在本地保存设置，不新增远程日志上报。原 Sparkle 自身的其他网络功能保持其原有行为。

## 构建和测试

需要 Node、npm；所有依赖固定在 `sparkle/package-lock.json`。第一次运行：

```
cd sparkle
npm ci --ignore-scripts --cache /tmp/bili-npm-cache
XDG_CACHE_HOME=/tmp/bili-buf-cache node_modules/.bin/buf generate
node --import tsx add-pure-annotations.ts
cd ..
node build.mjs
sparkle/node_modules/.bin/tsc --noEmit -p sparkle/tsconfig.json
cd sparkle
node --import tsx --test ../tests/adapter.test.ts
```

发布构建时：`ASSET_BASE_URL=https://真实域名/目录 node build.mjs`。不设置则故意生成 review-only 模块。本工具不上传、不提交、不创建发布。

已修正 vendored Sparkle 的 `src/utils/index.ts` 中对不存在的 createMergedPoints 的再导出，便于完整类型检查；不改变该函数实际业务实现。

测试为合成 protobuf/gRPC fixture 与 Surge API 模拟，不是网络播放测试。验证分类边界、BoxJS 布尔值、缺省/关闭/回退、签名原文、未知字段、三个接口、gzip、异常放行、日志脱敏和限额、模块不重叠、原播放处理保留。

## 来源与许可

- Sparkle，GPL-3.0，固定 d513a2eeab382c640ccd5d6ecd76e07c4828b1ed：https://github.com/kokoryh/Sparkle 。兼容版整体按GPL-3.0提供；完整修改源码位于 sparkle/。
- Sukka 分类策略参考，MIT，Copyright (c) 2024 Sukka，c87b7e74aa420d845e36e00f24d812772d68f488：https://github.com/SukkaW/Make-Bilibili-Great-Than-Ever-Before 。没有复制其运行时/依赖。
- protobuf 字段参考，MIT，Copyright (c) 2022 aaa1115910，0e454c06e954b00df7a0a5a6873c9f18a7f9d0f5：https://github.com/aaa1115910/bv/tree/0e454c06e954b00df7a0a5a6873c9f18a7f9d0f5/bili-api/grpc/proto/bilibili 。三个接口 field1 -> stream_list5/dash_audio6，视频 base1/backup2、音频 base2/backup3。
- 三份许可见 licenses/；依赖许可在安装后的 node_modules 各包内，发布包同时附 THIRD_PARTY_LICENSES.txt。
- Sparkle dist URL 已锁提交，但原模块的 skin 脚本及 Chronos 等间接依赖仍随其上游更新，不能宣称全部外部行为冻结。
