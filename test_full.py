import urllib.request, json, urllib.parse

BASE = "http://127.0.0.1:8765"

def get(path):
    try:
        return json.loads(urllib.request.urlopen(BASE + path).read())
    except Exception as e:
        return {"error": str(e)}

def post(path):
    try:
        req = urllib.request.Request(BASE + path, method='POST')
        return json.loads(urllib.request.urlopen(req).read())
    except Exception as e:
        return {"error": str(e)}

def delete(path):
    try:
        req = urllib.request.Request(BASE + path, method='DELETE')
        return json.loads(urllib.request.urlopen(req).read())
    except Exception as e:
        return {"error": str(e)}

def enc(s):
    return urllib.parse.quote(s)

# ===== v2.2 新增 API 测试 =====
new_tests = [
    ("进程树", "/api/system/process-tree"),
    ("带宽测试", "/api/network/bandwidth-test?host=127.0.0.1&port=8765&duration=2"),
    ("端口扫描(含服务名)", f"/api/network/scan?host={enc('127.0.0.1')}&start_port=8080&end_port=8090"),
    ("系统总览(磁盘修复)", "/api/system/overview"),
]

# ===== 原有 API 测试 =====
original_tests = [
    ("系统历史", "/api/system/history"),
    ("子网计算", f"/api/network/subnet?ip={enc('192.168.1.1')}&prefix=24"),
    ("端口扫描(本机20-30)", f"/api/network/scan?host={enc('127.0.0.1')}&start_port=20&end_port=30"),
    ("HTTP头", f"/api/network/http-headers?url={enc('http://baidu.com')}"),
    ("环境变量", "/api/system/env"),
    ("电源计划", "/api/system/power"),
    ("传感器", "/api/system/sensors"),
    ("Defender", "/api/security/defender"),
    ("已装程序", "/api/security/programs"),
    ("计划任务", "/api/security/tasks"),
    ("共享文件夹", "/api/security/shares"),
    ("密码策略", "/api/security/password-policy"),
    ("已装补丁", "/api/security/hotfixes"),
    ("Wi-Fi", "/api/network/wifi"),
    ("文件哈希", "/api/files/hash?path=" + enc("C:\\Windows\\notepad.exe") + "&algo=sha256"),
    ("大文件查找", "/api/files/large?dir=" + enc("C:\\Windows") + "&min_size_mb=50"),
    ("磁盘分析", "/api/files/analyze?dir=" + enc("C:\\Windows\\System32") + "&limit=10"),
    ("CPU详情", "/api/system/cpu"),
    ("内存详情", "/api/system/memory"),
    ("磁盘列表", "/api/system/disks"),
    ("网络接口", "/api/system/network-interfaces"),
    ("进程列表", "/api/processes?sort_by=cpu"),
    ("服务列表", "/api/services"),
    ("防火墙", "/api/security/firewall"),
    ("本地用户", "/api/security/users"),
    ("启动项", "/api/security/startup"),
    ("已登录用户", "/api/security/logged-on"),
    ("事件日志(System)", "/api/security/eventlog?log=System&count=10"),
    ("安全基线", "/api/security/baseline"),
    ("攻击面分析", "/api/security/attack-surface"),
    ("提权路径", "/api/pentest/privesc"),
    ("持久化检查", "/api/pentest/persistence"),
    ("弱口令审计", "/api/pentest/weak-credentials"),
    ("反取证检测", "/api/pentest/anti-forensics"),
]

print("=" * 60)
print("NetWalker v2.2.0 API 冒烟测试")
print("=" * 60)

# 先测试健康检查
print("\n[健康检查]")
r = get("/api/health")
if r.get("status") == "ok":
    print(f"[OK] 服务运行正常: {r.get('timestamp')}")
else:
    print(f"[FAIL] 服务异常: {r}")
    print("请先启动服务器: python server.py")
    exit(1)

print("\n" + "-" * 40)
print("v2.2 新增 API 测试")
print("-" * 40)

