# 去广告构建校验与 HaGeZi 对比 · 2026-10-04

本次改进构建校验，保留 Cats-Team、Sukka、AWAvenue 三个来源，
不恢复 BlueSkyXN，也不把 HaGeZi 自动加入默认列表。

## 本次构建改进

借鉴 HostlistCompiler 的“先规范化、校验、应用排除，再压缩”的处理顺序：

1. 下载阶段拒绝空响应、HTML 页面和无效 UTF-8；移除 UTF-8 BOM。
2. 将大小写、尾点和 Unicode 域名归一化；IP、全数字末标签、URL、
   通配符与非法 DNS 标签不作为域名接受。保留有效的已有 Punycode A-label。
3. 根据每个来源解析后的有效独立条目数检查源健康状况，
   注释、HTML 或重复行不能凑满构建下限。
4. 使用官方 Public Suffix List 的 ICANN 与 PRIVATE 区域，
   处理通配与例外，避免把整个多租户／公共后缀编译为拦截项。
5. 在父子域收敛前应用双向保护：既剔除受保护域的后代，
   也剔除会覆盖受保护子域的更宽后缀；保留其他明确广告子域。
6. 对关键词检查已知保护域的子串碰撞，记录每个来源的 SHA256、
   有效条目数及最终过滤统计。
7. `.mrs` 在同一文件系统的临时路径编译，只有非空产物编译成功才替换原文件；
   未成功推送的 CI 提交不能触发 Release 发布。
8. 统一 tar 顺序、时间、所有者及 gzip 元数据；保留未改变规则的原时间戳，
   包括 Windows CRLF 文件，避免无意义的每日重写。

### 已复现的保护缺陷

旧列表的 `.data.microsoft.com` 覆盖了 Cats 白名单
`events.data.microsoft.com`；`.pipe.aria.microsoft.com` 覆盖了
`mobile.pipe.aria.microsoft.com` 和 `browser.pipe.aria.microsoft.com`；
`.ugdtimg.com` 覆盖了 `free-adsmind.ugdtimg.com`。

新版移除这些过宽后缀，保留来源中明确列出的其他广告／遥测子域。
删除祖先前不能先做包含收敛，否则子域规则已经丢失，无法保留。

### 构建与验证记录

本次主列表由 197,439 条变为 197,407 条，关键词补充仍为 4 条。
最终过滤阶段识别 40 个 public suffix 候选与 2,495 个受保护候选，
这些是合并来源中的过滤统计，并不等于相对上一版新增删除的数量。
`invalid_domain: 0` 仅表示进入最终过滤集合的非法域名数为零，
不是声称上游输入没有无效行；无效行已经在解析阶段被拒绝。

25 项离线回归测试通过；完整构建通过，第二次完整构建无产物变化；
Advertising、AI、Ozon 的 `.mrs` 均解码后与对应 Surge 域名规则一致。
CI Bash 语法检查通过，改变测试文件 mtime 后，生成的压缩包字节仍一致。

```bash
python -m unittest discover -s tools/tests -v
python tools/gen_rulesets.py --write --mihomo ./mihomo --report validation.json
```

CI 将 JSON 校验报告打印到生成步骤日志。
[本次校验快照](adblock-validation-2026-10-04.json)记录来源与统计。
其来源哈希对应解码后、
移除 BOM 的文本；普通 ASCII/UTF-8 无 BOM 来源与原始字节哈希一致。

### 校验边界

Cats 白名单当前有 4 条正则／通配表达式未转换，报告明确列出；
不会把含糊表达式强行裁成一个父域。域名黑名单不能表达“拦截整个父域，
但放行其中一个子域”，所以遇到保护冲突时移除父域拦截，再保留明确广告子域。
关键词保护只覆盖已知保护域名的碰撞，不保证无限未知子域的匹配都无误伤。
PSL 获取或校验失败将停止本轮生成，保留已发布版本。

## HaGeZi 的定位

HaGeZi Multi 是按强度分级的 DNS 拦截列表，包含广告、追踪及恶意／诈骗等类别。
五档择一；Threat Intelligence、DoH bypass、URL shortener、Social 等专题列表
有不同目的，不应不加分类地全部并入普通去广告。

| 档位 | 定位与兼容性 |
|---|---|
| Light | Normal 的流量排名精简版，兼容性优先 |
| Normal | 较保守，低风险，不拦崩溃／错误监控 |
| Pro | 作者推荐的默认平衡档，低到中等风险，包含崩溃／错误监控拦截 |
| Pro++ | 更强的追踪拦截，兼容风险增加 |
| Ultimate | 最激进；官方明确说明部分正常功能可能受影响 |

我们采用来源合并、核心服务保护以及 Surge／Mihomo 双格式输出；
HaGeZi 则把来源、分类、例外与兼容性选择分配到各档。
HaGeZi 官方来源中也包含 AWAvenue，所以它不是完全独立的新增覆盖。

