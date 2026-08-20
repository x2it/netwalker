# 巡网者 NetWalker · 项目交接说明

> 系统运维 + 网络安全工具箱（Web UI 应用）
> 接手前请通读本文档，再打开 `server.py` 与 `static/index.html` 对照查看。

---

## 一、项目概述

- **定位**：Windows 系统运维 + 网络安全一体的本地 Web 工具箱
- **形态**：前后端分离的单机 Web 应用（浏览器访问本地服务）
- **目标用户**：运维工程师 / 安全工程师 / 个人极客
- **设计风格**：扁平化深色主题，极简、有呼吸感，强调真实可用（无假功能）
- **当前版本**：v2.2.0（2026-08-21）

## 二、技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| 后端 | Python 3.10+ / FastAPI / uvicorn | 单文件 `server.py`，2100+ 行，58 个 API |
| 前端 | 原生 HTML + CSS + JS（无框架） | `index.html` + `app.js` + `style.css` |
| 系统调用 | subprocess / PowerShell / psutil | 通过 `netsh`/`net`/`whoami`/`Get-*` 等 |
| 流式推送 | SSE (EventSource) | 端口扫描实时进度 |
| 运行环境 | Windows（依赖 PowerShell 与 netsh） | 不跨平台，Linux 需重写命令层 |

### 依赖安装

```powershell
# 推荐使用 requirements.txt
pip install -r requirements.txt

# 或手动安装
pip install fastapi uvicorn psutil pydantic

# 国内镜像（推荐阿里云）：
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
```

### 启动

```powershell
cd sysops
python server.py
# 或使用 uvicorn
python -m uvicorn server:app --host 127.0.0.1 --port 8765 --log-level info
# 浏览器打开 http://127.0.0.1:8765/
```

## 三、文件结构

```
sysops/
├── server.py              # 后端核心：所有 API（FastAPI，2100+ 行）
├── requirements.txt       # Python 依赖清单
├── README.md              # 项目说明文档（用户手册）
├── HANDOVER.md            # 本交接文档
├── LICENSE                # MIT License
├── .gitignore             # Git 忽略规则
├── test_full.py           # API 自动化测试脚本（可选）
├── __pycache__/           # Python 缓存（可删，已在 .gitignore 中）
└── static/                # 前端静态资源
    ├── index.html         # 页面骨架（30 个 page 容器）
    ├── css/
    │   └── style.css      # 全局样式 + 主题变量 + 组件样式 v2.2
    └── js/
        └── app.js         # 前端逻辑（导航、API 调用、渲染、SSE、导出）
```

## 四、后端 API 清单（共 58 个端点）

> 所有 API 以 `/api/` 开头，返回 JSON。命令执行统一用 `run_command()` / `run_powershell()`。

### 4.1 系统信息 `/api/system/*` (11)
| 路径 | 方法 | 功能 |
|---|---|---|
| `/api/system/overview` | GET | 系统总览：CPU/内存/磁盘(累加所有分区)/开机时间 |
| `/api/system/cpu` | GET | CPU 详情 + 每核使用率 + 频率 |
| `/api/system/memory` | GET | 物理内存 + 交换分区 |
| `/api/system/disks` | GET | 磁盘分区列表 |
| `/api/system/network-interfaces` | GET | 网卡列表 |
| `/api/system/env` | GET | 环境变量 |
| `/api/system/process-tree` | GET | ⭐ 进程树视图（父子关系 + CPU/内存占用） |
| `/api/system/updates` | GET | 系统更新历史 |
| `/api/system/power` | GET | 电源计划 |
| `/api/system/sensors` | GET | 传感器（温度/风扇/电池） |
| `/api/system/history` | GET | 开机/关机历史 |

### 4.2 网络工具 `/api/network/*` (16)
| 路径 | 方法 | 功能 |
|---|---|---|
| `/api/network/ping` | GET | Ping |
| `/api/network/dns` | GET | DNS 解析 |
| `/api/network/tracert` | GET | 路由追踪 |
| `/api/network/whois` | GET | Whois |
| `/api/network/port-check` | GET | 单端口检测 |
| `/api/network/scan` | GET | 端口扫描（200 线程 + 服务名映射） |
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

### 4.3 进程与服务 (5)
| 路径 | 方法 | 功能 |
|---|---|---|
| `/api/processes` | GET | 进程列表（CPU/内存/PID/名称排序） |
| `/api/processes/{pid}/kill` | POST | 结束进程 |
| `/api/services` | GET | 服务列表 |
| `/api/services/{name}/start` | POST | 启动服务 |
| `/api/services/{name}/stop` | POST | 停止服务 |

### 4.4 安全中心 `/api/security/*` (13)
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
| `/api/security/eventlog` | GET | 事件日志（System/Application/Security） |
| `/api/security/password-policy` | GET | 密码策略 |
| `/api/security/hotfixes` | GET | 已安装补丁 |
| `/api/security/baseline` | GET | **安全基线检查（评分+10项）** |
| `/api/security/attack-surface` | GET | **攻击面分析（监听+外联+高风险服务）** |

