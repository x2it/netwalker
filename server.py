"""
巡网者 (NetWalker) - 网络与系统运维工具箱
FastAPI 后端：系统信息 / 网络工具 / 进程管理 / 安全 / 渗透自检 / 文件工具

Copyright (c) 2026 知行工作室. 仅供学习研究与合法授权下的本机自检使用。
"""
import os
import sys
import ssl
import socket
import time
import hashlib
import platform
import ipaddress
import subprocess
import re
import json
import threading
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

import psutil
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="NetWalker", version="2.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8765",
        "http://localhost:8765",
        "http://localhost:3000",
    ],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# ======================== 辅助函数 ========================
def _get_windows_encoding() -> str:
    """获取 Windows 系统的 ANSI 代码页（用于解码系统命令输出）"""
    if platform.system() != "Windows":
        return "utf-8"
    try:
        import ctypes
        # GetACP() 返回 ANSI 代码页编号，如 936 (GBK)
        acp = ctypes.windll.kernel32.GetACP()
        # 代码页映射：936->gbk, 950->big5, 等
        # Windows 系统通常使用 .cp936 这样的 Python 编码名
        return f"cp{acp}"
    except Exception:
        return "gbk"


# 缓存系统编码，避免重复调用
_SYSTEM_ENCODING = None


def _fix_double_encoding(text: str) -> str:
    """修复 Windows netsh 命令输出中的双重编码问题。
    
    问题描述：
    Windows netsh (如 wlan show interfaces) 命令中，某些字段（如 SSID）
    存在多层编码问题：原始 UTF-8 字节经过多次错误的编码/解码转换。
    
    修复方法：
    对每行文本进行迭代的"反双重编码"处理（GBK 编码 + UTF-8 解码），
    直到结果稳定或达到最大迭代次数。
    
    判断标准：
    只要解码成功（没有异常），并且结果包含中文字符，就接受修复。
    """
    if not text:
        return text
    
    def _has_chinese(text: str) -> bool:
        """检查是否包含中文字符"""
        return any('\u4e00' <= c <= '\u9fff' or '\u3400' <= c <= '\u4dbf' for c in text)
    
    def _fix_line(line: str) -> str:
        """修复单行文本 - 迭代尝试"""
        if not line:
            return line
        
        original = line
        best_result = line
        
        # 迭代尝试最多 3 次
        current = line
        for _ in range(3):
            try:
                # 尝试双重编码修复
                raw_bytes = current.encode('gbk')
                decoded = raw_bytes.decode('utf-8')
                
                # 如果解码成功且包含中文，就接受修复
                # 但只有当结果与原文不同时才更新
                if _has_chinese(decoded) and decoded != original:
                    best_result = decoded
                
                # 如果没有变化，停止迭代
                if decoded == current:
                    break
                
                current = decoded
            except (UnicodeDecodeError, UnicodeEncodeError):
                # 编码失败，说明已经到达正确状态
                break
        
        return best_result
    
    # 逐行处理
    lines = text.split('\r\n')
    fixed_lines = [_fix_line(line) for line in lines]
    return '\r\n'.join(fixed_lines)


def _decode_bytes(data: bytes) -> str:
    """智能解码：优先使用系统 ANSI 编码解码，回退 UTF-8，最后 latin1。
    解决 Windows 下 net.exe/netsh/powerShell 默认 ANSI 编码输出导致的中文乱码。
    
    核心逻辑：
    1. 在 Windows 上，系统命令（net, netsh, ipconfig 等）通常使用 ANSI 代码页编码
    2. 简体中文系统默认代码页是 CP936 (GBK)
    3. 繁体中文是 CP950 (Big5)
    4. 英文系统可能是 CP437/CP850 等
    """
    global _SYSTEM_ENCODING
    if not data:
        return ""
    
    if _SYSTEM_ENCODING is None:
        _SYSTEM_ENCODING = _get_windows_encoding()
    
    # 编码尝试顺序：
    # 1. 系统 ANSI 编码（最可能正确的）
    # 2. UTF-8（现代应用可能使用）
    # 3. GBK/GB18030（备用，兼容中文 Windows）
    # 4. latin-1（兜底，不丢字节但可能显示错误字符）
    
    encodings_to_try = [_SYSTEM_ENCODING, "utf-8"]
    
    # 如果系统编码不是 GBK，额外尝试 GBK
    if _SYSTEM_ENCODING.lower() not in ("gbk", "cp936", "gb18030"):
        encodings_to_try.append("gbk")
    
    # 如果系统编码不是 Big5，额外尝试 Big5（繁体中文备用）
    if _SYSTEM_ENCODING.lower() not in ("big5", "cp950"):
        encodings_to_try.append("big5")
    
    for enc in encodings_to_try:
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    
    # 最终兜底
    return data.decode("latin-1", errors="replace")


def run_command(cmd: list, timeout: int = 15) -> str:
    """执行系统命令并返回输出。
    1. 在 Windows 上设置子进程控制台代码页为 UTF-8 (65001)
    2. 使用智能解码函数 _decode_bytes 处理输出
    """
    try:
        # Windows 下设置子进程的控制台代码页为 UTF-8
        env = None
        if platform.system() == "Windows":
            env = os.environ.copy()
            # 设置控制台输出代码页为 UTF-8
            env["PYTHONIOENCODING"] = "utf-8"
            # 子进程启动后自动 chcp 65001（通过 cmd /c 包装）
            # 但这不是万能的，有些程序不遵守，所以还是需要 _decode_bytes 兜底
        
        result = subprocess.run(cmd, capture_output=True, timeout=timeout, env=env)
        output = _decode_bytes(result.stdout) + _decode_bytes(result.stderr)
        return output.strip()
    except subprocess.TimeoutExpired:
        return f"命令超时（{timeout}秒）"
    except Exception as e:
        return f"执行出错: {str(e)}"


def run_powershell(cmd: str, timeout: int = 15) -> str:
    """执行 PowerShell 命令。
    1. 命令前注入 UTF-8 输出编码设置
    2. 设置子进程环境变量为 UTF-8
    3. 使用智能解码处理输出
    """
    utf8_preamble = (
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8;"
        "[Console]::InputEncoding = [System.Text.Encoding]::UTF8;"
        "$OutputEncoding = [System.Text.Encoding]::UTF8;"
    )
    full_cmd = f"{utf8_preamble}{cmd}"
    
    try:
        # Windows 下设置环境变量为 UTF-8
        env = None
        if platform.system() == "Windows":
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
        
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", full_cmd],
            capture_output=True, timeout=timeout, env=env,
        )
        return (_decode_bytes(result.stdout) + _decode_bytes(result.stderr)).strip()
    except subprocess.TimeoutExpired:
        return f"命令超时（{timeout}秒）"
    except Exception as e:
        return f"执行出错: {str(e)}"


def bytes_to_gb(b: int) -> float:
    return round(b / (1024 ** 3), 2)


def bytes_to_mb(b: int) -> float:
    return round(b / (1024 ** 2), 2)


# ======================== 系统信息 ========================
@app.get("/api/system/overview")
def system_overview():
    """系统总览：CPU、内存、磁盘(累加所有分区)、开机时间"""
    vm = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent(interval=0.5)
    boot_time = datetime.fromtimestamp(psutil.boot_time())

    # 计算所有分区的总容量和已用容量，而不是只算系统盘
    total_disk = 0
    used_disk = 0
    for p in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(p.mountpoint)
            total_disk += usage.total
            used_disk += usage.used
        except Exception:
            continue
            
    disk_percent = round((used_disk / total_disk) * 100, 1) if total_disk > 0 else 0

    return {
        "os": f"{platform.system()} {platform.release()}",
        "os_version": platform.version(),
        "hostname": socket.gethostname(),
        "arch": platform.machine(),
        "processor": platform.processor() or "N/A",
        "cpu_count_logical": psutil.cpu_count(logical=True),
        "cpu_count_physical": psutil.cpu_count(logical=False),
        "cpu_percent": cpu_percent,
        "memory_total_gb": bytes_to_gb(vm.total),
        "memory_used_gb": bytes_to_gb(vm.used),
        "memory_percent": vm.percent,
        "disk_total_gb": bytes_to_gb(total_disk),
        "disk_used_gb": bytes_to_gb(used_disk),
        "disk_percent": disk_percent,
        "boot_time": boot_time.strftime("%Y-%m-%d %H:%M:%S"),
        "uptime_hours": round((datetime.now() - boot_time).total_seconds() / 3600, 1),
    }


@app.get("/api/system/cpu")
def cpu_detail():
    """CPU 详细信息：每核使用率、频率"""
    per_cpu = psutil.cpu_percent(interval=0.5, percpu=True)
    freq = psutil.cpu_freq()
    return {
        "overall": psutil.cpu_percent(interval=0.3),
        "per_cpu": per_cpu,
        "logical_count": psutil.cpu_count(logical=True),
        "physical_count": psutil.cpu_count(logical=False),
        "freq_current": round(freq.current, 0) if freq else None,
        "freq_max": round(freq.max, 0) if freq else None,
        "freq_min": round(freq.min, 0) if freq else None,
        "load_avg": list(psutil.getloadavg()) if hasattr(psutil, "getloadavg") else None,
    }


@app.get("/api/system/memory")
def memory_detail():
    """内存与交换分区"""
    vm = psutil.virtual_memory()
    sm = psutil.swap_memory()
    return {
        "virtual": {
            "total_gb": bytes_to_gb(vm.total),
            "available_gb": bytes_to_gb(vm.available),
            "used_gb": bytes_to_gb(vm.used),
            "free_gb": bytes_to_gb(vm.free),
            "percent": vm.percent,
        },
        "swap": {
            "total_gb": bytes_to_gb(sm.total),
            "used_gb": bytes_to_gb(sm.used),
            "free_gb": bytes_to_gb(sm.free),
            "percent": sm.percent,
        },
    }