for name, path in new_tests:
    r = get(path)
    if isinstance(r, dict) and r.get("error"):
        print(f"[X] {name}: 错误 {r['error'][:80]}")
    else:
        if name == "进程树":
            print(f"[OK] {name}: 共 {r.get('total', 0)} 个进程，显示 {len(r.get('roots', []))} 个根进程")
        elif name == "带宽测试":
            lat = r.get('latency', {})
            tp = r.get('throughput', {})
            print(f"[OK] {name}: 延迟 {lat.get('avg_ms', '?')}ms, 吞吐 {tp.get('kbps', '?')}kbps")
        elif name == "端口扫描(含服务名)":
            print(f"[OK] {name}: 开放端口 {r.get('open_ports', [])}, 端口信息 {len(r.get('port_info', []))} 条")
        elif name == "系统总览(磁盘修复)":
            print(f"[OK] {name}: 磁盘 {r.get('disk_total_gb', '?')}GB, CPU {r.get('cpu_percent', '?')}%")
        else:
            print(f"[OK] {name}: 返回数据")

print("\n" + "-" * 40)
print("原有 API 测试")
print("-" * 40)

for name, path in original_tests:
    r = get(path)
    if isinstance(r, dict) and r.get("error"):
        print(f"[X] {name}: 错误 {r['error'][:80]}")
    else:
        if name == "子网计算":
            print(f"[OK] {name}: {r.get('network')}/{r.get('prefix')} 可用主机 {r.get('num_hosts')}")
        elif name == "端口扫描(本机20-30)":
            print(f"[OK] {name}: 开放端口 {r.get('open_ports')}")
        elif name == "HTTP头":
            print(f"[OK] {name}: 状态码 {r.get('status')} {r.get('reason','')}")
        elif name == "环境变量":
            print(f"[OK] {name}: {r.get('count')} 个变量")
        elif name == "文件哈希":
            if r.get("error"):
                print(f"[X] {name}: {r['error']}")
            else:
                print(f"[OK] {name}: {r.get('algorithm','').upper()} = {str(r.get('hash',''))[:32]}...")
        elif name == "大文件查找":
            print(f"[OK] {name}: 找到 {r.get('count',0)} 个文件")
        elif name == "磁盘分析":
            print(f"[OK] {name}: 总占用 {r.get('total_size_gb','?')} GB, {r.get('total_files','?')} 文件")
        elif name in ("Defender", "Wi-Fi", "防火墙"):
            print(f"[OK] {name}: 返回 {len(str(r))} 字符")
        elif name == "已装程序":
            print(f"[OK] {name}: {r.get('count',0)} 个程序")
        elif name == "计划任务":
            print(f"[OK] {name}: {r.get('count',0)} 个任务")
        elif name == "安全基线":
            print(f"[OK] {name}: 评分 {r.get('score', '?')}")
        elif name == "攻击面分析":
            print(f"[OK] {name}: 监听 {len(r.get('listening', []))} 项")
        elif name == "进程树":
            print(f"[OK] {name}: 共 {r.get('total', 0)} 个进程")
        else:
            print(f"[OK] {name}: 返回数据")

# 测试 POST API
print("\n" + "-" * 40)
print("POST API 测试")
print("-" * 40)

r = post(f"/api/terminal/run?cmd={enc('whoami')}")
if r.get("error"):
    print(f"[X] 命令终端 whoami: {r['error'][:60]}")
else:
    print(f"[OK] 命令终端 whoami: {r.get('output','')[:60]}")

r = post("/api/files/clean-temp")
if r.get("error"):
    print(f"[X] 清理临时: {r['error'][:60]}")
else:
    print(f"[OK] 清理临时: {r.get('message','')[:60]}")

# 测试 DELETE API (v2.2 新增)
print("\n" + "-" * 40)
print("DELETE API 测试 (v2.2 新增)")
print("-" * 40)

# 测试删除系统目录（应该被拦截）
sys_path = "C:/Windows"
r = delete(f"/api/files/delete?path={enc(sys_path)}")
if r.get("success") == False and "安全限制" in r.get("message", ""):
    print(f"[OK] 删除系统目录被正确拦截: {r['message']}")
else:
    print(f"[WARN] 删除系统目录: {r.get('message', '未知')}")

# 测试删除不存在的文件
nonexist_path = "C:/nonexistent_file_12345.txt"
r = delete(f"/api/files/delete?path={enc(nonexist_path)}")
if r.get("success") == False and "不存在" in r.get("message", ""):
    print(f"[OK] 删除不存在文件正确处理: {r['message']}")
else:
    print(f"[INFO] 删除不存在文件: {r.get('message', '未知')}")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
