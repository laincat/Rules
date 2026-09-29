本目录下的 Ozon / AI 规则集由 tools/gen_rulesets.py 自动生成
（GitHub Actions: gen-rulesets.yml 每日运行），请勿手改。

每个规则集两个文件，配套使用:

| 文件 | behavior | 内容 |
|---|---|---|
| Ozon.mrs / AI.mrs | domain | 纯域名 trie，format: mrs，主路径 |
| Ozon.yaml / AI.yaml | classical | 全量（含关键词 / IP-CIDR / IP-ASN），补充路径 |

两个 provider 一起挂，mrs 的 RULE-SET 放在 yaml 前面:
域名流量在 trie 里短路命中，yaml 只兜底关键词与 IP 规则。
只用 yaml 单文件的旧订阅不受影响（classical 本身就是全量）。

.mrs 由 CI 里的 mihomo convert-ruleset domain text 编译，
域名源是生成过程的中间产物，不进仓库。
