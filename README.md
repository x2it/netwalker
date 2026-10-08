# 巡网者 NetWalker · 网络与系统运维工具箱

> Windows 本地运维 / 网络工具 / 安全自检 / 渗透测试的一体化 Web 工具箱。

**NetWalker (巡网者)** is a self-hosted browser-based ops & security toolbox for Windows: 30 pages, 58 APIs covering system monitoring, network diagnostics, port scanning, process/service management, file utilities, security baseline checks and local pentest self-audit. Single-file FastAPI backend + zero-dependency vanilla frontend — no fake features, all data from the real machine.

<img src="https://raw.githubusercontent.com/x2it/netwalker/main/banner.png" alt="巡网者 NetWalker · 网络与系统运维工具箱" width="100%">

---

## 项目定位

NetWalker（巡网者）是一个**本机部署、浏览器访问**的单文件后端 + 原生前端的运维与安全工具箱。面向 Windows 系统，用 PowerShell / psutil / subprocess 采集本机真实数据，无任何虚假/占位功能。

**目标用户**：系统运维工程师、网络工程师、安全工程师、个人极客、蓝队/红队本机自检。

**设计风格**：扁平化深色主题 + 极简留白 + 真实动作可视化进度。

---

## 技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| 后端 | Python 3.10+ / FastAPI / uvicorn | 单文件 `server.py`，2100+ 行，58 个 API |
| 前端 | 原生 HTML + CSS + JS（零框架） | `index.html` + `app.js` + `style.css` |
| 系统调用 | subprocess / PowerShell / psutil / netsh / whoami | Windows 原生，不跨平台 |
| 流式推送 | SSE (EventSource) | 端口扫描实时进度与开放端口发现 |

---

## 快速开始

### 1. 安装依赖

```powershell
# 使用 requirements.txt 一键安装
pip install -r requirements.txt

# 或手动安装
pip install fastapi uvicorn psutil pydantic

# 国内推荐用阿里云镜像：
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
```

### 2. 启动

```powershell
cd sysops
python server.py
# 浏览器打开  http://127.0.0.1:8765
```

默认监听 `127.0.0.1:8765`（仅本机可访问，不含任何认证，请勿直接暴露到公网）。

### 3. 运行测试

```powershell
python test_full.py
```

---

## 功能模块（30 个页面 · 58 个 API）

### 🖥 系统监控

| 页面 | 说明 |
|---|---|
| 仪表盘 | CPU / 内存 / 磁盘环形仪表盘 + 系统信息 + 分区占用 |
| 实时监控 | Canvas 折线图实时绘制 CPU/内存历史 + 网络 I/O |
| CPU 监控 | 总体使用率 + 频率 + 每核可视化柱 |
| 内存 & 磁盘 | 物理内存 / 交换 / 分区详情表 |
| 网络接口 | IPv4 / IPv6 / MAC / 发送接收流量 |
| 环境变量 | 实时搜索过滤 |
| 电源 & 补丁 | 电源计划 / 传感器 / 已装补丁 |
| **进程树** ⭐ | 父子进程层级结构 + CPU/内存占用可视化 |

### 🌐 网络工具

| 页面 | 说明 |
|---|---|
| 网络诊断 | Ping / DNS / 路由追踪 / Whois / 单端口检测 / IP配置 / 路由表 / ARP（8 个 Tab） |
| 端口扫描 | **SSE 流式** 200 线程并发、端口服务名映射、常用范围快捷、发现端口实时闪烁 |
| **带宽测试** ⭐ | 延迟测量（10次）+ 吞吐量测试，支持自定义目标和时长 |
| SSL & HTTP | 证书详情 + 状态码 + HTTP Headers |
| Wi-Fi 信息 | 接口 + 配置文件（修复中文乱码） |
| 子网计算器 | 地址/掩码/广播/可用主机 列表展开 |
| 连接监控 | 所有 TCP/UDP 连接及状态徽章 |

### 🛠 管理工具

| 页面 | 说明 |
|---|---|
| 进程管理 | CPU/内存/PID/名称排序 + 一键结束进程 |
| 服务管理 | 运行中/已停止过滤 + 搜索 + 启动/停止 |
| 计划任务 | 搜索 + 下次/上次运行时间 |
| 命令终端 | 任意命令执行 + 快捷命令按钮 + 危险命令拦截 |

### 📁 文件工具

| 页面 | 说明 |
|---|---|
| 文件哈希 | MD5/SHA1/SHA256/SHA512 |
| 大文件查找 | 目录递归 + 阈值 MB |
| 磁盘分析 | Top 目录占用排行 |
| 重复文件 | 内容哈希分组检测 |
| 清理临时 | 临时目录垃圾清理 + 释放 MB 统计 |
| **文件删除** ⭐ | 安全限制下的文件/目录删除，支持递归删除 |

