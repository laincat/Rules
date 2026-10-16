# Mihomo · 来源与维护边界

[返回导航](readme.md)

## 官方资料

本地章节是阅读摘要和使用提示。按主题回到官方原文核对，不把整个官方手册复制到仓库。
官方在线文档会变化；已有版本专属内容保留其固定 tag 或公告链接，不将开发版行为推定到稳定版。

- [01 · 基础与全局配置](01-basics.md)：[官方原文 1](https://wiki.metacubex.one/config/general/)、[官方原文 2](https://wiki.metacubex.one/config/inbound/tun/)
- [02 · DNS 子系统](02-dns.md)：[官方原文 1](https://wiki.metacubex.one/config/dns/)
- [03 · Providers（代理集合 / 规则集合）](03-providers.md)：[官方原文 1](https://wiki.metacubex.one/config/rule-providers/)、[官方原文 2](https://wiki.metacubex.one/config/rule-providers/content/)
- [04 · 路由规则](04-rules.md)：[官方原文 1](https://wiki.metacubex.one/config/rules/)
- [05 · Geodata（`geox-url` / dat / mmdb / mrs）](05-geodata.md)：[官方原文 1](https://wiki.metacubex.one/config/general/)
- [06 · 代理组（策略组）](06-policy-groups.md)：[官方原文 1](https://wiki.metacubex.one/config/proxy-groups/)
- [07 · 运维与排错](07-operations.md)：[官方原文 1](https://wiki.metacubex.one/api/)

## 仓库资料

- [接入示例](repository-recipes.md)描述本仓库产物，不是软件默认设置。
- `upstream.json` 是自动观察记录，采集成功不等于文档全部内容已人工验证。
- `translations.json` 是发布说明译文缓存，不作为参数支持范围的来源。
- 新增兼容性声明必须给出该产品官方文档、版本化源码或官方发布说明；社区教程仅可作为数据归属说明。

## 复核记录

2026-10-16：按各自官方文档目录重整导航，移除跨产品教程依赖，分离仓库接入示例。
本次核对了章节映射中的官方入口及关键配置主题；旧的版本专属细节仍以各节固定来源为准。
自动状态和发布日志继续由现有巡检维护。

代理集合补充来源：[配置](https://wiki.metacubex.one/config/proxy-providers/) 与 [内容](https://wiki.metacubex.one/config/proxy-providers/content/)。
