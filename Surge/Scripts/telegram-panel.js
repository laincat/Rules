(async () => {
    try {
        // 通过 $input.panelName 获取当前触发的面板名称
        // 官方手册: $input = { purpose: "panel", position: "policy-selection", panelName: "PanelB" }
        const panelName = $input.panelName || "";
        
        // 根据面板名称映射到对应的策略组
        let policyName = "TG-SG";
        if (panelName.includes("SG") || panelName.includes("DC5")) {
            policyName = "TG-SG";
        } else if (panelName.includes("US") || panelName.includes("DC1&3")) {
            policyName = "TG-US";
        } else if (panelName.includes("EU") || panelName.includes("DC2")) {
            policyName = "TG-EU";
        }

        // 格式化流量
        function formatBytes(bytes) {
            if (!bytes || bytes === 0) return "0B";
            const k = 1024;
            const sizes = ["B", "KB", "MB", "GB", "TB"];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + sizes[i];
        }

        // 获取策略组信息
        const info = await new Promise((resolve) => {
            $policy.getGroup(policyName, (group) => {
                try {
                    if (!group) {
                        resolve({ 
                            type: "未找到", 
                            current: "未找到", 
                            latency: "N/A", 
                            traffic: "0B" 
                        });
                        return;
                    }

                    // 识别策略组类型
                    let type = "未知";
                    if (group.type === "select") type = "手动选择";
                    else if (group.type === "url-test") type = "自动测速";
                    else if (group.type === "smart") type = "智能路由";
                    else if (group.type === "fallback") type = "故障转移";
                    else if (group.type === "load-balance") type = "负载均衡";

                    const current = group.current || "未选择";
                    let latency = "N/A";
                    let traffic = "0B";

                    // 获取当前选中节点的延迟和流量
                    if (group.policies && Array.isArray(group.policies)) {
                        for (let p of group.policies) {
                            if (p.name === current) {
                                if (p.latency !== undefined && p.latency !== null) {
                                    latency = p.latency + "ms";
                                }
                                if (p.statistics) {
                                    const total = (p.statistics.download || 0) + (p.statistics.upload || 0);
                                    traffic = formatBytes(total);
                                }
                                break;
                            }
                        }
                    }

                    resolve({ type, current, latency, traffic });
                } catch (err) {
                    resolve({ 
                        type: "错误", 
                        current: policyName, 
                        latency: "N/A", 
                        traffic: "0B" 
                    });
                }
            });
        });

        // 返回面板内容
        $done({
            title: panelName || "Telegram 状态",
            content: `📋 类型：${info.type}\n🔗 节点：${info.current}\n⏱️ 延迟：${info.latency}\n📊 流量：${info.traffic}`,
            style: "info"
        });

    } catch (e) {
        // 错误时显示详细信息，方便排查
        $done({
            title: "⚠️ 脚本错误",
            content: e.message || "未知错误",
            style: "error"
        });
    }
})();