### 🛡 安全

| 页面 | 说明 |
|---|---|
| 安全中心 | 防火墙 / 本地用户 / 启动项 / Defender / 密码策略 |
| 安全评估 | **综合评分卡 + 10 项基线检查 + 攻击面分析**，可导出 HTML 报告 |
| 事件日志 | System / Application / Security 三类 |
| 已装程序 | 注册表项扫描已安装程序 |
| 共享文件夹 | net share 输出 |

### 🔬 渗透测试（本机自检）

| 页面 | 说明 |
|---|---|
| 提权路径 | AlwaysInstallElevated / 可写目录 / 未签名服务 / 令牌特权 / LOLBins，**可导出报告** |
| 持久化检查 | Run 注册表 / 启动文件夹 / 计划任务 / 服务 / WMI / IFEO，**可导出报告** |
| 弱口令审计 | 空密码 / Guest 状态 / LM Hash / 密码策略，**可导出报告** |
| 反取证检测 | 混杂模式 / 可疑进程 / 日志清除痕迹 / Defender 状态，**可导出报告** |

> 渗透测试模块仅对本机安全自检合法，非攻击工具。

⭐ v2.2 新增功能

---

## 文件结构

```
sysops/
├── server.py                # FastAPI 后端：58 个 API
├── requirements.txt         # Python 依赖清单
├── README.md                # 本文件
├── LICENSE                  # MIT License（2026 知行工作室）
├── .gitignore
├── HANDOVER.md              # 项目交接文档
├── test_full.py             # API 冒烟测试脚本
└── static/
    ├── index.html           # 页面骨架（30 个 page 容器）
    ├── css/
    │   └── style.css        # 深色主题 CSS v2.2
    └── js/
        └── app.js           # 前端逻辑（导航/渲染/SSE扫描/导出）
```

---

## 更新日志

### v2.2.0 (2026-08-21)

**新增功能：**
- 📊 **进程树视图** — 展示父子进程层级关系，实时显示 CPU/内存占用，按资源占用率排序
- 📶 **带宽测试** — 测量到目标主机的延迟（10次采样）和吞吐量，支持自定义测试时长
- 🗑 **文件删除** — 支持安全限制下的文件/目录删除，不允许删除系统关键目录
- 🏷 **端口服务名映射** — 端口扫描结果现在返回服务名称（如 HTTP, SSH, MySQL 等）
- 🔒 **增强的 CORS 配置** — 限制允许的源，添加 DELETE 方法支持

**功能优化：**
- 🚀 端口扫描性能优化：200 线程并发，单次扫描范围扩展至 1024 端口
- 📝 报告导出功能：安全评估和渗透测试模块支持一键导出 HTML 报告
- 🎨 全面的动作可视化：所有耗时操作显示进度反馈，避免"假死"
- 🌐 Wi-Fi 信息中文乱码修复：解决 netsh 命令双重编码问题
- 💾 磁盘总量显示修复：正确累加所有分区容量

**安全与稳定：**
- 🔒 CORS 配置收紧，仅允许本地开发源
- 🧵 线程安全改进：CPU/内存历史数据使用锁保护
- ⚠️ 文件删除 API 添加系统目录保护机制
- 🔧 编码处理增强：智能检测系统 ANSI 编码，UTF-8 优先

**UI/UX 改进：**
- 📱 移动端适配：汉堡菜单 + 响应式布局
- 🎨 质感提升：卡片阴影 hover、导航左色条、空状态优化
- 🔘 按钮交互反馈：加载状态禁用 + spinner 动画
- 📋 快捷操作：端口扫描常用范围快捷按钮

### v2.1.0 (2026-08-20)

- 端口扫描 SSE 流式推送
- 动作可视化反馈体系
- 报告导出功能
- 版权信息统一
- 开源准备（LICENSE + .gitignore）

### v2.0.0 (2026-08-19)

- 首个稳定版本发布
- 完整的系统信息采集
- 网络诊断工具集
- 安全基线检查
- 渗透测试模块（本机自检）

---

## API 清单（58 个端点）

### 系统信息 `/api/system/*` (11)
| 路径 | 方法 | 功能 |
|---|---|---|
| `/api/system/overview` | GET | 系统总览：CPU/内存/磁盘/开机时间 |
| `/api/system/cpu` | GET | CPU 详情 + 每核使用率 |
| `/api/system/memory` | GET | 物理内存 + 交换分区 |
| `/api/system/disks` | GET | 磁盘分区列表 |
| `/api/system/network-interfaces` | GET | 网卡列表 |
| `/api/system/env` | GET | 环境变量 |
| `/api/system/process-tree` | GET | ⭐ 进程树视图（父子关系 + 资源占用） |
| `/api/system/updates` | GET | 系统更新历史 |
| `/api/system/power` | GET | 电源计划 |
| `/api/system/sensors` | GET | 传感器（温度/风扇/电池） |
| `/api/system/history` | GET | 开机/关机历史 |