@app.get("/api/system/disks")
def disk_detail():
    """所有磁盘分区信息"""
    partitions = []
    for p in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(p.mountpoint)
            fstype = p.fstype if p.fstype else "—"
            partitions.append({
                "device": p.device,
                "mountpoint": p.mountpoint,
                "fstype": fstype,
                "opts": p.opts,
                "total_gb": bytes_to_gb(usage.total),
                "used_gb": bytes_to_gb(usage.used),
                "free_gb": bytes_to_gb(usage.free),
                "percent": usage.percent,
            })
        except PermissionError:
            continue
        except Exception:
            continue
    return {"partitions": partitions}


@app.get("/api/system/network-interfaces")
def net_interfaces():
    """网卡接口信息"""
    addrs = {}
    io = psutil.net_io_counters(pernic=True)
    for name, snic_list in psutil.net_if_addrs().items():
        info = {"ipv4": [], "ipv6": [], "mac": ""}
        for snic in snic_list:
            if snic.family == socket.AF_INET:
                info["ipv4"].append(snic.address)
            elif snic.family == socket.AF_INET6:
                info["ipv6"].append(snic.address)
            elif snic.family.name == "AF_PACKET" or "-" in str(snic.address):
                if not info["mac"]:
                    info["mac"] = snic.address
        stats = io.get(name)
        if stats:
            info["bytes_sent_mb"] = bytes_to_mb(stats.bytes_sent)
            info["bytes_recv_mb"] = bytes_to_mb(stats.bytes_recv)
            info["packets_sent"] = stats.packets_sent
            info["packets_recv"] = stats.packets_recv
        addrs[name] = info
    return {"interfaces": addrs}


# ======================== 网络工具 ========================
@app.get("/api/network/ping")
def ping(host: str = Query(..., description="目标主机"), count: int = Query(4, ge=1, le=20)):
    """Ping 指定主机"""
    output = run_command(["ping", "-n", str(count), host], timeout=30)
    return {"host": host, "output": output}


@app.get("/api/network/dns")
def dns_lookup(domain: str = Query(..., description="域名"), record_type: str = Query("A")):
    """DNS 解析"""
    rtype = record_type.upper() if record_type else "A"
    output = run_command(["nslookup", "-type=" + rtype, domain], timeout=15)
    return {"domain": domain, "record_type": rtype, "output": output}


@app.get("/api/network/port-check")
def port_check(host: str = Query(...), port: int = Query(..., ge=1, le=65535), timeout: int = Query(3, ge=1, le=10)):
    """检测目标主机端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        is_open = (result == 0)
        return {
            "host": host,
            "port": port,
            "open": is_open,
            "status": "开放" if is_open else "关闭/不可达",
        }
    except Exception as e:
        return {"host": host, "port": port, "open": False, "status": f"错误: {str(e)}"}


@app.get("/api/network/connections")
def net_connections(kind: str = Query("all")):
    """当前网络连接"""
    try:
        conns = psutil.net_connections(kind=kind if kind != "all" else "inet")
        results = []
        for c in conns:
            laddr = f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "—"
            raddr = f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "—"
            results.append({
                "fd": c.fd,
                "family": str(c.family.name) if c.family else "—",
                "type": str(c.type.name) if c.type else "—",
                "laddr": laddr,
                "raddr": raddr,
                "status": c.status or "—",
                "pid": c.pid or "—",
            })
        return {"total": len(results), "connections": results[:200]}
    except psutil.AccessDenied:
        return {"total": 0, "connections": [], "error": "权限不足，请以管理员运行"}


@app.get("/api/network/ipconfig")
def ipconfig():
    """IP 配置信息"""
    output = run_command(["ipconfig", "/all"], timeout=15)
    return {"output": output}


@app.get("/api/network/route")
def route_print():
    """路由表"""
    output = run_command(["route", "print"], timeout=15)
    return {"output": output}


@app.get("/api/network/arp")
def arp_table():
    """ARP 表"""
    output = run_command(["arp", "-a"], timeout=15)
    return {"output": output}


# ======================== 进程管理 ========================
@app.get("/api/processes")
def list_processes(sort_by: str = Query("cpu", pattern="^(cpu|memory|pid|name)$")):
    """进程列表，按 CPU 或内存排序"""
    procs = []
    for p in psutil.process_iter(attrs=["pid", "name", "username", "cpu_percent", "memory_percent", "memory_info", "status", "create_time", "exe"]):
        try:
            info = p.info
            mem_mb = bytes_to_mb(info["memory_info"].rss) if info.get("memory_info") else 0
            procs.append({
                "pid": info["pid"],
                "name": info["name"] or "—",
                "username": info["username"] or "—",
                "cpu_percent": round(info["cpu_percent"] or 0, 1),
                "memory_percent": round(info["memory_percent"] or 0, 1),
                "memory_mb": mem_mb,
                "status": info["status"] or "—",
                "create_time": datetime.fromtimestamp(info["create_time"]).strftime("%H:%M:%S") if info.get("create_time") else "—",
                "exe": info.get("exe") or "—",
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    sort_key = sort_by
    procs.sort(key=lambda x: x.get(sort_key, 0) if isinstance(x.get(sort_key), (int, float)) else 0, reverse=True)
    return {"total": len(procs), "processes": procs[:100]}


@app.post("/api/processes/{pid}/kill")
def kill_process(pid: int):
    """结束进程"""
    try:
        p = psutil.Process(pid)
        name = p.name()
        p.terminate()
        p.wait(timeout=5)
        return {"success": True, "pid": pid, "name": name, "message": f"已终止进程 {name} (PID: {pid})"}
    except psutil.NoSuchProcess:
        return {"success": False, "message": f"进程 {pid} 不存在"}
    except psutil.AccessDenied:
        return {"success": False, "message": "权限不足，请以管理员运行"}
    except psutil.TimeoutExpired:
        try:
            p.kill()
            return {"success": True, "pid": pid, "name": name, "message": f"已强制终止进程 {name}"}
        except Exception:
            return {"success": False, "message": "无法终止进程"}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ======================== 安全 ========================
@app.get("/api/security/firewall")
def firewall_status():
    """Windows 防火墙状态"""
    output = run_command(["netsh", "advfirewall", "show", "allprofiles", "state"], timeout=10)
    profiles = {}
    current = None
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("---"):
            continue
        # 匹配 "Domain Profile Settings:" 或 "域 配置文件 设置:"
        if "Profile Settings:" in line or "配置文件" in line:
            name = line.replace("Profile Settings:", "").replace("配置文件", "").replace("设置", "").strip()
            current = name
            profiles[current] = {}
        elif line.lower().startswith("state") or "状态" in line:
            # "State                                 ON"
            parts = line.split()
            val = parts[-1] if parts else ""
            if not val and "状态" in line:
                val = line.split("状态")[-1].strip()
            if current:
                profiles[current]["status"] = val
    if not profiles:
        profiles = {"raw": output}
    return {"profiles": profiles, "raw": output}


@app.get("/api/security/users")
def local_users():
    """本地用户列表"""
    output = run_command(["net", "user"], timeout=10)
    # 解析用户名
    lines = output.splitlines()
    users = []
    capture = False
    for line in lines:
        if "用户帐户" in line or "User accounts" in line:
            capture = True
            continue
        if "命令成功" in line or "The command completed" in line:
            capture = False
            continue
        if capture:
            # 跳过分隔线
            if line.startswith("---"):
                continue
            parts = line.split()
            users.extend(parts)
    return {"users": users, "count": len(users), "raw": output}


@app.get("/api/security/startup")
def startup_items():
    """启动项"""
    # 从注册表读取启动项
    reg_paths = [
        ("HKCU Run", r"HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"),
        ("HKLM Run", r"HKLM:\Software\Microsoft\Windows\CurrentVersion\Run"),
    ]
    items = []
    for label, path in reg_paths:
        output = run_powershell(f"Get-ItemProperty -Path '{path}' | Select-Object * -ExcludeProperty PS* 2>$null | Format-List", timeout=10)
        if output and "error" not in output.lower() and output.strip():
            for line in output.splitlines():
                line = line.strip()
                if line and ":" in line:
                    name, _, cmd = line.partition(":")
                    items.append({"location": label, "name": name.strip(), "command": cmd.strip()})
    return {"items": items, "count": len(items)}


@app.get("/api/security/logged-on")
def logged_on_users():
    """当前登录用户"""
    output = run_powershell("query user 2>$null", timeout=10)
    if not output or "error" in output.lower():
        output = run_command(["whoami"], timeout=5)
    return {"output": output}


# ======================== 服务管理 ========================
@app.get("/api/services")
def list_services(state: str = Query("all", pattern="^(all|running|stopped)$")):
    """Windows 服务列表"""
    services = []
    try:
        for svc in psutil.win_service_iter():
            try:
                info = svc.as_dict()
                svc_state = info.get("status", "unknown")
                if state == "running" and svc_state != "running":
                    continue
                if state == "stopped" and svc_state != "stopped":
                    continue
                services.append({
                    "name": info.get("name", "—"),
                    "display_name": info.get("display_name", "—"),
                    "status": svc_state,
                    "start_type": info.get("start_type", "—"),
                    "pid": info.get("pid") or "—",
                    "binpath": info.get("binpath", "—"),
                    "username": info.get("username", "—"),
                })
            except Exception:
                continue
        services.sort(key=lambda x: (0 if x["status"] == "running" else 1, x["name"]))
        return {"total": len(services), "services": services}
    except Exception as e:
        return {"total": 0, "services": [], "error": str(e)}


@app.post("/api/services/{name}/start")
def start_service(name: str):
    """启动服务"""
    output = run_command(["sc", "start", name], timeout=15)
    return {"name": name, "action": "start", "output": output}


@app.post("/api/services/{name}/stop")
def stop_service(name: str):
    """停止服务"""
    output = run_command(["sc", "stop", name], timeout=15)
    return {"name": name, "action": "stop", "output": output}


# ======================== 实时历史采样 ========================
HISTORY_MAX = 60  # 保留最近 60 个采样点
_cpu_history = []
_mem_history = []
_history_lock = threading.Lock()

# 常见端口服务名映射
PORT_SERVICE_MAP = {
    20: "FTP-DATA", 21: "FTP", 22: "SSH", 23: "Telnet",
    25: "SMTP", 53: "DNS", 67: "DHCP", 80: "HTTP",
    88: "Kerberos", 110: "POP3", 135: "RPC", 137: "NetBIOS-Name",
    138: "NetBIOS-DGM", 139: "NetBIOS-SSN", 143: "IMAP",
    161: "SNMP", 389: "LDAP", 443: "HTTPS", 445: "SMB",
    465: "SMTPS", 514: "Syslog", 587: "SMTP-Submission",
    636: "MS-RPC", 993: "IMAPS", 995: "POP3S", 1433: "MSSQL",
    1521: "Oracle DB", 1723: "PPTP", 2049: "NFS", 3306: "MySQL",
    3389: "RDP", 5432: "PostgreSQL", 5900: "VNC", 6379: "Redis",
    8080: "HTTP-Alt", 8443: "HTTPS-Alt", 9200: "Elasticsearch",
    11211: "Memcached", 27017: "MongoDB", 50070: "P2P",
}


def push_history():
    global _cpu_history, _mem_history
    with _history_lock:
        _cpu_history.append(psutil.cpu_percent(interval=0.3))
        if len(_cpu_history) > HISTORY_MAX:
            _cpu_history.pop(0)
        _mem_history.append(psutil.virtual_memory().percent)
        if len(_mem_history) > HISTORY_MAX:
            _mem_history.pop(0)


@app.get("/api/system/history")
def system_history():
    """CPU/内存历史采样"""
    push_history()
    return {
        "cpu": list(_cpu_history),
        "memory": list(_mem_history),
        "labels": list(range(len(_cpu_history))),
    }


# ======================== 网络进阶工具 ========================
@app.get("/api/network/tracert")
def tracert(host: str = Query(...), max_hops: int = Query(15, ge=1, le=30)):
    """路由追踪"""
    output = run_command(["tracert", "-d", "-h", str(max_hops), host], timeout=60)
    return {"host": host, "output": output}


@app.get("/api/network/whois")
def whois_lookup(domain: str = Query(...)):
    """Whois 查询（通过 nslookup 简化实现）"""
    output = run_command(["nslookup", "-type=ANY", domain], timeout=15)
    return {"domain": domain, "output": output}


def _check_port(host, port, timeout=0.6):
    """检测单个 TCP 端口是否开放（供线程池调用）"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return port if result == 0 else None
    except Exception:
        return None