## 对比方法与快照

HaGeZi 固定提交：
`913ee73a7b41aee70c943e422e19e16b7be55c47`，
提交时间为 `2026-10-03T09:26:29Z`。
五档文件标识的更新时间为 `2026-10-03 08:34 UTC`。

逐行验证本次五档输入只含 `||domain^`；
这种语法表示域名及其全部子域，不能转换成精确匹配。
本仓库前导 `.` 同样表示后缀，普通行仅精确匹配。

“完整覆盖”指我们存在相同或更宽的后缀规则；只拦截该域名本身的精确项，
不算完整覆盖 HaGeZi 的后缀项。另行记录去除语法前缀后的文字交集，
它不等于语义覆盖。统计是规则覆盖，不是广告拦截成功率。

本仓库比较基线是这次清洗后的 197,407 条工作区产物，SHA256 为
`41126869dcbb532d1ddb55c0c45f76e9dc2da34ead6a9809c704f9f3ef27ae2e`。
基线 HEAD 为 `1b48bd2`，不代表产物已经在该提交中；
JSON 明确标记为清洗后的未提交快照，并记录生成器与校验模块的哈希。

| 档位 | 上游条数 | 文字交集 | 我们完整覆盖 | 覆盖比例 | 经新校验后的新增后缀候选 |
|---|---:|---:|---:|---:|---:|
| Light | 51,311 | 20,425 | 26,537 | 51.72% | 23,804 |
| Normal | 199,284 | 76,500 | 93,435 | 46.89% | 102,991 |
| Pro | 227,420 | 78,653 | 83,461 | 36.70% | 140,556 |
| Pro++ | 248,298 | 80,699 | 83,848 | 33.77% | 160,544 |
| Ultimate | 284,074 | 80,526 | 81,900 | 28.83% | 190,540 |

反向比较：Normal 完整覆盖我们 79,200 条（40.12%），
Pro 完整覆盖我们 82,669 条（41.88%），因此无法直接替代现有来源。

强档覆盖数下降不代表其拦截更弱：HaGeZi 会把很多子域合并成父域，
我们的子域规则不能完整覆盖更广的父域后缀。
Normal 中一些仅按文字看似不在 Pro 的条目，实际上已被 Pro 的父域覆盖。

仅作试算：把 Normal 与我们合并，经保护与收敛后得到 297,491 条；
Pro 合并后为 333,719 条。候选数不等于净增条数，父域可能合并已有子域。
这些试算均未写入实际去广告产物。

按我们兼容优先的政策，Normal 中 5 个 public suffix 和 2,853 个受保护项
被剔除；Pro 中分别为 55 和 3,348 个。部分是动态 DNS／托管平台，
HaGeZi 可能选择整平台拦截；不能仅根据我们的排除政策认定它的规则错误。

完整统计、关键域名检查、文件 SHA256 与来源 URL 见
[对比 JSON 快照](adblock-comparison-2026-10-04.json)。

## 兼容性判断与建议

五档 Multi 均未拦截 `t.co`。Normal 未拦截
`dns.weixin.qq.com` 和 `aedns.weixin.qq.com`；
Pro、Pro++、Ultimate 都拦截这两个微信解析域名。
我们的当前列表仍拦截 `dns.weixin.qq.com`，未拦截 `aedns.weixin.qq.com`。
这是 HTTPDNS 策略差异，不能直接据此认定支付卡顿原因。

Normal／Pro 都未整域拦截 `tenpay.com` 或 `alipay.com`，
但包含若干支付宝遥测子域；我们的整域保护会主动剔除这些子域。
我们也保护 `sentry.io`、公共 CDN、部分推送服务等，
这些主动放行是差集的重要原因，而非单纯“漏拦”。

双方明显互补，但新增候选没有逐条验证为广告。继续保持现有来源，
如果后续增加 HaGeZi，优先评估 Normal，并单独审计差集，
重点复测支付、登录、推送和应用解析。不要直接替换现有列表，
也不要把各档或专用专题列表叠加以追求数量。

## 官方资料

- [HostlistCompiler README](https://github.com/AdguardTeam/HostlistCompiler)：源级与合并后处理、Compress、Validate、ConvertToAscii。
- [HaGeZi README（固定提交）](https://github.com/hagezi/dns-blocklists/blob/913ee73a7b41aee70c943e422e19e16b7be55c47/README.md)：分级定位与兼容性说明。
- [HaGeZi FAQ（固定提交）](https://github.com/hagezi/dns-blocklists/blob/913ee73a7b41aee70c943e422e19e16b7be55c47/FAQ.md)：来源清洗、规则上下文及误伤处理。
- [HaGeZi 来源（固定提交）](https://github.com/hagezi/dns-blocklists/blob/913ee73a7b41aee70c943e422e19e16b7be55c47/sources.md)。
- [Public Suffix List 官方文件](https://publicsuffix.org/list/public_suffix_list.dat)。