### 网络工具 `/api/network/*` (16)
| 路径 | 方法 | 功能 |
|---|---|---|
| `/api/network/ping` | GET | Ping 测试 |
| `/api/network/dns` | GET | DNS 解析 |
| `/api/network/tracert` | GET | 路由追踪 |
| `/api/network/whois` | GET | Whois 查询 |
| `/api/network/port-check` | GET | 单端口检测 |
| `/api/network/scan` | GET | 端口扫描（200线程并发） |
| `/api/network/scan-stream` | GET | 端口扫描（SSE 流式进度） |
| `/api/network/connections` | GET | 网络连接列表 |
| `/api/network/ipconfig` | GET | IP 配置 |
| `/api/network/route` | GET | 路由表 |
| `/api/network/arp` | GET | ARP 表 |
| `/api/network/ssl-cert` | GET | SSL 证书检查 |
| `/api/network/http-headers` | GET | HTTP 头检测 |
| `/api/network/wifi` | GET | Wi-Fi 接口 + 配置文件 |
| `/api/network/subnet` | GET | 子网计算器 |
| `/api/network/bandwidth-test` | GET | ⭐ 带宽/延迟测试 |

### 进程与服务 (5)
| 路径 | 方法 | 功能 |
|---|---|---|
| `/api/processes` | GET | 进程列表（CPU/内存/PID/名称排序） |
| `/api/processes/{pid}/kill` | POST | 结束进程 |
| `/api/services` | GET | 服务列表 |
| `/api/services/{name}/start` | POST | 启动服务 |
| `/api/services/{name}/stop` | POST | 停止服务 |

### 安全中心 `/api/security/*` (13)
| 路径 | 方法 | 功能 |
|---|---|---|
| `/api/security/firewall` | GET | 防火墙状态 |
| `/api/security/users` | GET | 本地用户列表 |
| `/api/security/startup` | GET | 启动项 |
| `/api/security/logged-on` | GET | 已登录用户 |
| `/api/security/defender` | GET | Defender 状态 |
| `/api/security/programs` | GET | 已装程序 |
| `/api/security/tasks` | GET | 计划任务 |
| `/api/security/shares` | GET | 共享文件夹 |
| `/api/security/eventlog` | GET | 事件日志 |
| `/api/security/password-policy` | GET | 密码策略 |
| `/api/security/hotfixes` | GET | 已安装补丁 |
| `/api/security/baseline` | GET | 安全基线检查 |
| `/api/security/attack-surface` | GET | 攻击面分析 |

### 渗透测试 `/api/pentest/*` (4)
| 路径 | 方法 | 功能 |
|---|---|---|
| `/api/pentest/privesc` | GET | 提权路径扫描 |
| `/api/pentest/persistence` | GET | 持久化点扫描 |
| `/api/pentest/weak-credentials` | GET | 弱口令审计 |
| `/api/pentest/anti-forensics` | GET | 反取证检测 |

### 文件工具 `/api/files/*` (6)
| 路径 | 方法 | 功能 |
|---|---|---|
| `/api/files/hash` | GET | 文件哈希计算 |
| `/api/files/large` | GET | 大文件查找 |
| `/api/files/analyze` | GET | 磁盘占用分析 |
| `/api/files/clean-temp` | POST | 清理临时文件 |
| `/api/files/duplicates` | GET | 重复文件检测 |
| `/api/files/delete` | DELETE | ⭐ 文件/目录删除 |

### 通用 (3)
| 路径 | 方法 | 功能 |
|---|---|---|
| `/api/terminal/run` | POST | 命令终端 |
| `/` | GET | 返回前端页面 |
| `/api/health` | GET | 健康检查 |

---

## 设计规范

- **主题色**：青绿色 `#2dd4bf` 作为主强调色
- **背景**：深色 `#0d1117` / `#161b22` / `#21262d` 三层
- **状态色**：绿 `#22c55e` / 黄 `#eab308` / 红 `#ef4444` / 蓝 `#3b82f6`
- **圆角**：`--radius:10px`（卡片）/ `--radius-sm:6px`（按钮、徽章）
- **字体**：系统字体 + JetBrains Mono（等宽，用于数字/路径/代码）
- **间距**：卡片间 16px，强调"呼吸感"

---

## 合法使用声明

本软件**仅用于**：
- 学习研究
- 合法授权下的本机安全自检

**禁止**用于未经授权的外部扫描/渗透/攻击。使用者对行为承担全部法律责任。

---

## 许可证

[MIT](LICENSE) © 2026 知行工作室 Zhixing Studio · [https://w3b.pub/](https://w3b.pub/) · support@w3b.pub