### 4.5 渗透测试（本地自检） `/api/pentest/*` (4)
> 仅针对本机安全自检，非攻击工具
| 路径 | 方法 | 功能 |
|---|---|---|
| `/api/pentest/privesc` | GET | 提权路径扫描（AlwaysInstallElevated/可写目录/未签名服务/令牌特权/LOLBins） |
| `/api/pentest/persistence` | GET | 持久化点扫描（Run注册表/启动文件夹/计划任务/服务/WMI/IFEO） |
| `/api/pentest/weak-credentials` | GET | 弱口令审计（空密码/Guest/LM Hash/密码策略/匿名会话） |
| `/api/pentest/anti-forensics` | GET | 反取证检测（嗅探器/可疑进程/日志清除/Defender状态/隐蔽外联） |

### 4.6 文件工具 `/api/files/*` (6)
| 路径 | 方法 | 功能 |
|---|---|---|
| `/api/files/hash` | GET | 文件哈希（md5/sha1/sha256/sha512） |
| `/api/files/large` | GET | 大文件查找 |
| `/api/files/analyze` | GET | 磁盘占用分析 |
| `/api/files/clean-temp` | POST | 清理临时文件 |
| `/api/files/duplicates` | GET | 重复文件检测 |
| `/api/files/delete` | DELETE | ⭐ 文件/目录删除（系统目录安全保护） |

### 4.7 通用 (3)
| 路径 | 方法 | 功能 |
|---|---|---|
| `/api/terminal/run` | POST | 命令终端（执行任意命令 + 危险命令拦截） |
| `/` | GET | 返回 `index.html` |
| `/api/health` | GET | 健康检查 |

⭐ v2.2 新增 API

## 五、前端页面清单（30 个 page）

> 通过侧边栏导航切换，每个 page 对应 `id="page-{name}"` 的 div。

| 分组 | 页面 (data-page) | 对应 JS 加载函数 |
|---|---|---|
| 系统监控 | dashboard / realtime / cpu / memory / interfaces / env / syspower / **proctree** | loadDashboard / (手动启动) / loadCPU / loadMemory / loadInterfaces / loadEnv / loadSysPower / **loadProcessTree** |
| 网络工具 | network / portscan / **bandwidth** / webcheck / wifi / subnet / connections | (按钮触发) / runPortScan / **runBandwidthTest** / runSslCheck/runHttpCheck / loadWifi / runSubnetCalc / loadConnections |
| 管理工具 | processes / services / tasks / terminal | loadProcesses / loadServices / loadTasks / runTerminal |
| 文件工具 | hash / largefiles / diskanalyze / duplicates / cleantemp | runHash / runLargeFiles / runDiskAnalyze / runDuplicates / runCleanTemp |
| 安全 | security / assessment / eventlog / programs / shares | loadSecurity / runAssessment / loadEventLog / loadPrograms / loadShares |
| 渗透测试 | privesc / persistence / weakcred / antiforen | runPrivesc / runPersistence / runWeakCred / runAntiForen |

⭐ v2.2 新增页面

## 六、前端关键机制

- **导航**：`.nav-item[data-page]` 点击 → `switchPage()` → 切 `.page.active` + 调 `loadPageData()`
- **加载函数注册表**：`loadPageData(page)` 内的 `loaders` 对象，**新增页面必须在此注册**
- **pageTitles**：`pageTitles` 对象，**新增页面必须加映射**（控制 topbar 标题）
- **通用请求**：`fetchAPI(path)` 返回 JSON，失败抛异常；`postAPI(path)` 用于 POST 请求
- **工具函数**：`esc(s)` HTML 转义、`loading(el,msg)` 加载占位、`emptyState(el,msg)` 空态、`gaugeRingSVG()` 仪表盘
- **风险徽章**：`riskBadge(level)` + `RISK_COLOR` 映射（极高/高/中/低/信息/安全/未知）
- **动作可视化**：`taskRunning(el, taskName, desc)` 显示进行中卡片；`setBtnBusy(btn, busy)` 按钮加载状态
- **报告导出**：`exportHTML(title, bodyContent)` 生成独立 HTML 报告并下载
- **SSE 扫描**：`EventSource` 接收 `/api/network/scan-stream` 实时推送

## 七、设计规范

- **主题色**：青绿色 `#2dd4bf` 作为主强调色（CSS 变量 `--accent`）
- **背景**：深色 `#0d1117` / `#161b22` / `#21262d` 三层
- **状态色**：绿 `#22c55e` / 黄 `#eab308` / 红 `#ef4444` / 蓝 `#3b82f6`
- **徽章**：`.badge-green/red/yellow/blue/gray`，半透明背景 + 同色文字
- **圆角**：`--radius:10px`（卡片）/ `--radius-sm:6px`（按钮、徽章）
- **字体**：系统字体 + JetBrains Mono（等宽，用于数字/路径/代码）
- **间距**：卡片间 16px，grid 之间用 gap，强调"呼吸感"

