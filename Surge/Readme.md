<p align="center">
  <img src="https://is1-ssl.mzstatic.com/image/thumb/PurpleSource221/v4/c7/15/0e/c7150ee6-dbdf-f99c-c8c3-fbbbb37cda46/Placeholder.mill/200x200bb-75.webp" width="150" />
</p>

<h1 align="center">Surge</h1>

<p align="center">Surge 规则集、模块与自动更新日志。</p>

<p align="center">
  <a href="https://www.nssurge.com/">官网</a> ·
  <a href="https://manual.nssurge.com/">官方手册</a> ·
  <a href="Changelog/readme.md">更新日志</a>
</p>

---

## 目录

| 目录 | 内容 |
|---|---|
| [`Advertising/`](Advertising/) | 去广告：`.sgmodule` 与 6 个按处置策略分片的 `.list`（对齐 SukkaW/Surge） |
| [`Module/`](Module/) | 功能性模块（Telegram / Ozon / 下载分流 / MITM…） |
| [`Ruleset/`](Ruleset/) | 常规规则集（`Japan` / `Special` / `Ozon` / `AI` / `Custom`） |
| [`Changelog/`](Changelog/readme.md) | **自动更新日志**：Telegram 公告的中文翻译 |

## 引用方式

通用订阅模块（`.sgmodule`）可直接引用；含私人策略的功能模块请先阅读 [模块兼容性说明](Module/readme.md)：

```
https://raw.githubusercontent.com/laincat/Rules/main/Surge/Advertising/Advertising.sgmodule
```

`.list` 扩展名不决定格式。以下四份为纯域名集，使用 `DOMAIN-SET`：

- `Ruleset/AI.list`、`Ruleset/Ozon.list`
- `Advertising/Advertising.Reject.list`、`Advertising/Advertising.RejectExtra.list`

其余十份 `.list` 为完整规则行，使用 `RULE-SET`，例如：

```
[Rule]
RULE-SET,https://raw.githubusercontent.com/laincat/Rules/main/Surge/Ruleset/Special.list,Proxy,extended-matching,"update-interval=21600"
FINAL,Proxy
```

> ⚠️ `DOMAIN-SET` 与 `RULE-SET` 文件格式不同，不能互换。AI / Ozon 的 `.Extra.list` 补集仍使用 `RULE-SET`。完整订阅示例见 [`Ruleset/readme.md`](Ruleset/readme.md)，格式定义以 [Surge 官方手册](https://manual.nssurge.com/)为准。

## 红果模块与来源核对

[`HongGuo.sgmodule`](Advertising/HongGuo.sgmodule) 可单独启用，无需 MITM 或证书。
2026-10-28 补入 `pangolin-dsp-toutiao.com`、`pangolin-dsp-toutiao-b.com` 两个域名后缀，
以及 `log*-applog.fqnovel.com` 上报规则。依据是
[hongguo-lite 的拦截清单及交叉核对说明](https://github.com/k6nfmm7dbr-commits/hongguo-lite/blob/main/README.md)；
将其宽泛关键词收窄，补齐独立使用时的缺口。既有正片、图片、登录与评论例外保持原样。

以下日期为关键规则文件最后提交的香港日期，核对时间为 2026-10-28，不代表设备实测结果：

| 来源 | 文件最后提交 | 许可核对 | 可参考的增量与限制 |
|---|---|---|---|
| [egern-hongguo-adblock](https://github.com/bluee1111/egern-hongguo-adblock/blob/main/hongguo-adblock.yaml) | 2026-10-09 | 仓库 MIT | 现有主来源，保留 reading-ad 与正片 CDN 的区分。 |
| [hongguo-lite](https://github.com/k6nfmm7dbr-commits/hongguo-lite/blob/main/surge/hongguo-lite.sgmodule) | 2026-10-06 | 仓库 MIT | 本次三条规则的依据；Plus 版路径拦截需要 MITM。 |
| [LoonKissSurge 番茄规则](https://github.com/QingRex/LoonKissSurge/blob/main/Surge/番茄小说去广告.sgmodule) | 2025-11-14 | 未发现模块统一许可证；README 要求遵循原作者许可 | 可交叉核对 log3/5、rtlog3/5 上报；含风控、登录与直播相关拦截，不宜整份合入。 |
| [HongGuo-Surge-Native](https://github.com/doovvip/sublink-worker2/blob/main/surge-modules/HongGuo-Surge-Native.sgmodule) | 2026-09-05 | 仓库 MIT | 纯域名部分已有覆盖；额外路径拦截、下载/画质响应脚本需要 MITM，后两者上游仍标为实验。 |
| [zqzess FanQieNovel](https://github.com/zqzess/rule_for_quantumultX/blob/master/Surge/Module/FanQieNovel.sgmodule) | 2024-03-06 | 未发现仓库许可证 | 可作历史交叉核对；含 zijieapi 关键词、bytedance.com 整域及视频域拦截，不建议直接导入。 |
| [fanqienovel-adguardhome-rules](https://github.com/gitlawyercan/fanqienovel-adguardhome-rules/blob/main/fanqienovel.txt) | 2026-10-05 | 文件头及 README 声明 MIT，未发现所链接的 LICENSE 文件 | 重点参考正片、登录、评论白名单；额外统计/素材域和直播、风控拦截需请求记录验证，不自动搬入。 |

本次仅补入上述三条域名规则；其余来源用于交叉核对，不引入远程脚本、VIP 改写或证书固定绕过。
离线测试验证新规则、非目标域名边界、既有 DIRECT 和 reading-ad 首条命中；不能替代 Surge 内核或真机播放测试。
域名规则可能影响共用这些域名的其他字节系应用；拦截广告和上报也可能影响金币/奖励入口。
设备上应复测冷启动、连续播放、切集、封面、登录和评论，并查看实际命中记录。
与通用 Advertising 模块组合时，仍需留意其 pre-matching 规则；普通 DIRECT 无法覆盖提前命中的 REJECT。