@app.get("/api/network/scan")
def port_scan(host: str = Query(...), start_port: int = Query(..., ge=1, le=65535),
              end_port: int = Query(..., ge=1, le=65535)):
    """端口扫描：扫描指定端口范围（200 线程并发，单次最多 1024 端口）"""
    if end_port < start_port:
        end_port = start_port
    if end_port - start_port > 1024:
        end_port = start_port + 1024
    open_ports = []
    with ThreadPoolExecutor(max_workers=200) as ex:
        futures = {ex.submit(_check_port, host, p): p for p in range(start_port, end_port + 1)}
        for f in as_completed(futures):
            r = f.result()
            if r is not None:
                open_ports.append(r)
    open_ports.sort()
    # 添加服务名映射
    port_info = [
        {"port": p, "service": PORT_SERVICE_MAP.get(p, "Unknown")}
        for p in open_ports
    ]
    return {
        "host": host, "range": f"{start_port}-{end_port}",
        "open_ports": open_ports, "port_info": port_info, "count": len(open_ports)
    }


def _sse(event, data):
    """格式化一条 SSE 消息"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/api/network/scan-stream")
def port_scan_stream(host: str = Query(...), start_port: int = Query(..., ge=1, le=65535),
                     end_port: int = Query(..., ge=1, le=65535)):
    """端口扫描（SSE 流式）：实时推送扫描进度与已发现的开放端口（含服务名）"""
    if end_port < start_port:
        end_port = start_port
    if end_port - start_port > 1024:
        end_port = start_port + 1024
    total = end_port - start_port + 1

    def event_stream():
        open_ports = []
        scanned = 0
        yield _sse("start", {"host": host, "range": f"{start_port}-{end_port}", "total": total})
        with ThreadPoolExecutor(max_workers=200) as ex:
            futures = {ex.submit(_check_port, host, p): p for p in range(start_port, end_port + 1)}
            for f in as_completed(futures):
                scanned += 1
                r = f.result()
                if r is not None:
                    open_ports.append(r)
                    yield _sse("found", {
                        "port": r,
                        "service": PORT_SERVICE_MAP.get(r, "Unknown"),
                        "scanned": scanned, "total": total,
                        "open": sorted(open_ports),
                        "percent": round(scanned * 100 / total)
                    })
                elif scanned % 10 == 0 or scanned == total:
                    yield _sse("progress", {
                        "scanned": scanned, "total": total,
                        "open": sorted(open_ports),
                        "percent": round(scanned * 100 / total)
                    })
        open_ports.sort()
        port_info = [
            {"port": p, "service": PORT_SERVICE_MAP.get(p, "Unknown")}
            for p in open_ports
        ]
        yield _sse("done", {
            "host": host, "range": f"{start_port}-{end_port}",
            "open_ports": open_ports, "port_info": port_info,
            "count": len(open_ports)
        })

    return StreamingResponse(event_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/network/ssl-cert")
def ssl_cert(host: str = Query(...), port: int = Query(443, ge=1, le=65535)):
    """SSL 证书信息"""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((host, port), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert(binary_form=True)
                if cert:
                    import ssl as _ssl
                    from cryptography import x509
                    from cryptography.hazmat.backends import default_backend
                    cert_obj = x509.load_der_x509_certificate(cert, default_backend())
                    return {
                        "host": host,
                        "port": port,
                        "subject": cert_obj.subject.rfc4514_string(),
                        "issuer": cert_obj.issuer.rfc4514_string(),
                        "not_before": cert_obj.not_valid_before.isoformat(),
                        "not_after": cert_obj.not_valid_after.isoformat(),
                        "serial": str(cert_obj.serial_number),
                        "version": cert_obj.version.name,
                    }
        return {"host": host, "port": port, "error": "未获取到证书"}
    except ImportError:
        # 无 cryptography 库，用 ssl 内置解析
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with socket.create_connection((host, port), timeout=8) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                    cert_dict = ssock.getpeercert()
                    return {
                        "host": host, "port": port,
                        "subject": str(cert_dict.get("subject", "")) if cert_dict else "",
                        "issuer": str(cert_dict.get("issuer", "")) if cert_dict else "",
                        "not_before": cert_dict.get("notBefore", "") if cert_dict else "",
                        "not_after": cert_dict.get("notAfter", "") if cert_dict else "",
                    }
        except Exception as e:
            return {"host": host, "port": port, "error": str(e)}
    except Exception as e:
        return {"host": host, "port": port, "error": str(e)}


@app.get("/api/network/http-headers")
def http_headers(url: str = Query(...)):
    """HTTP 响应头检测"""
    if not url.startswith("http"):
        url = "http://" + url
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SysOpsToolkit/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            headers = dict(resp.headers.items())
            return {
                "url": url,
                "status": resp.status,
                "reason": resp.reason,
                "headers": headers,
                "final_url": resp.url,
            }
    except urllib.error.HTTPError as e:
        return {"url": url, "status": e.code, "reason": e.reason, "headers": dict(e.headers.items())}
    except Exception as e:
        return {"url": url, "error": str(e)}


@app.get("/api/network/wifi")
def wifi_info():
    """Wi-Fi 接口信息 - 修复双重编码问题"""
    # 使用 run_command 获取原始输出
    interfaces_raw = run_command(["netsh", "wlan", "show", "interfaces"], timeout=10)
    profiles_raw = run_command(["netsh", "wlan", "show", "profiles"], timeout=10)
    
    # 修复双重编码问题
    interfaces_fixed = _fix_double_encoding(interfaces_raw)
    profiles_fixed = _fix_double_encoding(profiles_raw)
    
    return {
        "interfaces": interfaces_fixed,
        "profiles": profiles_fixed,
        "encoding_warning": None
    }


@app.get("/api/network/subnet")
def subnet_calc(ip: str = Query(...), prefix: int = Query(..., ge=0, le=128)):
    """子网计算器"""
    try:
        net = ipaddress.ip_network(f"{ip}/{prefix}", strict=False)
        version = net.version
        result = {
            "input": f"{ip}/{prefix}",
            "version": f"IPv{version}",
            "network": str(net.network_address),
            "broadcast": str(net.broadcast_address),
            "netmask": str(net.netmask),
            "prefix": net.prefixlen,
            "hostmask": str(net.hostmask),
            "num_addresses": net.num_addresses,
            "num_hosts": net.num_addresses - 2 if version == 4 and net.prefixlen < 31 else net.num_addresses,
        }
        if net.num_addresses <= 256:
            result["hosts"] = [str(h) for h in net.hosts()] if version == 4 else [str(h) for h in net][:256]
        return result
    except Exception as e:
        return {"input": f"{ip}/{prefix}", "error": str(e)}


# ======================== 安全深挖 ========================
@app.get("/api/security/defender")
def defender_status():
    """Windows Defender 状态"""
    output = run_powershell(
        "Get-MpComputerStatus | Select-Object ProductName,ProductVersion,AntivirusEnabled,"
        "RealTimeProtectionEnabled,AntivirusSignatureLastUpdated,"
        "AntivirusSignatureVersion,AntispywareSignatureVersion,QuickScanEndTime,FullScanEndTime | Format-List",
        timeout=15
    )
    return {"output": output}


@app.get("/api/security/programs")
def installed_programs():
    """已安装程序"""
    # 从注册表读取（更可靠）
    cmd = ("Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*,"
           "HKLM:\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*,"
           "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* 2>$null | "
           "Where-Object { $_.DisplayName } | "
           "Select-Object DisplayName,Publisher,DisplayVersion,InstallDate | "
           "Sort-Object DisplayName | Format-Table -AutoSize")
    output = run_powershell(cmd, timeout=20)
    # 解析表格
    lines = output.splitlines()
    programs = []
    if len(lines) > 2:
        for line in lines[2:]:
            if line.strip():
                # 简单按空格分割（不完美但可用）
                programs.append(line.strip())
    return {"count": len(programs), "programs": programs, "raw": output}


@app.get("/api/security/tasks")
def scheduled_tasks():
    """计划任务"""
    output = run_command(["schtasks", "/query", "/fo", "LIST"], timeout=20)
    # 解析任务
    tasks = []
    current = {}
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if key == "TaskName":
                if current:
                    tasks.append(current)
                current = {"name": val}
            elif current:
                current[key.lower()] = val
    if current:
        tasks.append(current)
    return {"count": len(tasks), "tasks": tasks[:200], "raw_preview": output[:500]}


@app.get("/api/security/shares")
def shared_folders():
    """共享文件夹"""
    output = run_command(["net", "share"], timeout=10)
    return {"output": output}


@app.get("/api/security/eventlog")
def event_log(log: str = Query("System", pattern="^(System|Application|Security)"), count: int = Query(20, ge=1, le=200)):
    """事件日志查看"""
    cmd = (f"Get-WinEvent -LogName '{log}' -MaxEvents {count} | "
           "Select-Object TimeCreated,Id,LevelDisplayName,ProviderName,Message | "
           "Format-List")
    output = run_powershell(cmd, timeout=20)
    return {"log": log, "count": count, "output": output}


@app.get("/api/security/password-policy")
def password_policy():
    """密码策略"""
    output = run_command(["net", "accounts"], timeout=10)
    return {"output": output}


@app.get("/api/security/hotfixes")
def installed_hotfixes():
    """已安装补丁"""
    output = run_powershell(
        "Get-HotFix | Select-Object HotFixID,Description,InstalledOn | Sort-Object InstalledOn -Descending | Format-Table -AutoSize",
        timeout=15
    )
    return {"output": output}


# ======================== 安全评估 ========================
@app.get("/api/security/baseline")
def security_baseline():
    """安全基线检查：综合评分 + 逐项检查"""
    checks = []

    # 1. 防火墙
    try:
        fw_out = run_command(["netsh", "advfirewall", "show", "allprofiles", "state"], timeout=10)
        fw_on = fw_out.upper().count("ON") >= 3
        all_off = fw_out.upper().count("OFF") >= 3
        checks.append({
            "category": "防火墙", "name": "所有配置文件防火墙已启用",
            "pass": fw_on and not all_off,
            "detail": "Domain/Private/Private 防火墙状态" + ("：全部启用" if fw_on else "：存在关闭项"),
            "severity": "high" if not fw_on else "info",
        })
    except Exception as e:
        checks.append({"category": "防火墙", "name": "防火墙状态", "pass": None, "detail": f"检测失败: {e}", "severity": "warn"})

    # 2. Defender 实时保护
    try:
        def_out = run_powershell(
            "(Get-MpComputerStatus).RealTimeProtectionEnabled", timeout=15
        ).strip().lower()
        rt_on = "true" in def_out
        checks.append({
            "category": "防病毒", "name": "Defender 实时保护已启用",
            "pass": rt_on, "detail": "Windows Defender 实时保护" + ("：已启用" if rt_on else "：未启用（高风险）"),
            "severity": "high" if not rt_on else "info",
        })
    except Exception:
        checks.append({"category": "防病毒", "name": "Defender 状态", "pass": None, "detail": "无法检测（可能非 Defender 环境）", "severity": "warn"})

    # 3. 来宾账户
    try:
        guest_out = run_command(["net", "user", "Guest"], timeout=10)
        guest_active = "Yes" in guest_out or "是" in guest_out.split("Account active")[-1][:30] if "Account active" in guest_out else False
        checks.append({
            "category": "账户安全", "name": "Guest 账户已禁用",
            "pass": not guest_active, "detail": "Guest 账户" + ("：已禁用" if not guest_active else "：已启用（高风险）"),
            "severity": "high" if guest_active else "info",
        })
    except Exception:
        checks.append({"category": "账户安全", "name": "Guest 账户", "pass": None, "detail": "检测失败", "severity": "warn"})

    # 4. 密码策略
    try:
        acct_out = run_command(["net", "accounts"], timeout=10)
        min_match = re.search(r"Minimum password length.*?(\d+)", acct_out, re.IGNORECASE | re.DOTALL)
        min_len = int(min_match.group(1)) if min_match else 0
        max_match = re.search(r"Maximum password age.*?(\d+)", acct_out, re.IGNORECASE | re.DOTALL)
        max_age = int(max_match.group(1)) if max_match else 0
        checks.append({
            "category": "密码策略", "name": "最小密码长度 ≥ 8 位",
            "pass": min_len >= 8, "detail": f"当前最小密码长度：{min_len} 位" + ("（合格）" if min_len >= 8 else "（建议≥8）"),
            "severity": "medium" if min_len < 8 else "info",
        })
        checks.append({
            "category": "密码策略", "name": "密码最长有效期 ≤ 90 天",
            "pass": 0 < max_age <= 90, "detail": f"当前密码有效期：{max_age} 天" + ("（合格）" if 0 < max_age <= 90 else "（建议定期更换）"),
            "severity": "low" if not (0 < max_age <= 90) else "info",
        })
    except Exception:
        checks.append({"category": "密码策略", "name": "密码策略", "pass": None, "detail": "检测失败", "severity": "warn"})

    # 5. 账户锁定策略
    try:
        acct_out = run_command(["net", "accounts"], timeout=10)
        lock_match = re.search(r"(Lockout threshold|锁定阈值).*?(\d+)", acct_out, re.IGNORECASE | re.DOTALL)
        lock_thresh = int(lock_match.group(2)) if lock_match else 0
        checks.append({
            "category": "暴力破解防护", "name": "账户锁定阈值已设置（≤5次）",
            "pass": 0 < lock_thresh <= 5, "detail": f"锁定阈值：{lock_thresh} 次" + ("（已启用防爆破）" if 0 < lock_thresh <= 5 else "（未启用，存在暴力破解风险）"),
            "severity": "high" if lock_thresh == 0 else "info",
        })
    except Exception:
        checks.append({"category": "暴力破解防护", "name": "账户锁定", "pass": None, "detail": "检测失败", "severity": "warn"})

    # 6. 管理共享
    try:
        share_out = run_command(["net", "share"], timeout=10)
        admin_shares = [l for l in share_out.splitlines() if l.strip().endswith("$") and ("C" in l or "ADMIN" in l)]
        checks.append({
            "category": "共享安全", "name": "默认管理共享 (C$/Admin$)",
            "pass": len(admin_shares) == 0, "detail": ("未发现管理共享" if not admin_shares else f"存在 {len(admin_shares)} 个管理共享（C$/Admin$，可关闭）"),
            "severity": "medium" if admin_shares else "info",
        })
    except Exception:
        checks.append({"category": "共享安全", "name": "管理共享", "pass": None, "detail": "检测失败", "severity": "warn"})

    # 7. 自动登录
    try:
        al_out = run_powershell(
            "Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon' -Name AutoAdminLogon -ErrorAction SilentlyContinue | Select-Object -ExpandProperty AutoAdminLogon",
            timeout=10
        ).strip().lower()
        auto_login = "1" in al_out or "yes" in al_out
        checks.append({
            "category": "登录安全", "name": "自动登录已禁用",
            "pass": not auto_login, "detail": "自动登录" + ("：已禁用" if not auto_login else "：已启用（凭据明文存储于注册表）"),
            "severity": "medium" if auto_login else "info",
        })
    except Exception:
        checks.append({"category": "登录安全", "name": "自动登录", "pass": None, "detail": "检测失败", "severity": "warn"})

    # 8. RDP 暴露检查
    try:
        rdp_out = run_powershell(
            "(Get-ItemProperty 'HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server' -Name fDenyTSConnections).fDenyTSConnections",
            timeout=10
        ).strip()
        rdp_disabled = "1" in rdp_out
        checks.append({
            "category": "远程访问", "name": "RDP 已禁用",
            "pass": rdp_disabled, "detail": "远程桌面" + ("：已禁用" if rdp_disabled else "：已启用（建议配合网络层限制）"),
            "severity": "medium" if not rdp_disabled else "info",
        })
    except Exception:
        checks.append({"category": "远程访问", "name": "RDP 状态", "pass": None, "detail": "检测失败", "severity": "warn"})

    # 9. UAC 用户账户控制
    try:
        uac_out = run_powershell(
            "(Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System' -Name EnableLUA).EnableLUA",
            timeout=10
        ).strip()
        uac_on = "1" in uac_out
        checks.append({
            "category": "系统加固", "name": "UAC 用户账户控制已启用",
            "pass": uac_on, "detail": "UAC" + ("：已启用" if uac_on else "：已禁用（高风险）"),
            "severity": "high" if not uac_on else "info",
        })
    except Exception:
        checks.append({"category": "系统加固", "name": "UAC", "pass": None, "detail": "检测失败", "severity": "warn"})

    # 计算评分
    total = len(checks)
    passed = sum(1 for c in checks if c["pass"] is True)
    failed = sum(1 for c in checks if c["pass"] is False)
    unknown = sum(1 for c in checks if c["pass"] is None)
    # 有效项计分（排除未知）
    effective = total - unknown
    score = round((passed / effective) * 100) if effective > 0 else 0

    # 风险等级
    high_issues = sum(1 for c in checks if c.get("severity") == "high" and c["pass"] is False)
    if high_issues >= 2 or score < 50:
        risk_level = "高危"
    elif score < 75:
        risk_level = "中危"
    elif score < 90:
        risk_level = "低危"
    else:
        risk_level = "安全"

    # 兼容字段：前端 renderAssessment() 期望 id / title / passed
    # 后端内部保持 category / name / pass / detail / severity 不变，这里做一次映射。
    compatible_checks = []
    for i, c in enumerate(checks):
        p = c.get("pass")
        compatible_checks.append({
            **c,
            "id": c.get("id") or (c.get("category") or "X") + f"#{i:02d}",
            "title": c.get("title") or c.get("name") or c.get("category") or f"检查项{i}",
            "passed": c.get("passed") if "passed" in c else p,
            "detail": c.get("detail") or "",
            "severity": c.get("severity") or "info",
            "category": c.get("category") or "其他",
            "name": c.get("name") or c.get("title") or c.get("id") or "",
            "pass": p,
        })

    return {
        "score": score,
        "risk_level": risk_level,
        "total": total,
        "passed": passed,
        "failed": failed,
        "unknown": unknown,
        "high_issues": high_issues,
        "checks": compatible_checks,
    }


@app.get("/api/security/attack-surface")
def attack_surface():
    """攻击面分析：监听端口 + 外部连接 + 暴露服务 + 风险评估"""
    # 监听端口
    listening = []
    external_conns = []
    try:
        conns = psutil.net_connections(kind="inet")
        for c in conns:
            if c.status == psutil.CONN_LISTEN and c.laddr:
                port = c.laddr.port
                addr = c.laddr.ip
                # 0.0.0.0 / :: 表示对外暴露
                exposed = addr in ("0.0.0.0", "::", ":::")
                listening.append({
                    "port": port,
                    "address": addr,
                    "exposed": exposed,
                    "pid": c.pid,
                    "process": _proc_name(c.pid),
                })
            elif c.status == "ESTABLISHED" and c.raddr:
                rip = c.raddr.ip
                # 排除本地回环和内网
                if not (rip.startswith("127.") or rip == "::1" or rip.startswith("192.168.") or rip.startswith("10.") or rip.startswith("172.")):
                    external_conns.append({
                        "local": f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "—",
                        "remote": f"{c.raddr.ip}:{c.raddr.port}",
                        "pid": c.pid,
                        "process": _proc_name(c.pid),
                    })
    except psutil.AccessDenied:
        pass

    # 高风险端口映射
    risky_ports = {
        21: "FTP（明文传输）", 22: "SSH", 23: "Telnet（明文，极高风险）",
        25: "SMTP", 53: "DNS", 135: "RPC（需限制）", 137: "NetBIOS",
        138: "NetBIOS", 139: "SMB（历史漏洞）", 445: "SMB（勒索病毒常用）",
        1433: "SQL Server", 1521: "Oracle", 3306: "MySQL",
        3389: "RDP（暴力破解目标）", 5432: "PostgreSQL", 5900: "VNC",
        6379: "Redis（未授权常见）", 27017: "MongoDB（未授权常见）",
        8080: "HTTP-Alt", 8443: "HTTPS-Alt",
    }
    risky_services = []
    for item in listening:
        if item["port"] in risky_ports:
            risky_services.append({
                "port": item["port"],
                "service": risky_ports[item["port"]],
                "exposed": item["exposed"],
                "process": item["process"],
                "risk": "极高" if item["exposed"] and item["port"] in (23, 445, 3389, 6379, 27017) else "高" if item["exposed"] else "中",
            })

    # 暴露端口数（对外监听）
    exposed_count = sum(1 for l in listening if l["exposed"])
    # 风险评估
    high_risk = sum(1 for r in risky_services if r["risk"] == "极高")
    if high_risk > 0 or exposed_count > 10:
        exposure_level = "高危"
    elif exposed_count > 5 or len(risky_services) > 2:
        exposure_level = "中危"
    elif exposed_count > 0:
        exposure_level = "低危"
    else:
        exposure_level = "最小暴露"

    return {
        "listening_total": len(listening),
        "exposed_count": exposed_count,
        "listening": listening,
        "external_connections": external_conns,
        "external_count": len(external_conns),
        "risky_services": risky_services,
        "exposure_level": exposure_level,
    }


def _proc_name(pid):
    """安全获取进程名"""
    if not pid:
        return "—"
    try:
        return psutil.Process(pid).name()
    except Exception:
        return "—"


# ======================== 渗透测试（本地自检） ========================
@app.get("/api/pentest/privesc")
def pentest_privesc():
    """提权路径扫描：可写系统目录、未签名服务、AlwaysInstallElevated、令牌特权、可利用程序"""
    findings = []

    # 1. AlwaysInstallElevated（MSI 提权）
    try:
        out = run_powershell(
            "(Get-ItemProperty 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\Installer' -Name AlwaysInstallElevated -ErrorAction SilentlyContinue).AlwaysInstallElevated",
            timeout=8
        ).strip()
        if "1" in out:
            findings.append({
                "category": "MSI 提权", "name": "AlwaysInstallElevated 已启用",
                "severity": "极高", "exploitable": True,
                "detail": "任意用户可高权限运行 MSI 包，可用 msiexec 提权",
                "remediation": "禁用 HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\Installer\\AlwaysInstallElevated",
            })
        else:
            findings.append({"category": "MSI 提权", "name": "AlwaysInstallElevated", "severity": "信息", "exploitable": False, "detail": "未启用（安全）", "remediation": "—"})
    except Exception:
        findings.append({"category": "MSI 提权", "name": "AlwaysInstallElevated", "severity": "未知", "exploitable": None, "detail": "检测失败", "remediation": "—"})

    # 2. 可写系统目录（PATH 劫持点）
    writable_paths = []
    for p in [r"C:\Windows\System32", r"C:\Windows", r"C:\Windows\System32\wbem"]:
        try:
            test_file = os.path.join(p, ".sysops_write_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            writable_paths.append(p)
        except Exception:
            pass
    if writable_paths:
        findings.append({
            "category": "PATH 劫持", "name": "系统目录可写",
            "severity": "高", "exploitable": True,
            "detail": "以下目录当前用户可写：" + ", ".join(writable_paths),
            "remediation": "限制系统目录 ACL，普通用户不应可写",
        })
    else:
        findings.append({"category": "PATH 劫持", "name": "系统目录权限", "severity": "信息", "exploitable": False, "detail": "系统目录不可写（安全）", "remediation": "—"})

    # 3. 未签名/无数字签名的服务可执行文件
    unsigned_services = []
    try:
        svc_out = run_powershell(
            "Get-CimInstance Win32_Service -Filter \"State='Running'\" | Select-Object Name,PathName | ConvertTo-Json",
            timeout=20
        )
        # 解析服务路径
        try:
            svc_list = json.loads(svc_out) if svc_out.strip().startswith("[") else [json.loads(svc_out)]
        except Exception:
            svc_list = []
        # 用 powershell 校验签名
        for svc in svc_list[:40]:
            path = (svc.get("PathName") or "").split(" /")[0].strip('"').strip("'")
            if not path or not os.path.exists(path):
                continue
            try:
                sig = run_powershell(
                    f"(Get-AuthenticodeSignature '{path}').Status", timeout=5
                ).strip()
                if sig and "Valid" not in sig and "valid" not in sig:
                    unsigned_services.append({"name": svc.get("Name"), "path": path, "signature": sig})
            except Exception:
                pass
        if unsigned_services:
            findings.append({
                "category": "未签名服务", "name": f"发现 {len(unsigned_services)} 个未签名服务",
                "severity": "中", "exploitable": True,
                "detail": "未签名可执行可被替换执行恶意代码",
                "remediation": "审计服务可执行文件签名，可疑路径加白名单",
            })
        else:
            findings.append({"category": "未签名服务", "name": "服务签名", "severity": "信息", "exploitable": False, "detail": "已扫描服务均签名", "remediation": "—"})
    except Exception:
        findings.append({"category": "未签名服务", "name": "服务签名检测", "severity": "未知", "exploitable": None, "detail": "检测失败", "remediation": "—"})

    # 4. 当前进程令牌特权
    try:
        whoami_priv = run_command(["whoami", "/priv"], timeout=8)
        privs = [l.strip() for l in whoami_priv.splitlines() if "Enabled" in l or "启用" in l]
        has_debug = any("Debug" in p or "调试" in p for p in privs)
        has_impersonate = any("Impersonate" in p or "模拟" in p for p in privs)
        risky_privs = []
        if has_debug: risky_privs.append("SeDebugPrivilege（可调试任意进程）")
        if has_impersonate: risky_privs.append("SeImpersonatePrivilege（可模拟令牌，JuicyPotato 类利用）")
        if risky_privs:
            findings.append({
                "category": "令牌特权", "name": "持有高敏感特权",
                "severity": "高", "exploitable": True,
                "detail": "当前令牌包含：" + "; ".join(risky_privs),
                "remediation": "降权运行服务，避免高权限服务暴露令牌",
            })
        else:
            findings.append({"category": "令牌特权", "name": "令牌特权", "severity": "信息", "exploitable": False, "detail": "无敏感提权特权", "remediation": "—"})
    except Exception:
        findings.append({"category": "令牌特权", "name": "令牌特权检测", "severity": "未知", "exploitable": None, "detail": "检测失败", "remediation": "—"})

    # 5. 高危可利用程序（历史漏洞工具）
    common_tools = {
        "java.exe": "Java（历史沙箱逃逸）", "python.exe": "Python（DLL 劫持）",
        "powershell.exe": "PowerShell（无文件攻击）", "mshta.exe": "mshta（脚本攻击常用）",
        "certutil.exe": "certutil（远程下载/编码绕过）", "bitsadmin.exe": "bitsadmin（外联常用）",
        "regsvr32.exe": "regsvr32（squiblydoo 攻击）", "rundll32.exe": "rundll32（无文件常用）",
    }
    found_tools = []
    for exe in common_tools:
        for path_dir in os.environ.get("PATH", "").split(";"):
            candidate = os.path.join(path_dir, exe)
            if os.path.exists(candidate):
                found_tools.append({"tool": exe, "desc": common_tools[exe], "path": candidate})
                break
    if found_tools:
        findings.append({
            "category": "Living off the Land", "name": f"系统自带 {len(found_tools)} 个攻击常用工具",
            "severity": "信息", "exploitable": False,
            "detail": "这些工具常被 APT/红队用于无文件攻击（LOLBins）",
            "remediation": "通过 AppLocker/WDAC 限制执行",
        })

    exploitable_count = sum(1 for f in findings if f.get("exploitable") is True)
    risk_level = "高危" if any(f["severity"] == "极高" for f in findings) else (
        "中危" if any(f["severity"] == "高" for f in findings) else (
            "低危" if any(f["severity"] == "中" for f in findings) else "安全"
        )
    )
    return {
        "total_findings": len(findings),
        "exploitable": exploitable_count,
        "risk_level": risk_level,
        "findings": findings,
        "unsigned_services": unsigned_services,
        "found_tools": found_tools,
    }


@app.get("/api/pentest/persistence")
def pentest_persistence():
    """持久化机制扫描：启动项、计划任务、服务、WMI、注册表劫持、Active Setup"""
    locations = []

    # 1. Run 启动项
    try:
        run_keys = [
            r"HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
            r"HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce",
            r"HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
            r"HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce",
        ]
        for key in run_keys:
            out = run_powershell(f"Get-ItemProperty '{key}' | Format-List *", timeout=8)
            entries = [l.strip() for l in out.splitlines() if ":" in l and not l.startswith("PS") and "PSPath" not in l]
            for entry in entries:
                parts = entry.split(":", 1)
                if len(parts) == 2 and parts[1].strip() and parts[0].strip() not in ("PSComputerName", "PSParentPath"):
                    locations.append({"type": "注册表 Run", "key": key, "item": parts[0].strip(), "value": parts[1].strip()})
    except Exception:
        pass

    # 2. 启动文件夹
    for start_dir in [r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup", r"%ProgramData%\Microsoft\Windows\Start Menu\Programs\Startup"]:
        real = os.path.expandvars(start_dir)
        if os.path.exists(real):
            for f in os.listdir(real):
                locations.append({"type": "启动文件夹", "key": real, "item": f, "value": os.path.join(real, f)})

    # 3. 计划任务（可疑）
    try:
        tasks_out = run_powershell(
            "Get-ScheduledTask | Where-Object {$_.State -ne 'Disabled'} | Select-Object TaskName,Author,@{N='Path';E={$_.Actions.Execute}} | ConvertTo-Json -Depth 2",
            timeout=20
        )
        try:
            tlist = json.loads(tasks_out) if tasks_out.strip().startswith("[") else ([json.loads(tasks_out)] if tasks_out.strip().startswith("{") else [])
        except Exception:
            tlist = []
        for t in tlist[:30]:
            name = t.get("TaskName", "")
            path = t.get("Path", "") or (t.get("Actions", {}).get("Execute") if isinstance(t.get("Actions"), dict) else "")
            if not path:
                continue
            locations.append({"type": "计划任务", "key": f"Task: {name}", "item": name, "value": path})
    except Exception:
        pass

    # 4. 服务（异常）
    try:
        svc_out = run_powershell(
            "Get-CimInstance Win32_Service | Where-Object {$_.PathName -and ($_.PathName -like '*temp*' -or $_.PathName -like '*Users*' -or $_.PathName -like '*.dll*')} | Select-Object Name,PathName,StartMode | ConvertTo-Json -Depth 2",
            timeout=20
        )
        try:
            slist = json.loads(svc_out) if svc_out.strip().startswith("[") else ([json.loads(svc_out)] if svc_out.strip().startswith("{") else [])
        except Exception:
            slist = []
        for s in slist:
            locations.append({"type": "可疑服务", "key": f"Service: {s.get('Name')}", "item": s.get("Name"), "value": s.get("PathName", "")})
    except Exception:
        pass

    # 5. WMI 事件订阅（典型持久化）
    try:
        wmi_out = run_powershell(
            "Get-CimInstance -Namespace root/Subscription -ClassName __EventConsumer | Select-Object Name,ScriptText | ConvertTo-Json -Depth 2",
            timeout=12
        )
        try:
            wlist = json.loads(wmi_out) if wmi_out.strip().startswith("[") else ([json.loads(wmi_out)] if wmi_out.strip().startswith("{") else [])
        except Exception:
            wlist = []
        for w in wlist:
            locations.append({"type": "WMI 事件订阅", "key": "WMI EventConsumer", "item": w.get("Name", ""), "value": (w.get("ScriptText") or "")[:200]})
    except Exception:
        pass

    # 6. Image File Execution Options（调试器劫持）
    try:
        ifeo_out = run_powershell(
            "Get-ChildItem 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Image File Execution Options' | ForEach-Object { $n=$_.PSChildName; $d=(Get-ItemProperty $_.PSPath -Name Debugger -ErrorAction SilentlyContinue).Debugger; if($d){ \"$n|$d\" } }",
            timeout=12
        )
        for line in ifeo_out.splitlines():
            if "|" in line:
                name, deb = line.split("|", 1)
                locations.append({"type": "IFEO 调试器劫持", "key": "Image File Execution Options", "item": name, "value": deb})
    except Exception:
        pass

    return {
        "total": len(locations),
        "items": locations,
        "risk_level": "高危" if any(l["type"] == "WMI 事件订阅" for l in locations) else (
            "中危" if len(locations) > 20 else "低危"
        ),
    }


@app.get("/api/pentest/weak-credentials")
def pentest_weak_credentials():
    """弱口令审计：空密码账户、密码策略、LMHash、Guest/Administrator 状态"""
    findings = []

    # 1. 本地用户与状态
    try:
        users_out = run_command(["net", "user"], timeout=10)
        user_names = []
        in_users = False
        for line in users_out.splitlines():
            if "----" in line:
                in_users = not in_users
                continue
            if in_users and line.strip() and "The command" not in line:
                user_names.extend(line.split())
        # 排除最后两个（命令完成）
        user_names = [u for u in user_names if u not in ("command", "completed", "successfully.")]

        for u in user_names[:20]:
            try:
                detail = run_command(["net", "user", u], timeout=8)
                active_line = [l for l in detail.splitlines() if "Account active" in l or "账户活动" in l]
                is_active = any("Yes" in l or "是" in l for l in active_line)
                # 检查密码是否到期/从未设置
                pw_line = [l for l in detail.splitlines() if "Password last set" in l or "Password required" in l]
                if pw_line and any("Never" in l and "Password required" in l for l in pw_line):
                    findings.append({"user": u, "issue": "密码可为空", "severity": "高", "detail": "Password required = No"})
                if is_active and u.lower() == "guest":
                    findings.append({"user": u, "issue": "Guest 账户已启用", "severity": "极高", "detail": "Guest 是低权限但常作跳板"})
            except Exception:
                pass
    except Exception:
        pass

    # 2. 密码策略
    try:
        acct_out = run_command(["net", "accounts"], timeout=10)
        min_match = re.search(r"Minimum password length.*?(\d+)", acct_out, re.IGNORECASE | re.DOTALL)
        min_len = int(min_match.group(1)) if min_match else 0
        if min_len < 8:
            findings.append({"user": "(策略)", "issue": f"最小密码长度仅 {min_len}", "severity": "高" if min_len == 0 else "中", "detail": "建议≥8 位"})
        lock_match = re.search(r"(Lockout threshold|锁定阈值).*?(\d+)", acct_out, re.IGNORECASE | re.DOTALL)
        lock_thresh = int(lock_match.group(2)) if lock_match else 0
        if lock_thresh == 0:
            findings.append({"user": "(策略)", "issue": "账户锁定阈值=0（无限尝试）", "severity": "高", "detail": "存在暴力破解风险"})
    except Exception:
        pass

    # 3. LMHash 启用（旧式哈希）
    try:
        lm_out = run_powershell(
            "(Get-ItemProperty 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Lsa' -Name NoLMHash -ErrorAction SilentlyContinue).NoLMHash",
            timeout=8
        ).strip()
        if "0" in lm_out or not lm_out:
            findings.append({"user": "(哈希)", "issue": "存储 LM Hash（旧式可秒破）", "severity": "高", "detail": "NoLMHash 未启用"})
        else:
            findings.append({"user": "(哈希)", "issue": "LM Hash 已禁用", "severity": "信息", "detail": "仅存储 NTLM Hash"})
    except Exception:
        findings.append({"user": "(哈希)", "issue": "LM Hash 状态未知", "severity": "未知", "detail": "—"})

    # 4. 空密码会话检查（匿名 SMB 枚举）
    try:
        sess_out = run_command(["net", "session"], timeout=10)
        if "There are no entries" in sess_out or "没有" in sess_out or not sess_out.strip():
            findings.append({"user": "(会话)", "issue": "无空会话", "severity": "信息", "detail": "无匿名 SMB 会话"})
        else:
            findings.append({"user": "(会话)", "issue": "存在 SMB 会话", "severity": "中", "detail": "检查是否为匿名枚举"})
    except Exception:
        pass

    risk = "高危" if any(f["severity"] == "极高" for f in findings) else (
        "中危" if any(f["severity"] == "高" for f in findings) else (
            "低危" if any(f["severity"] == "中" for f in findings) else "安全"
        )
    )
    return {"total": len(findings), "risk_level": risk, "findings": findings}


@app.get("/api/pentest/anti-forensics")
def pentest_anti_forensics():
    """反取证/隐蔽通道检测：网卡混杂模式、隐蔽信道、日志清除痕迹、监控绕过工具"""
    findings = []

    # 1. 网卡混杂模式（嗅探器标志）
    promisc = []
    try:
        net_out = run_powershell(
            "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Select-Object Name,InterfaceDescription,LinkSpeed | ConvertTo-Json",
            timeout=10
        )
        try:
            nlist = json.loads(net_out) if net_out.strip().startswith("[") else ([json.loads(net_out)] if net_out.strip().startswith("{") else [])
        except Exception:
            nlist = []
        # 检查是否有嗅探工具进程占用网卡
        sniff_procs = ["wireshark", "tcpdump", "dumpcap", "nmap", "ettercap", "kismet", "aircrack"]
        running_procs = [p.name().lower() for p in psutil.process_iter(['name']) if p.info['name']]
        found_sniffers = [s for s in sniff_procs if any(s in p for p in running_procs)]
        if found_sniffers:
            findings.append({
                "category": "嗅探器", "name": f"检测到 {len(found_sniffers)} 个抓包工具",
                "severity": "高", "detail": "运行中：" + ", ".join(found_sniffers),
            })
        else:
            findings.append({"category": "嗅探器", "name": "无抓包工具运行", "severity": "信息", "detail": "—"})
    except Exception:
        findings.append({"category": "嗅探器", "name": "嗅探器检测失败", "severity": "未知", "detail": "—"})

    # 2. 可疑进程：调试器、注入、监控绕过
    suspicious_processes = []
    suspicious_keywords = {
        "mimikatz": "凭据提取工具", "procdump": "内存转储工具",
        "nltest": "域信任枚举", "processhacker": "进程注入/操控",
        "x96dbg": "动态调试器", "ollydbg": "动态调试器",
        "ida.exe": "逆向工具", "nc.exe": "Netcat 反弹",
        "ncat.exe": "Netcat 反弹",
    }
    try:
        for p in psutil.process_iter(['name', 'pid', 'exe']):
            pname = (p.info['name'] or "").lower()
            for kw, desc in suspicious_keywords.items():
                if kw in pname:
                    suspicious_processes.append({
                        "name": p.info['name'], "pid": p.info['pid'],
                        "exe": p.info.get('exe', '—'), "desc": desc,
                    })
                    break
    except Exception:
        pass
    if suspicious_processes:
        findings.append({
            "category": "可疑进程", "name": f"{len(suspicious_processes)} 个可疑进程运行",
            "severity": "高", "detail": "调试器/凭据工具/反弹 Shell",
        })
    else:
        findings.append({"category": "可疑进程", "name": "无可疑进程", "severity": "信息", "detail": "—"})

    # 3. 日志清除痕迹（System 日志最近清空）
    try:
        log_out = run_powershell(
            "Get-WinEvent -FilterHashtable @{LogName='System';Id=104} -MaxEvents 5 -ErrorAction SilentlyContinue | Select-Object TimeCreated,@{N='User';E={$_.Properties[0].Value}} | ConvertTo-Json",
            timeout=15
        )
        try:
            logs = json.loads(log_out) if log_out.strip().startswith("[") else ([json.loads(log_out)] if log_out.strip().startswith("{") else [])
        except Exception:
            logs = []
        if logs:
            findings.append({
                "category": "日志清除", "name": f"检测到 {len(logs)} 次事件日志清除",
                "severity": "极高", "detail": "Event ID 104（日志清空），可能是反取证行为",
            })
        else:
            findings.append({"category": "日志清除", "name": "无日志清除记录", "severity": "信息", "detail": "—"})
    except Exception:
        findings.append({"category": "日志清除", "name": "日志检查失败", "severity": "未知", "detail": "—"})

    # 4. Defender 实时保护是否被禁用
    try:
        def_out = run_powershell("(Get-MpComputerStatus).RealTimeProtectionEnabled", timeout=10).strip().lower()
        if "false" in def_out:
            findings.append({
                "category": "防御绕过", "name": "Defender 实时保护已禁用",
                "severity": "极高", "detail": "实时保护关闭，可能是绕过或被破坏",
            })
        else:
            findings.append({"category": "防御绕过", "name": "Defender 实时保护正常", "severity": "信息", "detail": "—"})
    except Exception:
        findings.append({"category": "防御绕过", "name": "Defender 状态未知", "severity": "未知", "detail": "—"})

    # 5. 可疑外联（非标准端口）
    try:
        external = []
        for c in psutil.net_connections(kind="inet"):
            if c.status == "ESTABLISHED" and c.raddr:
                rip = c.raddr.ip
                rport = c.raddr.port
                if not (rip.startswith("127.") or rip == "::1" or rip.startswith("192.168.") or rip.startswith("10.")):
                    # 非标准端口（443/80/53）
                    if rport not in (80, 443, 53, 8080, 8443):
                        external.append({"remote": f"{rip}:{rport}", "pid": c.pid, "process": _proc_name(c.pid)})
        if external:
            findings.append({
                "category": "隐蔽外联", "name": f"{len(external)} 个非标准端口外联",
                "severity": "高", "detail": "可能是 C2 通道（如 4444/1234 等）",
            })
        else:
            findings.append({"category": "隐蔽外联", "name": "无非标准端口外联", "severity": "信息", "detail": "—"})
    except Exception:
        findings.append({"category": "隐蔽外联", "name": "外联检测失败", "severity": "未知", "detail": "—"})

    risk = "高危" if any(f["severity"] == "极高" for f in findings) else (
        "中危" if any(f["severity"] == "高" for f in findings) else (
            "低危" if any(f["severity"] == "中" for f in findings) else "安全"
        )
    )
    return {
        "total_findings": len(findings),
        "risk_level": risk,
        "findings": findings,
        "suspicious_processes": suspicious_processes[:20],
        "external_connections": external if 'external' in locals() else [],
    }


# ======================== 文件工具 ========================
@app.get("/api/files/hash")
def file_hash(path: str = Query(...), algo: str = Query("sha256", pattern="^(md5|sha1|sha256|sha512)")):
    """文件哈希计算"""
    if not os.path.exists(path):
        return {"path": path, "error": "文件不存在"}
    if os.path.isdir(path):
        return {"path": path, "error": "路径是目录，请选择文件"}
    try:
        h = hashlib.new(algo)
        with open(path, "rb") as f:
            while True:
                chunk = f.read(8192 * 1024)
                if not chunk:
                    break
                h.update(chunk)
        size = os.path.getsize(path)
        return {
            "path": path,
            "algorithm": algo,
            "hash": h.hexdigest(),
            "size_bytes": size,
            "size_mb": round(size / (1024 * 1024), 2),
        }
    except Exception as e:
        return {"path": path, "error": str(e)}


@app.get("/api/files/large")
def find_large_files(dir: str = Query(...), min_size_mb: int = Query(100, ge=1), limit: int = Query(50, ge=1, le=500)):
    """查找大文件"""
    if not os.path.exists(dir):
        return {"dir": dir, "error": "目录不存在"}
    results = []
    min_bytes = min_size_mb * 1024 * 1024
    try:
        for root, dirs, files in os.walk(dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    size = os.path.getsize(fpath)
                    if size >= min_bytes:
                        results.append({
                            "path": fpath,
                            "size_mb": round(size / (1024 * 1024), 2),
                            "size_gb": round(size / (1024 ** 3), 3),
                        })
                except (PermissionError, OSError):
                    continue
        results.sort(key=lambda x: x["size_mb"], reverse=True)
        return {"dir": dir, "min_size_mb": min_size_mb, "count": len(results), "files": results[:limit]}
    except Exception as e:
        return {"dir": dir, "error": str(e)}


@app.get("/api/files/analyze")
def disk_analyze(dir: str = Query(...), limit: int = Query(50, ge=1, le=500)):
    """磁盘空间分析：按目录统计占用"""
    if not os.path.exists(dir):
        return {"dir": dir, "error": "目录不存在"}
    dir_sizes = {}
    file_count = 0
    total_size = 0
    try:
        for root, dirs, files in os.walk(dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    size = os.path.getsize(fpath)
                    total_size += size
                    file_count += 1
                    # 归属到 root 目录
                    dir_sizes[root] = dir_sizes.get(root, 0) + size
                except (PermissionError, OSError):
                    continue
        # 排序取 Top
        sorted_dirs = sorted(dir_sizes.items(), key=lambda x: x[1], reverse=True)[:limit]
        return {
            "dir": dir,
            "total_size_gb": round(total_size / (1024 ** 3), 2),
            "total_files": file_count,
            "scanned_dirs": len(dir_sizes),
            "top_dirs": [{"path": d, "size_mb": round(s / (1024 * 1024), 2)} for d, s in sorted_dirs],
        }
    except Exception as e:
        return {"dir": dir, "error": str(e)}


@app.post("/api/files/clean-temp")
def clean_temp():
    """清理临时文件"""
    temp_dirs = [
        os.environ.get("TEMP", ""),
        os.environ.get("TMP", ""),
        os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Temp"),
    ]
    cleaned = 0
    freed_mb = 0
    errors = 0
    for tdir in temp_dirs:
        if not tdir or not os.path.exists(tdir):
            continue
        for item in os.listdir(tdir):
            fpath = os.path.join(tdir, item)
            try:
                if os.path.isfile(fpath):
                    size = os.path.getsize(fpath)
                    os.remove(fpath)
                    cleaned += 1
                    freed_mb += size
                elif os.path.isdir(fpath):
                    import shutil
                    shutil.rmtree(fpath, ignore_errors=True)
                    cleaned += 1
            except (PermissionError, OSError):
                errors += 1
                continue
    return {
        "cleaned": cleaned,
        "freed_mb": round(freed_mb / (1024 * 1024), 2),
        "errors": errors,
        "message": f"清理完成：删除 {cleaned} 项，释放 {round(freed_mb / (1024 * 1024), 2)} MB",
    }


@app.get("/api/files/duplicates")
def find_duplicates(dir: str = Query(...), limit: int = Query(100, ge=1, le=500)):
    """重复文件检测（按内容哈希）"""
    if not os.path.exists(dir):
        return {"dir": dir, "error": "目录不存在"}
    # 先按大小分组，再对相同大小的计算哈希
    size_map = {}
    try:
        for root, dirs, files in os.walk(dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    size = os.path.getsize(fpath)
                    size_map.setdefault(size, []).append(fpath)
                except (PermissionError, OSError):
                    continue
        # 只对同大小文件多于1个的计算哈希
        hash_map = {}
        scanned = 0
        for size, paths in size_map.items():
            if len(paths) < 2:
                continue
            for p in paths:
                try:
                    h = hashlib.md5()
                    with open(p, "rb") as f:
                        while True:
                            chunk = f.read(8192 * 1024)
                            if not chunk:
                                break
                            h.update(chunk)
                    digest = h.hexdigest()
                    hash_map.setdefault((size, digest), []).append(p)
                    scanned += 1
                except (PermissionError, OSError):
                    continue
        dups = [{"size_mb": round(s / (1024 * 1024), 2), "files": paths}
                for (s, d), paths in hash_map.items() if len(paths) > 1]
        dups.sort(key=lambda x: x["size_mb"], reverse=True)
        total_dup_mb = sum(d["size_mb"] for d in dups)
        return {
            "dir": dir, "scanned": scanned,
            "duplicate_groups": len(dups),
            "total_dup_mb": round(total_dup_mb, 2),
            "duplicates": dups[:limit],
        }
    except Exception as e:
        return {"dir": dir, "error": str(e)}


# ======================== 系统增强 ========================
@app.get("/api/system/env")
def env_vars():
    """环境变量"""
    return {"variables": dict(os.environ), "count": len(os.environ)}


@app.get("/api/system/process-tree")
def process_tree():
    """进程树视图：父子关系 + CPU/内存占用"""
    try:
        # 构建进程树
        procs = {}
        for p in psutil.process_iter(attrs=["pid", "ppid", "name", "username",
                                              "cpu_percent", "memory_percent", "status"]):
            info = p.info
            pid = info["pid"]
            procs[pid] = {
                "pid": pid,
                "ppid": info.get("ppid", 0) or 0,
                "name": info.get("name", "—"),
                "username": info.get("username", "—"),
                "cpu_percent": round(info.get("cpu_percent") or 0, 1),
                "memory_percent": round(info.get("memory_percent") or 0, 1),
                "status": info.get("status", "—"),
                "children": [],
            }
        # 构建父子关系
        roots = []
        for pid, proc in procs.items():
            ppid = proc["ppid"]
            if ppid in procs and ppid != pid:
                procs[ppid]["children"].append(proc)
            else:
                roots.append(proc)

        def sort_tree(node):
            node["children"].sort(key=lambda x: x["cpu_percent"], reverse=True)
            for child in node["children"]:
                sort_tree(child)

        for root in roots:
            sort_tree(root)

        roots.sort(key=lambda x: x["cpu_percent"], reverse=True)

        total_procs = len(procs)
        return {"total": total_procs, "roots": roots[:50]}
    except Exception as e:
        return {"total": 0, "roots": [], "error": str(e)}


@app.get("/api/network/bandwidth-test")
def bandwidth_test(host: str = Query("127.0.0.1", description="目标主机"),
                    port: int = Query(8765, ge=1, le=65535),
                    duration: float = Query(3.0, ge=1.0, le=30.0, description="测试时长(秒)")):
    """带宽/延迟测试：测量到目标主机的连接延迟和吞吐量"""
    results = {"host": host, "port": port, "duration_s": duration}

    # 延迟测试
    latencies = []
    for _ in range(10):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            start = time.perf_counter()
            sock.connect((host, port))
            latency = (time.perf_counter() - start) * 1000  # ms
            latencies.append(latency)
            sock.close()
        except Exception:
            latencies.append(None)

    valid_lat = [l for l in latencies if l is not None]
    results["latency"] = {
        "min_ms": round(min(valid_lat), 2) if valid_lat else None,
        "avg_ms": round(sum(valid_lat) / len(valid_lat), 2) if valid_lat else None,
        "max_ms": round(max(valid_lat), 2) if valid_lat else None,
        "tests_ok": len(valid_lat),
        "tests_total": len(latencies),
    }

    # 吞吐量测试（通过多次连接测量）
    bytes_total = 0
    conn_count = 0
    start_time = time.perf_counter()
    timeout_at = start_time + duration

    while time.perf_counter() < timeout_at:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((host, port))
            # 发送测试数据
            test_data = b"GET / HTTP/1.1\r\nHost: test\r\n\r\n"
            sock.send(test_data)
            # 尝试接收少量数据
            sock.settimeout(0.5)
            try:
                resp = sock.recv(1024)
                bytes_total += len(resp)
            except socket.timeout:
                pass
            bytes_total += len(test_data)
            conn_count += 1
            sock.close()
        except Exception:
            pass
        time.sleep(0.05)

    elapsed = time.perf_counter() - start_time
    results["throughput"] = {
        "connections": conn_count,
        "bytes": bytes_total,
        "duration_s": round(elapsed, 2),
        "kbps": round(bytes_total * 8 / elapsed / 1024, 2) if elapsed > 0 else 0,
    }

    return results


@app.delete("/api/files/delete")
def delete_file(path: str = Query(..., description="文件或目录路径"),
                recursive: bool = Query(False, description="递归删除目录内容")):
    """删除文件或目录（危险操作，请谨慎使用）"""
    # 安全检查：不允许删除系统关键目录
    dangerous_paths = [
        r"C:\Windows", r"C:\Program Files", r"C:\Program Files (x86)",
        r"C:\Users", r"C:\ProgramData",
    ]
    abs_path = os.path.abspath(path)
    for dp in dangerous_paths:
        if abs_path.startswith(os.path.abspath(dp)):
            return {"path": path, "success": False,
                    "message": f"安全限制：不允许删除系统关键目录 {dp}"}

    if not os.path.exists(abs_path):
        return {"path": path, "success": False, "message": "路径不存在"}

    try:
        if os.path.isfile(abs_path):
            os.remove(abs_path)
            return {"path": path, "success": True, "type": "file", "message": "文件已删除"}
        elif os.path.isdir(abs_path):
            if recursive:
                import shutil
                shutil.rmtree(abs_path)
                return {"path": path, "success": True, "type": "directory", "message": "目录已递归删除"}
            else:
                return {"path": path, "success": False,
                        "message": "目标是目录，请设置 recursive=true 确认递归删除"}
        else:
            return {"path": path, "success": False, "message": "不支持的路径类型"}
    except PermissionError:
        return {"path": path, "success": False, "message": "权限不足"}
    except Exception as e:
        return {"path": path, "success": False, "message": str(e)}


@app.get("/api/system/updates")
def windows_updates():
    """Windows 更新状态"""
    output = run_powershell(
        "Get-WindowsUpdateLog 2>$null; "
        "Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 10 | "
        "Format-Table HotFixID,Description,InstalledOn -AutoSize",
        timeout=15
    )
    return {"output": output}


@app.get("/api/system/power")
def power_plan():
    """电源计划"""
    output = run_command(["powercfg", "/list"], timeout=10)
    active = run_command(["powercfg", "/getactivescheme"], timeout=10)
    return {"plans": output, "active": active}


@app.get("/api/system/sensors")
def sensors():
    """传感器信息（温度/风扇/电池）"""
    result = {}
    # 电池
    try:
        bat = psutil.sensors_battery()
        if bat:
            result["battery"] = {
                "percent": bat.percent,
                "plugged": bat.power_plugged,
                "secs_left": bat.secsleft if bat.secsleft != psutil.POWER_TIME_UNLIMITED else "unlimited",
            }
    except Exception:
        pass
    # 温度（多数 Windows 不支持）
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            result["temperatures"] = {k: [{"label": t.label, "current": t.current, "high": t.high} for t in v] for k, v in temps.items()}
    except Exception:
        pass
    # 风扇
    try:
        fans = psutil.sensors_fans()
        if fans:
            result["fans"] = {k: [{"label": f.label, "current": f.current} for f in v] for k, v in fans.items()}
    except Exception:
        pass
    return result


# ======================== 命令终端 ========================
@app.post("/api/terminal/run")
def run_terminal(cmd: str = Query(...)):
    """执行终端命令"""
    # 安全限制：禁止危险命令
    dangerous = ["format", "del /f /s /q c:", "shutdown", "rd /s /q"]
    for d in dangerous:
        if d in cmd.lower():
            return {"cmd": cmd, "output": "该命令被安全策略拦截", "blocked": True}
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace"
        )
        output = (result.stdout or "") + (result.stderr or "")
        return {"cmd": cmd, "output": output.strip(), "returncode": result.returncode}
    except subprocess.TimeoutExpired:
        return {"cmd": cmd, "output": "命令超时（30秒）", "returncode": -1}
    except Exception as e:
        return {"cmd": cmd, "output": f"执行出错: {str(e)}", "returncode": -1}


# ======================== 静态文件服务 ========================
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "SysOps Toolkit API is running. Static files not found."}


@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765)