## 八、扩展指引（给下一位 agent）

### 新增一个 API + 页面的标准流程
1. **后端**：在 `server.py` 对应分组下加 `@app.get("/api/xxx/yyy")`，函数返回 dict/JSON
2. **前端导航**：`index.html` 对应 `.nav-section` 加 `<button class="nav-item" data-page="xxx">`
3. **前端容器**：`index.html` 加 `<div class="page" id="page-xxx">...</div>`
4. **JS 注册**：`app.js` 的 `pageTitles` 加映射 + `loadPageData` 的 `loaders` 加加载函数
5. **JS 渲染**：写 `loadXxx()` 或 `runXxx()` 函数，调 `fetchAPI()` + `wrap.innerHTML = ...`
6. **测试**：`python -m py_compile server.py` 检查语法 → 启动 → 浏览器验证 → curl 验证 JSON
7. **更新文档**：同步更新 README.md 和 HANDOVER.md 的 API 清单

### 命令执行注意事项
- 统一用 `run_command(["cmd","arg"])`（subprocess）或 `run_powershell("...")`
- **必须设 timeout**，避免卡死（PowerShell 调用 8~20 秒）
- **编码处理**：`_decode_bytes()` 自动检测系统 ANSI 编码，优先使用 UTF-8
- **正则解析 PowerShell 输出**：用 `re.IGNORECASE | re.DOTALL`，注意中英文系统差异
- **JSON 解析 PowerShell 输出**：用 `ConvertTo-Json`，但单条记录返回对象非数组，需 `[json.loads(out)]` 包裹
- **路径转义**：f-string 内不能含反斜杠，改用字符串拼接

### 安全注意事项
- `run_terminal()` 已实现危险命令拦截（format, shutdown, del /f 等）
- `/api/files/delete` 限制不允许删除系统关键目录
- CORS 配置仅允许本地开发源
- 文件删除操作需 `recursive=true` 确认递归删除

### 已知坑
1. `pip install fastapi` 在清华源可能找不到，用阿里云镜像
2. FastAPI `Query(regex=...)` 已弃用，改用 `Query(pattern=...)`
3. PowerShell `Get-CimInstance` 单条返回对象，需 `if out.startswith('[') else [json.loads(out)]`
4. `net user` 输出末尾有"命令完成成功"会被误判为用户名，需过滤
5. 控制台中文输出可能乱码，但 API 返回的 JSON 数据正常
6. `_SYSTEM_ENCODING` 全局缓存系统编码，首次调用后不会改变

## 九、后续可扩展方向（建议优先级）

1. **认证与多用户**：当前完全无认证，仅本地使用；如部署到服务器需加 BasicAuth/JWT
2. **历史与告警**：监控数据持久化（SQLite），阈值告警（邮件/钉钉）
3. **远程主机支持**：通过 SSH/WMI 扩展到多主机管理
4. **CVE 漏洞库**：基于已装程序版本号匹配 CVE（接 NVD API）
5. **流量抓包**：集成 npcap 做实时流量可视化
6. **报告导出增强**：支持 PDF 格式导出
7. **Docker 化**：打包成单容器（虽然 Windows 命令层不跨平台）
8. **WebSocket 实时推送**：替代当前的轮询，提升实时监控性能
9. **配置持久化**：保存用户设置（端口扫描范围、主机列表等）
10. **端口扫描结果历史**：记录历史扫描结果，支持对比

## 十、版本历史

### v2.2.0 (2026-08-21)
- **新增功能**：
  - 进程树视图（`/api/system/process-tree`）
  - 带宽/延迟测试（`/api/network/bandwidth-test`）
  - 文件删除 API（`/api/files/delete`）
  - 端口服务名映射（PORT_SERVICE_MAP）
- **功能优化**：
  - 端口扫描支持 200 线程并发，扩展至 1024 端口
  - Wi-Fi 信息中文乱码修复（双重编码问题）
  - 磁盘总量正确累加所有分区
- **安全增强**：
  - CORS 配置收紧
  - 线程安全改进（Lock 保护历史数据）
  - 文件删除系统目录保护
- **UI/UX**：
  - 移动端适配（汉堡菜单 + 响应式布局）
  - 动作可视化（进度反馈）
  - 质感提升

### v2.1.0 (2026-08-20)
- 端口扫描 SSE 流式推送
- 动作可视化反馈体系
- 报告导出功能
- 开源准备（LICENSE + .gitignore）

### v2.0.0 (2026-08-19)
- 首个稳定版本
- 完整的系统信息采集
- 网络诊断工具集
- 安全基线检查
- 渗透测试模块（本机自检）
