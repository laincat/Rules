# BilibiliPlus：B站 Surge 模块 + BoxJS 设置

版本 **2026.11.08.2**，实验版，未在用户的真实 iPhone/Surge 环境验证。

## 项目关系

- 用户原来安装的 `bilibili.sgmodule` 本来就是 **Surge 模块**，来源为 [kokoryh/Sparkle 仓库](https://github.com/kokoryh/Sparkle/blob/d513a2eeab382c640ccd5d6ecd76e07c4828b1ed/release/surge/module/bilibili.sgmodule)。本文中的 Sparkle 只表示这个 GitHub 来源仓库，不是另一款运行软件。
- **BilibiliPlus 也是 Surge 模块**：保留原模块的主体配置，在三个 App 播放接口中加入受 BoxJS 控制的诊断和有限的 PCDN 备用地址优选。这里的“兼容”指这层整合关系，不表示每个异常场景都与原模块完全等价。
- [Sukka 的 Make Bilibili Great Than Ever Before](https://github.com/SukkaW/Make-Bilibili-Great-Than-Ever-Before) 是另一个面向 B站网页的用户脚本项目。本模块只借鉴其部分 CDN 分类思路，**不是把该项目完整移植到 Surge，也不具备其所有功能**。
- BoxJS 仅是设置入口，保存开关供脚本读取，不负责拦截或优化视频。

原模块、引用项目及其作者的归属不变。本项目是独立整合作品，不是 kokoryh 或 Sukka 官方发布。

## 安装及更新

- [Surge 模块](https://raw.githubusercontent.com/laincat/Rules/main/Surge/Advertising/BilibiliPlus/Bilibili.Compatibility.sgmodule)
- [BoxJS 订阅配置](https://raw.githubusercontent.com/laincat/Rules/main/Surge/Advertising/BilibiliPlus/Bilibili.Compatibility.boxjs.json)
- [完整对应源码](Bilibili.Compatibility.Source.tar.gz)
- [文件 SHA-256 校验](Bilibili.Compatibility.SHA256SUMS)

为保留已发出的订阅链接，文件名继续使用 `Bilibili.Compatibility.*`；界面名称统一为 BilibiliPlus。

1. 保留已安装的 BoxJS 模块。
2. 停用原 B站 Surge 模块后，再启用 BilibiliPlus。**不要同时开启两个 B站模块。** 已安装 BilibiliPlus 的用户更新原订阅即可，不必重复安装。
3. 原模块的参数设置不会承诺自动迁移。若曾修改“空降助手策略”“屏蔽P2P”等参数，请按原值设置新模块。
4. 在 BoxJS 的订阅管理中添加上面的配置链接并保存设置。订阅 ID 和存储键保持不变，已有 BilibiliPlus 设置可继续使用。
5. 初次使用保留默认：新增功能总开关开启、地址优化关闭、诊断开启。原模块已有的广告过滤及 P2P 规则仍按其参数生效，并非整个模块都处于“只观察”状态。

以上为跟随本仓库 main 的链接。GitHub Release 同名附件由仓库既有流程发布；镜像模块内部仍引用 GitHub 脚本，不能保证完全不依赖 GitHub 网络。

## 保留了原模块的哪些部分

基于原模块 `d513a2eeab382c640ccd5d6ecd76e07c4828b1ed` 快照：

- Rule、Map Local、Body Rewrite、MITM 域名，以及原来的八项模块参数和默认值均保留。
- 原有去广告、评论、动态、空降助手、皮肤、直播页面相关接口处理等仍引用该版本的原脚本；不表示新增了直播 CDN 优选。
- 原七条 Script 变为八条：从原 protobuf 响应规则中拆出 UGC PlayView、PlayViewUnite、PGC PlayView 三个播放接口，交给兼容脚本处理，其余接口仍使用原脚本。两条规则不重叠。
- 三个播放接口的原有提示清理及后台播放/投屏相关处理保留，另加了大小、帧格式和错误状态检查。超过 2MiB 或不支持的响应原样放行，因此该次响应的原播放清理也可能不执行。

这是一份锁定版本的整合快照。原仓库后续更新**不会自动合入** BilibiliPlus，需要重新核对和构建。主要原脚本锁定了提交，但皮肤脚本及 Chronos 等间接依赖仍有动态上游，不能称全部依赖冻结。

## BoxJS 三个开关

- **新增功能总开关**：只关闭新增优化与诊断，不关闭原模块的去广告、P2P 端口或 tracker 规则。
- **优先非 PCDN 备用地址（实验）**：默认关闭。只在当前普通 DASH 音频/视频表示的前 32 个备用地址中，选择第一个符合已识别 HTTPS 镜像条件的地址。不凭空构造新 CDN，不改签名原文；原主地址放回备用列表供客户端使用。未验证 App 是否实际采用失败回退。
- **脱敏诊断日志**：默认开启，独立于模块原来的“日志等级”参数。新增日志仅输出版本、固定接口标签、模式及表示/命中/可替换/已替换/无备用等计数，不记录 URL、Cookie、token、视频 ID 或响应原文。每接口每 UTC 日期约 100 条；并发写非原子，并非严格安全配额。原脚本的其他日志行为不由此开关控制。

关闭地址优化不等于撤销原模块或其他规则集的 PCDN 拦截。若原地址已被规则拒绝，放入备用列表也不能绕过该规则。

## 与 Sukka 的差异及覆盖边界

- 当前识别部分 PCDN 域名和 URL 标记；2026.11.08.2 补上 `os=mcdn` 及已知签名期限检查：正常镜像域名带该参数时也不应视为非 PCDN。两项目的域名分类范围仍不完全相同。
- 只从同一 DASH 对象返回的已有备用地址优选；没有 Sukka 的跨主机签名候选、候选分层、失败冷却或浏览器请求重试。保留签名不代表验证签名仍有效，本版会跳过已知 `deadline` 或 Akamai `hdnts` 中 `exp` 距离当前时间不超过 60 秒的备用地址；无法解读期限时仍按其他条件判断，不冒称已验证有效，也不测速。
- 不解析 `xy_usource` 回源，不构造 `proxy-tf-all-ws` 代理地址；纯 IP 的资源 URL 不会仅因为是 IP 就认定为 PCDN。
- 只处理匹配的 App protobuf 控制接口中的普通 DASH 视频和 `dash_audio`。不覆盖分段流、Dolby/HiRes 特殊音轨、直播 CDN 优选；没有网页 DOM、WebRTC/PCDN SDK 替换、Thread Ripper 或 App“我的”原生开关。
- 未识别、没有合适备用源或不支持的结构保守放行；**不能保证消除所有 PCDN**，不解锁权限或画质。
- Sukka 运行在网页内部，本版运行在 Surge 网络处理层，适用客户端及控制能力不同。

Proto 字段以固定提交的社区定义核对，不是当前用户 iOS 抓包证据。未知字段保留，但序列化顺序可能变化。仅处理一个完整 unary gRPC 消息；gzip 先做头尾/大小预检，再检查解压后大小，这不是对恶意 gzip 的严格峰值内存隔离。失败时 `$done({})` 保留原响应。新 2MiB 上限只作用于三个播放接口，不影响其他动态/评论响应。

## 诊断与回滚

播放普通视频或番剧、切换清晰度并拖动，查看 Surge 的 `bilibili.compat.playback` 脚本日志。`eligible>0` 只是找到符合选择条件的备用地址，不代表已经验证可达或播放成功。再短时开启优化，对比 `changed` 与播放表现。

出现问题先关闭地址优化；完整回滚则停用 BilibiliPlus、恢复原 B站 Surge 模块。MITM 复用原模块域名，不代表设备已成功解密。本项目没有自动改变设备证书或网络设置，也不对媒体大包做内容缓冲。新增部分不上传诊断日志，原模块其他网络功能保持其原有行为。

## 构建与测试

完整源码包中 `sparkle/` 是原仓库及本地修改的源码目录名，保留这个名称用于来源追溯。Node/npm 依赖固定在其中的 `package-lock.json`：

```
cd sparkle
npm ci --ignore-scripts --cache /tmp/bili-npm-cache
PATH="$PWD/node_modules/.bin:$PATH" XDG_CACHE_HOME=/tmp/bili-buf-cache node_modules/.bin/buf generate
node --import tsx add-pure-annotations.ts
cd ..
ASSET_BASE_URL=https://raw.githubusercontent.com/laincat/Rules/main/Surge/Advertising/BilibiliPlus node build.mjs
sparkle/node_modules/.bin/tsc --noEmit -p sparkle/tsconfig.json
cd sparkle
ASSET_BASE_URL=https://raw.githubusercontent.com/laincat/Rules/main/Surge/Advertising/BilibiliPlus node --import tsx --test ../tests/adapter.test.ts
```

另可在源码包根目录执行 `python -m unittest discover -s tests -p '*_test.py'` 验证打包边界与可重现性。

完成构建与测试后，可用 `python package.py --output /目标目录/Bilibili.Compatibility.Source.tar.gz` 重建完整对应源码包。打包器排除 node_modules、Git 状态和符号链接，并固定归档时间戳；同一输入可重现相同包。

不设置 `ASSET_BASE_URL` 时故意生成使用 example.invalid 的 review-only 模块，不能直接导入；构建工具不上传、不提交或发布。

测试使用合成 protobuf/gRPC fixture 与 Surge API 模拟，不是真机网络播放测试。覆盖分类、BoxJS 设置、无备用放行、签名原文、未知字段、三个接口、gzip、错误放行、日志脱敏和限额、规则不重叠、原播放逻辑保留，以及 `os=mcdn` 的主/备用地址回归。

源码中移除了原 `src/utils/index.ts` 对不存在的 `createMergedPoints` 的再导出，以通过完整类型检查；未改变该函数实际业务实现。

## 来源与许可证

- 原 B站 Surge 模块及代码：[kokoryh/Sparkle](https://github.com/kokoryh/Sparkle)，GPL-3.0，固定 `d513a2eeab382c640ccd5d6ecd76e07c4828b1ed`。整合版整体按 GPL-3.0 提供，完整修改源码随包发布。
- 部分 CDN 分类思路参考：[SukkaW/Make-Bilibili-Great-Than-Ever-Before](https://github.com/SukkaW/Make-Bilibili-Great-Than-Ever-Before)，MIT，Copyright (c) 2024 Sukka，固定 `c87b7e74aa420d845e36e00f24d812772d68f488`。没有复制其完整运行时/依赖，也不代表相同算法。
- protobuf 字段参考：[aaa1115910/bv](https://github.com/aaa1115910/bv/tree/0e454c06e954b00df7a0a5a6873c9f18a7f9d0f5/bili-api/grpc/proto/bilibili)，MIT，Copyright (c) 2022 aaa1115910，固定 `0e454c06e954b00df7a0a5a6873c9f18a7f9d0f5`。
- 完整源码包内 `licenses/` 保存三份原许可，`THIRD_PARTY_LICENSES.txt` 保存依赖许可。原作者归属未改。
