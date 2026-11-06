# 红果模块与广告 / 直播诊断

日常使用 [HongGuo.sgmodule](HongGuo.sgmodule)：45 条原生域名规则，无需 JS、MITM 或证书。本次正式版字节不变，Diagnostic 中的 45 条规则及顺序也完全不变。**没有解除任何 REJECT，没有修复直播插播，也没有修改响应或阻断直播媒体。**

临时测试使用 [HongGuo.Diagnostic.sgmodule](HongGuo.Diagnostic.sgmodule)，版本 `2026.11.06.2`。它在原 4 个 fqnovel 主机之外，保留 iOS 7.4.3 IPA 静态报告里的 22 个广告、直播、消息和资源候选，再加入实际请求记录出现的 `webcast5-open-lf.douyin.com`，共 **27 个精确 MITM 主机**。没有扩大到整个 `amemv.com`、`douyin.com`、`zijieapi.com` 或其他通配域名。静态存在不代表手机实际请求。

## 安装、更新与回退

- [正式版固定下载地址](https://github.com/laincat/Rules/releases/download/latest/HongGuo.sgmodule)
- [Diagnostic 固定下载地址](https://github.com/laincat/Rules/releases/download/latest/HongGuo.Diagnostic.sgmodule)
- [诊断脚本](HongGuo.Diagnostic.js) / [手动摘要脚本](HongGuo.Diagnostic.Report.js)

1. 停用正式版，导入或更新 Diagnostic，再启用。二者不要同时启用。若已装旧诊断版，更新模块并刷新远程脚本；脚本 URL 已带本版查询标记以避免沿用旧缓存。确认模块脚本名显示“27主机”，并用日志里的 `version=2026.11.06.2` 核对实际运行版本。只刷新JS而不更新旧26主机模块不会补上新主机。
2. 手机必须已有正确配置和信任的 Surge MITM 证书，并启用对应功能。模块仅使用 `hostname = %APPEND%`，不会开启全局 MITM、安装证书或更改 TLS 验证。**不要为了诊断关闭 TLS 验证。**
3. 与其他模块同用时核对最终生效规则和脚本优先级；`Advertising.sgmodule` 的 `pre-matching` 仍可能提前拒绝。Surge 每个请求、每个响应分别只执行第一个匹配脚本；本诊断也可能抢先覆盖其他请求/响应脚本。不要盲目调序来覆盖其他脚本，先查冲突。
4. 更新后立即短时间复现“开屏、原有广告触发场景、正片切进直播间”，记下手机本地时间、集数和操作，事件发生后及时导出日志并查看摘要剩余额度。不需要为了诊断点击广告、支付或发送聊天消息。若出现请求失败、播放异常或证书固定问题，立即停用 Diagnostic，恢复正式版。
5. 测试结束立即停用，**最长两天后手动停用**，再启用正式版。本模块没有自动到期关闭功能。停用后它追加的主机与脚本不再生效；其他配置本来存在的 MITM 主机不变，也不会删除 Surge 证书。日志可在 Surge 中清理，本版使用8个有界本地状态键，总上限36 KiB，不保存正文；旧版状态不会被主动删除或当作新版计数使用。

## 一处复制摘要与详细日志

在 Surge 脚本列表手动运行 `红果诊断-摘要(手动运行)`，打开该脚本日志，复制最新的 `hongguo-local-summary` JSON。摘要分开显示 control、ad、background 的请求/结构/失败采样计数、最近观察/记录时间、当天日志预算、失败/限额采样概况，以及无观察、旧日期、状态不可用等固定状态。它只读本地状态，不上传、不清空、不重置日志预算；这是**现场摘要，不是完整历史**，不能证明模块安装后已经正常解密。

出现跳直播时，另外复制对应时段的 `红果诊断-请求(广告与直播27主机)` 和 `红果诊断-响应(API结构)` 脚本日志，附上大致本地时间和时区。日志按一行一个 JSON 输出，Surge 可能加时间前缀。主交付是“请求”和“响应”两份原生脚本日志文件，摘要为可选辅助。打开 Surge 的“日志 → 脚本日志”，找到上述名称，使用该版本提供的分享/导出操作；若没有该入口，复制日志全文保存为 `.txt` 再发送。没有在你的手机上验证具体按钮或生成实际文件，因此这里不提供虚构的文件路径。只分享这三个脚本的日志，**不要分享完整抓包、请求详情、请求/响应正文、Cookie、Token 或配置文件**。模块没有设置 `debug=true`，不主动将脚本日志镜像进请求详情。

详细事件文件直接使用 Surge 原生 `console.log` 按脚本名称保存的日志，方便分别导出；没有引入网页面板、浏览器存储或第三方反馈上传。

## 精确主机与诊断层级

### 原有 API 候选（4）

```text
api3-normal.fqnovel.com
api5-normal.fqnovel.com
api3-normal-lq.fqnovel.com
api5-normal-lq.fqnovel.com
```

### 广告接口与包内调度候选（10）

```text
ad.zijieapi.com
ads.zijieapi.com
ads3-normal.zijieapi.com
ads5-normal.zijieapi.com
ads3-normal-lf.zijieapi.com
ads3-normal-hl.zijieapi.com
ads3-normal-lq.zijieapi.com
ads5-normal-lf.zijieapi.com
ads5-normal-hl.zijieapi.com
ads5-normal-lq.zijieapi.com
```

### 直播 API 主机候选（4）

```text
webcast.amemv.com
webcast-open.amemv.com
webcast-open.douyin.com
webcast5-open-lf.douyin.com
```

### 直播搜索 HTTPS 候选（1）

```text
search.amemv.com
```

### WSS 消息候选（2）

```text
webcast100-ws-open.douyin.com
webcast100-ws-c.amemv.com
```

### 直播静态资源候选（6）

```text
lf-webcast-gr-sourcecdn.bytegecko.com
lf-webcast-sourcecdn-tos.bytegecko.com
lf1-webcastcdn-tos.douyinstatic.com
lf3-webcastcdn-tos.douyinstatic.com
lf6-webcastcdn-tos.douyinstatic.com
lf9-webcastcdn-tos.douyinstatic.com
```

所有 27 个主机只追加为 MITM 候选。MITM 是**整台设备、按主机**生效，不局限于红果或下列路径，可能涉及同主机的其他应用、正常业务和账号流量。脚本不记录这些内容，但 Surge 的其他抓包/日志设置仍可能保留它们；不要导出完整流量。MITM 会增加 TLS/CPU/内存成本；Surge 的默认 `auto-quic-block` 机制可对命中 MITM 的 QUIC 促使回退，但主配置是否沿用默认值未知。新增主机在设备记录中出现的是 QUIC；是否回退 TCP、完成解密及兼容证书固定都未实测，不能保证加名单就会有响应日志。本模块不改这些全局设置，也没有手机耗电/延迟实测。

- `红果诊断-请求(广告与直播27主机)` 不读取请求头、请求正文或响应，只记录固定主机和预定义类别：`player-detail`、`ad-api`、`live-api`、`live-search`、`live-message-poll`、`live-message-handshake-candidate`、`live-asset`、`other-on-approved-host`。原始路径与查询都不输出。另用固定 `endpoint` 标签区分 `ad-live-cmm`、`ad-patch`、`live-room-enter`、`live-room-info` 等白名单端点，未知路径仍只给固定大类，不输出路径值。
- `红果诊断-响应(API结构)` 只在下列候选 API 返回时缓冲至多 256 KiB，检查 JSON 中旧版7个广告候选字段及9个待验证直播导航字段的脱敏位置、类型和计数，以及合法 HTTP 状态码（无法识别时为 null），不输出值，不把字段存在当成控制广告的证明。
- `/webcast/im/` 消息轮询、两个 WSS 主机和六个资源主机**不进入正文脚本**。WSS 标签最多表示请求层候选，不证明握手成功、没有观察 WebSocket 帧，更不是视频流地址。JS、图片、媒体和聊天正文都不检查。

正文候选范围：

- 原 4 个 fqnovel 主机的 `/novel/player/video_detail/v1/`。
- 广告主机及原 4 个 fqnovel 主机上的 `/api/ad/v1` 与明确广告子路径（banner、inspire、patch、inspire_preload、inspire_send、aggregate、live_cmm、召回、反馈/举报）；`/api/ad/splash/novelapp/v15/`、`/api/ad/splash/stock/realtime/v15/`、`/api/ad/union/sdk/get_ads/`、`/api/incentive/marketing/done`、`/reading/reader/bonus/ad_reward/v数字/`、`/reading/commerceapi/ad/delivery_plan/v数字/`。
- 4 个直播 API 主机上的 feed、openapi/feed、content_open/feed，以及 room/enter、room/info、room/enter_preload、room/realtime_status_center/info，允许有无 `/webcast` 前缀。
- `search.amemv.com/aweme/v1/live/search/`。

相对路径与不同主机的组合只是诊断匹配候选，不是确认调用链。未知路径只产生固定 `other-on-approved-host` 类别，不读正文。匹配正则是具体实现边界。

**保留拦截的影响：** 现有 `ads*-normal*` 等 REJECT 继续生效，没有广告响应可供结构采样。若 `pre-matching` 提前拒绝，连请求脚本也可能不执行。加到 MITM 不等于放行，也不保证每个主机都有日志。需要临时解除阻断时须单独明确确认，本模块没有做。

## 隐私、性能与计数边界

两类日志仅输出固定版本、UTC 时间、白名单主机、固定类别/端点标签、阶段/结果和计数。正文诊断另外输出固定字段名、脱敏位置与类型：未知键显示 `*`、数组索引显示 `[]`。没有原始 URL/路径、查询值、头、Cookie、Token、账号 ID、聊天内容或正文；没有任何网络请求、上传或响应改写，也没有新增FLV或其他媒体流阻断。异常文本可能含敏感内容，因此也不回显。详细脚本用 `$done({})` 原样结束。

### 分池采样与限制

`pool` 表示诊断的采样分组，不是确认的业务功能。只对固定路径分类：`player-detail`、`live-api`、`live-search` 进入 control；`ad-api` 和广告主机上的未知路径进入 ad；资源、消息和其余未知路径进入 background。资源/消息及这些未知路径不能消耗 control 的预算或冷却。请求、响应结构独立，失败/限额采样也按这三组隔离。

顺序执行时的尽力限额（每UTC日）：

- control 请求：96条；同一主机/固定端点至少5秒，不同端点没有共享的秒级冷却。状态最多8192字符。
- ad 请求：48条；池内至少1秒，同一主机/固定端点至少60秒。状态最多4096字符。
- background 请求：48条；池内至少1秒，同一主机/固定端点至少5分钟。状态最多4096字符。
- control 响应结构：48条；同一主机/端点/HTTP状态/结构至少10秒，不同端点没有共享的秒级冷却。状态最多4096字符。
- ad 响应结构：24条；池内至少60秒，同一主机/端点/HTTP状态/结构至少30分钟。状态最多4096字符。
- background 不检查响应正文。所有结构日志单行最多8192字符。
- 失败/限额事件：control、ad、background 各24条；各池至少60秒，同一主机/端点/方向/原因至少5分钟，每池状态最多4096字符。仅输出实际观察到的固定原因：`body-not-text`、`body-too-large`、`json-parse-failed`、`json-non-container`、`daily-budget`、`global-cooldown`（池内）、`duplicate-endpoint`、`duplicate-shape`、`cooldown-capacity`、`log-size-limit`。不回显异常文本。

跨UTC日恢复日志预算但不重置有效冷却；时钟回退暂停相应池，直到追上已记录时间。状态只存时间、饱和计数和固定长度脱敏指纹，不保存正文或历史日志副本。新状态键从本次首次运行计数，不把旧版预算混入。

**短时间复现，不承诺连续两天详细覆盖。** 同一控制端点持续高频出现时，请求96条/5秒和结构48条/10秒均可能约8分钟用完；多个端点或变化结构可更快耗尽。请及时导出，并用手动摘要检查各池剩余量。达到预算不等于关闭MITM、停止响应缓冲或停止结构解析。

Surge持久存储没有原子比较更新：并发执行仍可能同时读到旧状态、写回相同计数并输出相同记录，造成超额、重复或漏计。分池只减少互相抢占，**没有修复或承诺消除并发竞争**；这类记录也不能单凭自身证明重复配置。各池计数不能相加当作精确网络请求数。

`observedRequestsToday` 是相应请求池观察到的匹配次数，`observedParsedResponsesToday` 是相应结构池解析的响应数；`observedTargetFieldHitsInResponse` 是全部预定义目标的遍历次数，`observedNavigationFieldHitsInResponse` 仅为新增待验证字段的遍历次数。字段 `hits` 受遍历上限影响，都不是广告次数或导航次数。

正文脚本限制 256 KiB UTF-8、5000 节点、16 层、每节点 128 子项、32 个输出结构项；超限、解析失败、存储失败等均原样放行。Surge 的响应 `max-size` 超限会跳过脚本并透传。请求脚本不设置 `requires-body=true`。预算不会消除 HTTP/TLS 处理开销，日志少不代表开销为零。

**没有日志不代表没有广告。** 可能是未命中候选、静态域名未使用、提前拦截、MITM 未生效、证书固定、其他脚本抢先、超大小或预算/冷却生效。失败事件也受限频，并非完整错误统计。存储失败本身可能无法安全留痕；`no-observations` 不能区分这些原因。Surge 已在脚本执行前跳过的大响应无法被 JS 记录成 `body-too-large`，请求后缺少结构日志也不能推断已被拒绝。空字段只表示没找到预定义目标，不能说明响应没有广告。

## 证据与限制

原22个新增候选来自红果短剧 iOS 7.4.3 / 构建 7.4.3.33 的离线 IPA 报告，包标识 `com.phoenix.video`，文件 SHA-256 `37118984f159cc2ac8e30654d35196ea31dbf0e829b2bf081df9fd00ee74b036`。广告调度依据包内 `tnc.json`，其余依据主程序完整 URL 或相对路径字符串。未包含 BOE、byted.org 开发测试域名，也没有把所有 SDK 字符串当作实际生产请求。服务端调度仍可能新增主机，本清单不承诺覆盖所有运行时地址。

本版新增精确主机 `webcast5-open-lf.douyin.com` 来自用户设备请求记录，记录显示DIRECT/QUIC；这仅支持加入主机候选，不确认其具体路径或响应内容。既有 `/room/enter/`、`/room/info/`、`/room/enter_preload/`、`/webcast/openapi/feed/`、`/webcast/content_open/feed/` 依据IPA静态字符串，对新主机的组合仍是待验证匹配。

新增固定字段名为 `room`、`room_info`、`live_info`、`live_room`、`webcast_info`、`jump_info`、`jump_type`、`navigation`、`schema`。它们是**有限名称假设，不是已从真实响应验证的导航字段**。日志标记 `candidate=unverified-live-navigation`，仅输出类型及出现次数（有记录即说明遍历时存在），不输出字段值、URL、ID或这些对象的任意子字段摘要。字段出现也不证明控制跳转；字段值变化不会用于结构指纹。本次没有新增 `room_id`、`user_id` 或URL字段采集。

保留的 `/novel/player/video_detail/v1/` 来自 [Android HgApp::detail 源码](https://github.com/ziyu4huang/guoapp/blob/76304b2f1ae41b352d629758637a0bf1b60aeb0c/src/hgapp.rs#L223)，iOS 是否调用仍未确认。旧版目标字段为 `enable_insert_ad`、`disable_insert_ad`、`insert_ad_rit_type`、`video_patch_ad_config`、`ad_duration`、`ad_repeat_info` 和待验证的 `chapter_middle_ad_config`。静态字符串不能给出可靠的广告枚举值或真实响应映射。没有主动请求应用在线接口或运行IPA；新主机的HTTPS回退、响应结构及WSS仍无真机验证。

Surge 依据：[请求脚本](https://manual.nssurge.com/scripting/http-request.html)、[响应脚本](https://manual.nssurge.com/scripting/http-response.html)、[MITM](https://manual.nssurge.com/http/mitm.html)、[脚本与缓存](https://manual.nssurge.com/scripting/overview.html)。

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

自动测试包含通配符语言包含证明、原始与精简规则的差分回归、诊断版规则一致性，以及Node VM中的日志隐私、时间滚动、预算、异常和透传模拟。本版另覆盖27主机三处名单一致、资源/消息/未知/广告与control隔离、背景预算耗尽/损坏、各池冷却与跨日、type-only直播标签、状态摘要，以及可复现并发旧状态读入的限制模型。这些不是 Surge 真机测试；真实接口是否命中、证书固定、播放及脚本冲突仍需本次手机测试。

```sh
python -m unittest discover -s tools/tests -p 'test_hongguo_modules.py' -v
node tools/tests/hongguo_diagnostic.test.cjs
```

Surge 依据：[域名规则](https://manual.nssurge.com/rules/domain.html)、[响应脚本与大小限制](https://manual.nssurge.com/scripting/http-response.html)、[脚本匹配、路径及日志](https://manual.nssurge.com/scripting/overview.html)。
