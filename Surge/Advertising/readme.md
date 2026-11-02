# 红果模块与直播插播诊断

日常使用 [HongGuo.sgmodule](HongGuo.sgmodule)。它保留原有域名拦截与 DIRECT 例外，不需要 JS、MITM 或证书。本次只删除 6 条已被较早同策略规则覆盖的规则：51 条精简到 45 条，保留原顺序，没有扩大拦截范围。原生域名匹配不需要缓冲响应；改成 JS 不会天然更快。没有手机 CPU、耗电或延迟实测。

两天测试使用 [HongGuo.Diagnostic.sgmodule](HongGuo.Diagnostic.sgmodule)。它包含相同的 45 条规则，可以替代正式版，另外检查一个候选接口的响应结构。**直播插播尚未修好：诊断脚本不修改响应，也不阻断直播媒体。**

## 导入与回退

- [正式版固定下载地址](https://github.com/laincat/Rules/releases/download/latest/HongGuo.sgmodule)
- [Diagnostic 诊断版固定下载地址](https://github.com/laincat/Rules/releases/download/latest/HongGuo.Diagnostic.sgmodule)
- [诊断脚本源码](HongGuo.Diagnostic.js)

1. 停用原 `HongGuo.sgmodule`，再导入并启用 Diagnostic；两者不要同时启用。与 `Advertising.sgmodule` 同用时红果模块排在前面，但对方的 `pre-matching` 仍可能先匹配。其他覆盖相同请求的响应脚本也可能冲突：Surge 对同一个响应只执行第一个匹配的响应脚本。
2. 诊断版仅通过 `hostname = %APPEND%` 追加下面 4 个精确主机，不覆盖其他 hostname，不加通配符。手机上必须已有正确配置和信任的 Surge MITM 证书，并启用相应功能，才能观察 HTTPS 响应结构。模块不安装、更换证书，也不设置 MITM 的全局开关。
3. 正常看剧，发生正片中途直接切进直播间时，记下大致时间、集数和操作。请求失败、播放异常或疑似证书固定问题时，立刻停用 Diagnostic、恢复正式版；不要为了诊断关闭 TLS 验证。
4. 两天后停用 Diagnostic，重新启用正式版。停用后该模块追加的 MITM 主机和脚本不再生效；其他配置原来已设置的主机保持原状。日志由 Surge 管理，导出后可在其日志界面清理。

精确 MITM 主机：

```text
api3-normal.fqnovel.com
api5-normal.fqnovel.com
api3-normal-lq.fqnovel.com
api5-normal-lq.fqnovel.com
```

这会使 Surge 在手机本地解密上述主机的 HTTPS 流量，主机上可能还有正常业务与账号流量。脚本仅匹配下面这个固定路径，不发送任何网络请求，不读取请求头或响应头，不上传日志。

## 日志与边界

脚本名是 `hongguo-live-diagnostic`。打开 Surge 的脚本日志，找到这个脚本，将两天测试期间的日志复制或导出为文本，附上发生直播跳转的大致时间。只分享这个脚本的日志，不需要导出完整抓包、请求正文或配置文件。日志是每行一条 JSON；Surge 可能另外加上时间前缀。脚本只用 `console.log` 写入本地脚本日志，不写下载目录或另建远端日志服务。

日志包含诊断版本、UTC 时间、去查询参数后的固定主机/路径、白名单字段的位置/类型及计数。未知字段名显示为 `*`，数组索引显示为 `[]`；不记录字段值、URL 查询、Cookie、Token、用户 ID、账号数据或响应正文。UTC 时间与手机显示的本地时间可能有时区差，请保留日志原时间。

日志版本为 `2026.11.02.1`。顺序执行时每个 UTC 日最多 24 条、全局至少间隔 60 秒、同一主机同一结构至少间隔 30 分钟；下一 UTC 日自动恢复每日预算，跨日仍保留未结束的冷却时间。系统时钟回退时暂停记录，直到时间追上已观察的时间。单条日志最多 8192 字符；固定持久状态最多 4096 字符，仅保存版本、日/时间戳、饱和计数及最多 24 个脱敏结构指纹，不累计正文或日志。Surge 持久存储没有原子比较更新接口，并发执行可能短时超过限额或少计数，因此这些是尽力限制，计数不能当成广告次数或精确流量统计。

`observedParsedResponsesToday` 是当日已解析的匹配响应计数，`observedTargetFieldHitsToday` 是有界遍历找到的目标字段次数，`loggedResponsesToday` 是当日已发日志计数；`observedTargetFieldHitsInResponse` 和字段的 `hits` 只描述当前响应，计数最多 999999。被限频但可解析的响应仍计入当日观察数。`truncated=true` 表示遍历或日志字段已裁剪。

达到预算不等于关闭 MITM、停止响应缓冲或停止统计解析。`requires-body=true` 会缓冲匹配的响应，`max-size=262144` 限制为 256 KiB，超限由 Surge 跳过脚本并透传。脚本另限制为 5000 个节点、16 层深度、每节点 128 个子项及 32 个结构项，未知结构、解析失败及持久化失败均原样放行。持久状态损坏时也会停止记录而不回显错误内容。测试结束后请停用诊断版。

**没有日志不代表没有广告。** 可能是 iOS 没有请求这个 Android 候选路径、请求未进入 MITM、响应超过上限、其他脚本先匹配、日志预算或限频生效，也可能发生了证书固定失败。空字段日志只说明本次采样未找到预定义字段，不说明响应没有广告。出现字段也不说明它控制直播插播，仍需结合跳转时间和后续证据确认。

## 候选依据

候选路径只有 `/novel/player/video_detail/v1/`。[Android 客户端 `HgApp::detail` 源码](https://github.com/ziyu4huang/guoapp/blob/76304b2f1ae41b352d629758637a0bf1b60aeb0c/src/hgapp.rs#L223) 的 223–232 行调用该接口。**尚未确认 iOS 实际使用该路径，不能把 Android 的字段与 iOS 响应结构视为相同。**

本地 iOS 7.4.1 可读字符串出现过 `enable_insert_ad`、`disable_insert_ad`、`insert_ad_rit_type`、`video_patch_ad_config`、`ad_duration`、`ad_repeat_info`；另把 `chapter_middle_ad_config` 作为待验证字段。SDK 组件和字符串存在并不证明正在调用，也没有直播广告枚举值或可靠的网络响应映射。因此本次不盲改字段，不全封 webcast/CDN。

## 精简覆盖与验证

| 删除的规则 | 更早的同策略覆盖 |
|---|---|
| `v*-reading-videocdn*.qznovelvod.com` DIRECT | `v*-reading-video*.qznovelvod.com` DIRECT |
| `*-fq-tts.fqnovelvod.com` DIRECT | `fqnovelvod.com` DOMAIN-SUFFIX DIRECT |
| `ads*-normal-lq.zijieapi.com` REJECT | `ads*-normal-*.zijieapi.com` REJECT |
| `v*-bd-daily-reading-ad.qznovelvod.com` REJECT | `v*-reading-ad.qznovelvod.com` REJECT |
| `v*-se-daily-reading-ad.qznovelvod.com` REJECT | `v*-reading-ad.qznovelvod.com` REJECT |
| `v*-se-sjy-daily-reading-ad.qznovelvod.com` REJECT | `v*-reading-ad.qznovelvod.com` REJECT |

保留 `p3-ad-sign.byteimg.com` 的早期 DIRECT，保留广告视频 REJECT 在 `qznovelvod.com` 兜底 DIRECT 之前，也保留明确的 `n98-v-readingvideo` 例外和覆盖更多变体的 pangolin API 规则。

自动测试包含通配符语言包含证明、原始与精简规则的差分回归、诊断版规则一致性，以及 Node VM 内的日志隐私、时间滚动、预算、异常和透传模拟。这些不是 Surge 真机测试；真实接口是否命中、证书固定、播放及脚本冲突仍需本次手机测试。

```sh
python -m unittest discover -s tools/tests -p 'test_hongguo_modules.py' -v
node tools/tests/hongguo_diagnostic.test.cjs
```

Surge 依据：[域名规则](https://manual.nssurge.com/rules/domain.html)、[响应脚本与大小限制](https://manual.nssurge.com/scripting/http-response.html)、[脚本匹配、路径及日志](https://manual.nssurge.com/scripting/overview.html)。
