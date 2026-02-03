# CF-Speed-DNS

<p align="center">
  <b>🚀 Cloudflare 优选 IP 自动 DNS 解析推送工具</b>
</p>

<p align="center">
  自动获取 Cloudflare CDN 最快节点 IP，并推送到 DNS 解析服务
</p>

---

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 🌐 **优选 IP 获取** | 自动从测速网站获取电信/移动/联通最优 IP |
| ⚡ **自动 DNS 更新** | 支持 Cloudflare DNS 和 DNSPod 自动解析 |
| 📱 **消息推送** | 通过 PushPlus 推送更新通知到微信 |
| ⏰ **定时运行** | GitHub Actions 每 6 小时自动执行 |
| 🎯 **多线路支持** | 支持电信、联通等多种运营商线路 |

---

## 📁 项目结构

```
cf-speed-dns/
├── dnscf.py          # Cloudflare DNS 更新（旧版电信）
├── dnscf_dx.py       # Cloudflare DNS 更新（电信线路，Playwright版）
├── dnscf_lt.py       # Cloudflare DNS 更新（联通线路，Playwright版）
├── dnspod.py         # DNSPod DNS 更新
├── qCloud.py         # 腾讯云相关
├── requirements.txt  # Python 依赖
└── .github/workflows/
    ├── dns_cf.yml    # 旧版电信优选 Action
    ├── dns_cf_dx.yml # 电信优选 Action（Playwright）
    ├── dns_cf_lt.yml # 联通优选 Action（Playwright）
    ├── dns_pod.yml   # DNSPod Action
    └── sync.yml      # 同步 Action
```

---

## 🚀 快速开始

### 1. Fork 本项目

点击右上角 **Fork** 按钮，将项目复制到你的 GitHub 账户。

### 2. 配置 Secrets

进入你的仓库 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

#### Cloudflare DNS 配置

| Secret 名称 | 说明 | 示例 |
|------------|------|------|
| `CF_API_TOKEN` | Cloudflare API Token | `xxxxxxxxxxxxxxxx` |
| `CF_ZONE_ID` | Cloudflare Zone ID | `xxxxxxxxxxxxxxxx` |
| `CF_DNS_NAME` | 旧版电信优选域名 | `cf.example.com` |
| `CF_DNS_NAME_DX` | 电信优选域名（Playwright版，支持多个） | `dx1.example.com,dx2.example.com` |
| `CF_DNS_NAME_YD` | 联通优选域名（支持多个） | `lt1.example.com,lt2.example.com` |
| `PUSHPLUS_TOKEN` | PushPlus 推送 Token | `xxxxxxxxxxxxxxxx` |

#### DNSPod 配置（可选）

| Secret 名称 | 说明 |
|------------|------|
| `DOMAIN` | 主域名，如 `example.com` |
| `SUB_DOMAIN` | 子域名，如 `dns` |
| `SECRETID` | 腾讯云 SecretId |
| `SECRETKEY` | 腾讯云 SecretKey |

### 3. 启用 Actions

进入 **Actions** 标签页，启用 workflow，或手动触发运行。

---

## ⏰ 运行频率

| Workflow | 运行频率 | 说明 |
|----------|---------|------|
| `dns_cf.yml` | 每 6 小时 | 旧版电信优选 IP 更新 |
| `dns_cf_dx.yml` | 每 6 小时 | 电信优选 IP 更新（Playwright） |
| `dns_cf_lt.yml` | 每 6 小时 | 联通优选 IP 更新（Playwright） |
| `dns_pod.yml` | 每 6 小时 | DNSPod 更新 |

---

## 📡 优选 IP 接口

### 在线页面
- 实时优选 IP 列表：[https://ip.164746.xyz](https://ip.164746.xyz)

### API 接口

```bash
# 获取 Top IP
curl 'https://ip.164746.xyz/ipTop.html'
# 返回: 104.16.204.6,104.18.103.125

# 获取 Top 10 IP
curl 'https://ip.164746.xyz/ipTop10.html'
```

---

## 🔧 技术说明

### 联通优选 (dnscf_lt.py)

使用 **Playwright** 无头浏览器获取动态加载的优选 IP：
- 数据源：`https://api.uouin.com/cloudflare.html`
- 等待 JavaScript 完全加载后解析数据
- 自动筛选联通线路 IP

### 多域名模式

支持配置多个域名（逗号分隔），每个域名对应一个优选 IP：

```
CF_DNS_NAME_YD=lt1.example.com,lt2.example.com,lt3.example.com
```

---

## 📱 消息推送

集成 [PushPlus](https://www.pushplus.plus/) 微信推送服务：

1. 访问 [PushPlus](https://www.pushplus.plus/) 获取 Token
2. 将 Token 添加到 GitHub Secrets: `PUSHPLUS_TOKEN`
3. DNS 更新后自动推送通知到微信

---

## 🙏 致谢

- [XIU2/CloudflareSpeedTest](https://github.com/XIU2/CloudflareSpeedTest) - Cloudflare 测速工具
- [ddgth/cf2dns](https://github.com/ddgth/cf2dns) - CF 优选 IP 推送

---

## 📄 License

MIT License

---

<p align="center">
  <a href="https://dartnode.com" title="Powered by DartNode - Free VPS for Open Source">
    <img src="https://dartnode.com/branding/DN-Open-Source-sm.png" alt="Powered by DartNode">
  </a>
</p>
