# Surge · 来源与维护边界

[返回导航](readme.md)

## 官方资料

本地章节是阅读摘要和使用提示。按主题回到官方原文核对，不把整个官方手册复制到仓库。
官方在线文档会变化；已有版本专属内容保留其固定 tag 或公告链接，不将开发版行为推定到稳定版。

- [01 · Profile（配置文件）](01-profile.md)：[官方原文 1](https://manual.nssurge.com/profile/format.html)
- [02 · 规则](02-rules.md)：[官方原文 1](https://manual.nssurge.com/rules/overview.html)
- [03 · 规则集：`RULE-SET` 与 `DOMAIN-SET`](03-ruleset.md)：[官方原文 1](https://manual.nssurge.com/rules/ruleset.html)
- [04 · DNS 与策略](04-dns-and-policy.md)：[官方原文 1](https://manual.nssurge.com/dns/overview.html)、[官方原文 2](https://manual.nssurge.com/policy-groups/overview.html)
- [05 · Module 与脚本](05-module-and-script.md)：[官方原文 1](https://manual.nssurge.com/profile/module.html)、[官方原文 2](https://manual.nssurge.com/scripting/overview.html)
- [06 · 运维与排错](06-operations.md)：[官方原文 1](https://manual.nssurge.com/tools/http-api.html)

## 仓库资料

- [接入示例](repository-recipes.md)描述本仓库产物，不是软件默认设置。
- `upstream.json` 是自动观察记录，采集成功不等于文档全部内容已人工验证。
- `translations.json` 是发布说明译文缓存，不作为参数支持范围的来源。
- 新增兼容性声明必须给出该产品官方文档、版本化源码或官方发布说明；社区教程仅可作为数据归属说明。

## 复核记录

2026-10-16：按各自官方文档目录重整导航，移除跨产品教程依赖，分离仓库接入示例。
本次核对了章节映射中的官方入口及关键配置主题；旧的版本专属细节仍以各节固定来源为准。
自动状态和发布日志继续由现有巡检维护。

## 细分主题

- [01-profile.md](01-profile.md)：[官方 profile/general.html](https://manual.nssurge.com/profile/general.html)
- [02-rules.md](02-rules.md)：[官方 rules/domain.html](https://manual.nssurge.com/rules/domain.html)、[官方 policies/reject.html](https://manual.nssurge.com/policies/reject.html)、[官方 features/ip-rewrite.html](https://manual.nssurge.com/features/ip-rewrite.html)
- [03-ruleset.md](03-ruleset.md)：[官方 rules/domain.html](https://manual.nssurge.com/rules/domain.html)
- [04-dns-and-policy.md](04-dns-and-policy.md)：[官方 dns/advanced.html](https://manual.nssurge.com/dns/advanced.html)、[官方 dns/local-dns-mapping.html](https://manual.nssurge.com/dns/local-dns-mapping.html)、[官方 policy-groups/parameters.html](https://manual.nssurge.com/policy-groups/parameters.html)
