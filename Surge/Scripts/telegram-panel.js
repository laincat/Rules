(async () => {
    try {
        // ✅ 正确：通过 $input.panelName 获取面板标识
        const panelName = $input.panelName || "";
        let policyName = "";
        
        // 根据面板名称映射到对应的策略组
        if (panelName.includes("SG") || panelName.includes("DC5")) {
            policyName = "TG-SG";
        } else if (panelName.includes("US") || panelName.includes("DC1&3")) {
            policyName = "TG-US";
        } else if (panelName.includes("EU") || panelName.includes("DC2")) {
            policyName = "TG-EU";
        } else {
            policyName = "TG-SG"; // fallback
        }

        // 后续逻辑保持不变：通过 $policy.getGroup 获取策略组信息
        const info = await new Promise((resolve) => {
            $policy.getGroup(policyName, (group) => {
                // ... 处理 group 数据 ...
            });
        });

        $done({
            title: "🇸🇬 Telegram 新加坡 (DC5)",  // 标题可以硬编码或动态生成
            content: `📋 类型：${info.type}\n🔗 节点：${info.current}\n⏱️ 延迟：${info.latency}\n📊 流量：${info.traffic}`,
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
