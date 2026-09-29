"""关键服务观察名单 —— 构建期 honor_upstream_exceptions 的收窄依据。

哪些域名「整站 REJECT 会出事」，这份判断必须集中维护。
机制②（尊重上游白名单）用它收窄作用域：上游有「条件放行」信号
（@@ 例外 / 仅带 $modifier）+ 域名在本名单内 → 撤销其整站条目。

不单独收窄就放行会把上游 1000+ 个广告网络一起放出去。
"""
from __future__ import annotations

# 常见两段式公共后缀（够用即可，不是完整 PSL）
TWO_LEVEL = set("""
com.cn net.cn org.cn gov.cn edu.cn ac.cn com.hk com.tw com.br com.au com.mx
com.tr com.bd com.ar com.sg com.my com.vn com.ua com.pl com.ph com.pk com.co
co.uk org.uk ac.uk gov.uk co.jp or.jp ne.jp ac.jp co.kr or.kr co.nz co.za
co.il co.in co.id co.th net.au org.au edu.au net.br org.br
""".split())

# 整站被 REJECT 会明显出问题的主域（eTLD+1）
WATCH = {
    # 通用 CDN / 静态资源
    "cloudfront.net", "akamai.com", "akamaihd.net", "akamaized.net",
    "cloudflare.com", "fastly.net", "fastlylb.net", "cdn77.org",
    "jsdelivr.net", "unpkg.com", "googleapis.com", "gstatic.com",
    "googleusercontent.com", "googletagmanager.com", "google-analytics.com",
    "google.com", "google.cn", "alicdn.com", "aliyun.com", "aliyuncs.com",
    "myqcloud.com", "qcloud.com", "qiniu.com", "qiniudn.com", "upyun.com",
    "bcebos.com", "bdstatic.com", "ksyun.com", "huaweicloud.com",
    "azure.com", "azureedge.net", "microsoft.com", "windows.com",
    "windows.net", "office.com", "office365.com", "live.com", "outlook.com",
    "microsoftonline.com", "apple.com", "icloud.com", "mzstatic.com",
    "aaplimg.com", "apple-cloudkit.com",
    # 支付 / 电商
    "alipay.com", "alipayobjects.com", "taobao.com", "tmall.com", "jd.com",
    "360buy.com", "paypal.com", "stripe.com", "weixin.qq.com", "wechat.com",
    "tenpay.com", "unionpay.com", "qq.com", "weibo.com", "sina.com.cn",
    "sinaimg.cn", "sina.cn", "sohu.com", "163.com", "126.com", "126.net",
    "douban.com", "zhihu.com", "bilibili.com", "hdslb.com", "douyu.com",
    "huya.com", "kuaishou.com", "douyin.com", "iesdouyin.com",
    "bytedance.com", "toutiao.com", "snssdk.com", "pstatp.com",
    "byteimg.com", "baidu.com", "bdimg.com", "gtimg.com", "qlogo.cn",
    "xiaomi.com", "mi.com", "huawei.com", "honor.com", "oppo.com",
    "vivo.com", "meizu.com", "samsung.com", "oneplus.com",
    # 推送 / 统计 / 登录 / 更新
    "umeng.com", "umengcloud.com", "getui.com", "jpush.cn", "xg.qq.com",
    "appstore.com", "itunes.com", "googleplay.com", "gvt1.com", "apkpure.com",
    # 开发 / 协作
    "github.com", "githubusercontent.com", "githubassets.com", "gitlab.com",
    "npmjs.com", "pypi.org", "docker.com", "stackoverflow.com", "sentry.io",
    # 其它
    "wikipedia.org", "wikimedia.org", "openai.com", "anthropic.com",
    "notion.so", "figma.com", "dropbox.com", "onedrive.com",
}


def etld1(host: str) -> str:
    """粗略但够用的 eTLD+1。"""
    p = host.split(".")
    if len(p) >= 3 and ".".join(p[-2:]) in TWO_LEVEL:
        return ".".join(p[-3:])
    return ".".join(p[-2:]) if len(p) >= 2 else host
# 命中 WATCH 时给出人话说明：这域名到底是干嘛的、整站拦了会怎样
SERVICE = {
    "getui.com": "个推（国内主流 App 推送通道）→ 收不到推送",
    "jpush.cn": "极光推送（国内主流 App 推送通道）→ 收不到推送",
    "umeng.com": "友盟统计 + 推送 → 推送受影响；统计子域本来就单独列了",
    "umengcloud.com": "友盟云（统计上报）→ 同上",
    "google-analytics.com": "Google Analytics，去追踪的常规目标",
    "googletagmanager.com": "Google 标签管理器，部分网站用它注入功能脚本，拦了可能页面异常",
    "cloudfront.net": "AWS CDN",
    "baidu.com": "百度",
    "qq.com": "腾讯",
    "taobao.com": "淘宝",
    "xiaomi.com": "小米",
    "windows.com": "微软",
    "microsoft.com": "微软",
    "aliyuncs.com": "阿里云",
    "sina.com.cn": "新浪",
    "sina.cn": "新浪",
    "apple.com": "苹果",
    "googleapis.com": "Google API",
    "fastly.net": "Fastly CDN",
    "akamaihd.net": "Akamai CDN",
    "bcebos.com": "百度云对象存储",
    "163.com": "网易",
    "126.net": "网易",
    "sohu.com": "搜狐",
    "samsung.com": "三星",
    "meizu.com": "魅族",
    "mi.com": "小米",
    "huya.com": "虎牙",
    "snssdk.com": "字节跳动 SDK",
    "google.com": "Google",
    "windows.net": "微软 Azure",
    "jd.com": "京东",
}
