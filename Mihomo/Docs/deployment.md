# Mihomo · Docker、系统代理与 TUN

[返回导航](readme.md) · [来源说明](sources.md)

这是本仓库的部署检查清单。字段含义以 [官方全局配置](https://wiki.metacubex.one/config/general/) 与 [官方 TUN 文档](https://wiki.metacubex.one/config/inbound/tun/) 为准。

## 同一配置的三个入口

- 本机系统代理：由操作系统或客户端把 HTTP/SOCKS 流量交给 `mixed-port`。内核启动不表示系统代理已设置。
- LAN 代理：保留 `allow-lan: true` 和合适的 `bind-address`；客户端指向运行内核机器的 LAN 地址和代理端口。
- TUN：保留 `tun.enable: true`，由对应主机的网络设备、权限和路由接管流量。

LAN 代理端口和管理 API 是不同入口。开放代理给可信局域网，不表示应该把管理 API 或 DNS 递归服务暴露给公网；按需设置认证、访问限制与主机防火墙。

## Docker 检查顺序

1. 先确认运行内核版本及配置挂载路径。以 [仓库配置](../config.yaml) 为基础，保留实际订阅与节点设置，不重复粘贴多个顶层 `dns` / `tun` / `rules`。
2. 端口映射或 host 网络必须匹配实际部署。容器里的 `127.0.0.1` 指向容器自身；桥接网络下仅监听回环地址的服务不能靠端口发布直接访问。
3. TUN 需要容器获得相应网络设备与权限。检查 `/dev/net/tun`、容器网络命名空间与路由；单纯发布代理端口不能证明宿主机流量经过 TUN。
4. Docker Desktop 的 Linux 虚拟机与原生 Linux 主机的网络不同。不要直接套用 Linux host 网络或路由结论，先明确要接管的是容器、宿主机还是局域网设备。
5. 不因排错直接使用广泛的特权模式；从启动日志确认所缺的设备或网络能力，只授予部署所需权限。

本页不提供通用 Compose 模板：设备、网络模式和权限需结合部署主机确定。

## 应用前与应用后

```sh
mihomo -v
mihomo -t -f config.yaml
```

在容器内运行时，使用容器实际配置路径；在原生内核运行时，使用本机路径。
语法测试成功后仍需检查 provider 下载、DNS、路由和真实请求，不能当成联网验收。

- 系统代理：本机请求是否进入请求日志，目标策略是否正确
- LAN：第二台设备经代理端口能否连接，管理 API 是否仍受保护
- TUN：启停前后目标路由与连接记录是否符合预期；LAN 地址是否仍可访问
- DNS：本地解析与被接管流量是否走预期解析路径，避免回环与重复接管
- 更新：查看 [官方发布记录](https://github.com/MetaCubeX/mihomo/releases) 后再更换内核；本仓库规则订阅使用固定 `latest` 附件，内核版本与规则附件版本分开管理

## 本仓库 Geodata

已验证的自有镜像配置集中在 [config.yaml](../config.yaml) 的 `geox-url`，四项分别对应 GEOIP、GEOSITE、国家 IP 库和 ASN 库。
GeoIP 镜像使用它自己的固定发布 tag `geoip`；Rules 规则附件使用 `latest`。不要批量替换不同仓库的 tag。
更换源前核对文件名、大小或校验和以及实际分类覆盖，不把下载成功等同于内容等价。
