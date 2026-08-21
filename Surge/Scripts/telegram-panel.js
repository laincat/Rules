(async () => {
    try {
        const panelTitle = $panel.title || "";
        let policyName = "";
        if (panelTitle.includes("新加坡") || panelTitle.includes("DC5")) {
            policyName = "TG-SG";
        } else if (panelTitle.includes("美国") || panelTitle.includes("DC1&3")) {
            policyName = "TG-US";
        } else if (panelTitle.includes("欧洲") || panelTitle.includes("DC2")) {
            policyName = "TG-EU";
        } else {
            policyName = "TG-SG";
        }

        const info = await new Promise((resolve) => {
            $policy.getGroup(policyName, (group) => {
                if (!group) {
                    resolve({ type: "未找到", current: "未找到", latency: "N/A", traffic: "0B" });
                    return;
                }

                let type = "未知";
                if (group.type === "select") type = "手动选择";
                else if (group.type === "url-test") type = "自动测速";
                else if (group.type === "smart") type = "智能路由";
                else if (group.type === "fallback") type = "故障转移";
                else if (group.type === "load-balance") type = "负载均衡";

                const current = group.current || "未选择";

                let latency = "N/A";
                let traffic = "0B";
                if (group.policies) {
                    for (let p of group.policies) {
                        if (p.name === current) {
                            if (p.latency !== undefined && p.latency !== null) {
                                latency = p.latency + "ms";
                            }
                            if (p.statistics) {
                                const total = (p.statistics.download || 0) + (p.statistics.upload || 0);
                                const k = 1024;
                                const sizes = ["B", "KB", "MB", "GB", "TB"];
                                const i = Math.floor(Math.log(total) / Math.log(k));
                                traffic = parseFloat((total / Math.pow(k, i)).toFixed(1)) + sizes[i];
                            }
                            break;
                        }
                    }
                }

                resolve({ type, current, latency, traffic });
            });
        });

        const lines = [
            `📋 类型：${info.type}`,
            `🔗 节点：${info.current}`,
            `⏱️ 延迟：${info.latency}`,
            `📊 流量：${info.traffic}`
        ];

        $done({
            title: $panel.title,
            content: lines.join("\n"),
            style: "info"
        });
    } catch (e) {
        $done({
            title: "⚠️ 脚本错误",
            content: e.message || "未知错误",
            style: "error"
        });
    }
})();