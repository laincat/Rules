(async () => {
    try {
        // 直接从面板配置中读取 policy 参数
        const policyName = $panel.policy || "TG-SG";

        const info = await new Promise((resolve) => {
            $policy.getGroup(policyName, (group) => {
                // ... 原有逻辑保持不变 ...
                // 这里 group 不存在时返回 "未找到"
                if (!group) {
                    resolve({ type: "未找到", current: "未找到", latency: "N/A", traffic: "0B" });
                    return;
                }
                // ... 处理 group 数据 ...
            });
        });

        // ... 构建并返回内容 ...
        $done({
            title: $panel.title, // 这里依然使用 $panel.title 作为标题
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
