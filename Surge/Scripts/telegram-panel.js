(async () => {
    try {
        // 通过 $input.panelName 获取当前触发的面板名称
        const panelName = $input.panelName || "";
        let policyName = "TG-SG"; // 默认

        // 根据面板名称映射到策略组
        if (panelName.includes("SG") || panelName.includes("DC5")) {
            policyName = "TG-SG";
        } else if (panelName.includes("US") || panelName.includes("DC1&3")) {
            policyName = "TG-US";
        } else if (panelName.includes("EU") || panelName.includes("DC2")) {
            policyName = "TG-EU";
        }

        // ... (策略组信息获取逻辑保持不变) ...

        // 返回面板内容
        $done({
            title: $input.panelName || "Telegram 状态",
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
