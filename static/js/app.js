/* ===== NetWalker (巡网者) v2.2 - 前端逻辑 =====
 * Copyright (c) 2026 知行工作室. 仅供学习研究与合法授权下的本机自检使用。
 */
const API = '';
let currentPage = 'dashboard';

// ===== 移动端菜单控制 =====
function initMobileMenu() {
    const toggleBtn = document.getElementById('menu-toggle');
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.getElementById('overlay');
    
    function openMenu() {
        sidebar.classList.add('open');
        overlay.classList.add('active');
    }
    
    function closeMenu() {
        sidebar.classList.remove('open');
        overlay.classList.remove('active');
    }
    
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            if (sidebar.classList.contains('open')) {
                closeMenu();
            } else {
                openMenu();
            }
        });
    }
    
    if (overlay) {
        overlay.addEventListener('click', closeMenu);
    }
    
    // 点击侧边栏项目后自动关闭菜单
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            if (window.innerWidth <= 768) {
                closeMenu();
            }
        });
    });
    
    // 窗口调整大小时，如果PC尺寸则强制关闭菜单
    window.addEventListener('resize', () => {
        if (window.innerWidth > 768) {
            closeMenu();
        }
    });
}

// ===== 通用请求 =====
async function fetchAPI(path) {
    const res = await fetch(API + path);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

async function postAPI(path) {
    const res = await fetch(API + path, { method: 'POST' });
    return res.json();
}

// ===== Toast =====
function toast(msg, type = 'info') {
    const c = document.getElementById('toast-container');
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = msg;
    c.appendChild(el);
    setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 200); }, 3500);
}

// ===== 加载状态 =====
function loading(el, msg = '加载中...') {
    el.innerHTML = `<div class="loading-overlay"><div class="spinner"></div>${msg}</div>`;
}

function emptyState(el, msg = '暂无数据') {
    el.innerHTML = `<div class="empty-state"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg><div>${msg}</div></div>`;
}

// ===== 工具函数 =====
function getProgressClass(p) { return p < 60 ? 'green' : p < 85 ? 'yellow' : 'red'; }
function getGaugeColor(p) { return p < 60 ? '#22c55e' : p < 85 ? '#eab308' : '#ef4444'; }

function gaugeRingSVG(percent, color) {
    const r = 42, circ = 2 * Math.PI * r;
    const offset = circ - (percent / 100) * circ;
    return `<div class="gauge-ring"><svg viewBox="0 0 100 100"><circle class="gauge-bg" cx="50" cy="50" r="${r}"/><circle class="gauge-fg" cx="50" cy="50" r="${r}" stroke="${color}" stroke-dasharray="${circ}" stroke-dashoffset="${offset}"/></svg><div class="gauge-text">${percent}%</div></div>`;
}

function fmtNum(n) { return n == null ? '—' : Number(n).toLocaleString(); }
function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

// ===== 进行中状态（动作可视化）=====
// 在目标元素显示一张「进行中」卡片：标题 + 副标题 + 进度条（percent 为数字则确定，缺省则不确定动画）
function taskRunning(el, title, subtitle, percent) {
    const indeterminate = (typeof percent !== 'number');
    const bar = indeterminate
        ? `<div class="indeterminate-bar"><div class="indeterminate-fill"></div></div>`
        : `<div class="progress-bar" style="margin:0"><div class="progress-fill accent" style="width:${Math.min(100,Math.max(0,percent))}%"></div></div>`;
    const pctText = indeterminate ? '' : `<span class="mono text-accent" style="font-size:13px">${Math.round(percent)}%</span>`;
    el.innerHTML = `<div class="card task-running">
        <div class="task-running-head"><div class="spinner"></div><div class="task-running-title">${esc(title)} ${pctText}</div></div>
        <div class="task-running-sub">${esc(subtitle || '')}</div>
        ${bar}
    </div>`;
}
// 更新已有进行中卡片的进度
function taskRunningUpdate(el, percent, subtitle) {
    const fill = el.querySelector('.progress-fill');
    const pct = el.querySelector('.task-running-title .mono');
    if (fill) fill.style.width = Math.min(100, Math.max(0, percent)) + '%';
    if (pct) pct.textContent = Math.round(percent) + '%';
    if (subtitle !== undefined && el.querySelector('.task-running-sub')) el.querySelector('.task-running-sub').textContent = subtitle;
}
// 按钮忙碌态（禁用 + 显示 spinner）
function setBtnBusy(btn, busy) {
    if (!btn) return;
    if (busy) {
        if (btn.dataset.orig === undefined) btn.dataset.orig = btn.innerHTML;
        btn.disabled = true;
        btn.classList.add('btn-busy');
        btn.innerHTML = `<div class="spinner" style="width:13px;height:13px;border-width:2px"></div>处理中`;
    } else {
        btn.disabled = false;
        btn.classList.remove('btn-busy');
        if (btn.dataset.orig !== undefined) { btn.innerHTML = btn.dataset.orig; delete btn.dataset.orig; }
    }
}

// ===== 报告导出（生成独立 HTML 下载）=====
function exportHTML(filename, title, bodyHTML) {
    const ts = new Date().toLocaleString('zh-CN');
    const html = `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>${esc(title)} - 安全报告</title>
<style>
body{font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;background:#0d1117;color:#e6edf3;margin:0;padding:40px;line-height:1.6}
.report{max-width:960px;margin:0 auto}
h1{color:#2dd4bf;border-bottom:1px solid #30363d;padding-bottom:12px;font-size:22px;margin:0 0 4px}
h2{color:#8b949e;font-size:13px;text-transform:uppercase;letter-spacing:.5px;margin:24px 0 10px;font-weight:600}
.meta{color:#6e7681;font-size:12px;margin-bottom:20px}
.card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:16px;margin-bottom:12px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{background:#21262d;padding:10px 12px;text-align:left;color:#8b949e;border-bottom:1px solid #30363d;font-weight:600}
td{padding:8px 12px;border-bottom:1px solid #30363d;vertical-align:top}
.badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600}
.badge-green{background:rgba(34,197,94,.15);color:#22c55e}.badge-red{background:rgba(239,68,68,.15);color:#ef4444}
.badge-yellow{background:rgba(234,179,8,.15);color:#eab308}.badge-blue{background:rgba(59,130,246,.15);color:#3b82f6}
.badge-gray{background:#21262d;color:#6e7681}
.mono{font-family:Consolas,"Cascadia Code",monospace}
.info-item{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #30363d;font-size:13px}
.info-item:last-child{border:none}.info-key{color:#8b949e}.info-val{font-family:Consolas,monospace;font-weight:500;text-align:right;word-break:break-all}
.check-row{display:flex;gap:12px;padding:10px;background:#21262d;border:1px solid #30363d;border-radius:6px;margin-bottom:6px}
.footer{color:#6e7681;font-size:11px;margin-top:32px;border-top:1px solid #30363d;padding-top:12px}
</style></head><body><div class="report">
<h1>${esc(title)}</h1>
<div class="meta">生成时间：${ts} · 主机：${esc(location.hostname)} · SysOps Toolkit</div>
${bodyHTML}
<div class="footer">本报告由 SysOps Toolkit 自动生成 · Copyright (c) 2026 知行工作室 · 仅供安全自检参考</div>
</div></body></html>`;
    const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    toast('报告已导出：' + filename, 'success');
}

// ===== 导航 =====
const pageTitles = {
    dashboard:'仪表盘', realtime:'实时监控', cpu:'CPU 监控', memory:'内存 & 磁盘',
    interfaces:'网络接口', env:'环境变量', syspower:'电源 & 补丁', proctree:'进程树',
    network:'网络诊断', portscan:'端口扫描', bandwidth:'带宽测试', webcheck:'SSL & HTTP 检测',
    wifi:'Wi-Fi 信息', subnet:'子网计算器', connections:'连接监控',
    processes:'进程管理', services:'服务管理', tasks:'计划任务', terminal:'命令终端',
    hash:'文件哈希', largefiles:'大文件查找', diskanalyze:'磁盘分析',
    duplicates:'重复文件', cleantemp:'清理临时文件',
    security:'安全中心', assessment:'安全评估', eventlog:'事件日志', programs:'已装程序', shares:'共享文件夹',
    privesc:'提权路径', persistence:'持久化检查', weakcred:'弱口令审计', antiforen:'反取证检测'
};

document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => switchPage(btn.dataset.page));
});

function switchPage(page) {
    currentPage = page;
    document.querySelectorAll('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.page === page));
    document.querySelectorAll('.page').forEach(p => p.classList.toggle('active', p.id === 'page-' + page));
    document.getElementById('page-title').textContent = pageTitles[page] || page;
    if (page === 'realtime') return; // 实时监控需手动启动
    loadPageData(page);
}

document.getElementById('refresh-btn').addEventListener('click', () => loadPageData(currentPage));

// Tab 切换
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        const target = tab.dataset.tab;
        tab.parentElement.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t === tab));
        tab.parentElement.parentElement.querySelectorAll('.tab-content').forEach(c => c.classList.toggle('active', c.dataset.content === target));
    });
});

function loadPageData(page) {
    const loaders = {
        dashboard:loadDashboard, cpu:loadCPU, memory:loadMemory, interfaces:loadInterfaces,
        env:loadEnv, syspower:loadSysPower, proctree:loadProcessTree, bandwidth:()=>{},
        connections:loadConnections,
        processes:loadProcesses, services:loadServices, tasks:loadTasks,
        security:loadSecurity, shares:loadShares, eventlog:loadEventLog,
        // 以下页面为耗时扫描，需用户点击按钮触发，不自动加载
        assessment:()=>{}, programs:()=>{},
        privesc:()=>{}, persistence:()=>{}, weakcred:()=>{}, antiforen:()=>{}
    };
    if (loaders[page]) loaders[page]();
}

// ===== 进程树 =====
async function loadProcessTree() {
    const el = document.getElementById('proctree-result');
    const countEl = document.getElementById('proctree-count');
    loading(el, '加载进程树...');
    try {
        const data = await fetchAPI('/api/system/process-tree');
        countEl.textContent = `共 ${data.total} 个进程（显示前 ${data.roots.length} 个根进程）`;
        if (data.error) { emptyState(el, data.error); return; }
        if (!data.roots.length) { emptyState(el, '无进程数据'); return; }
        
        function renderNode(node, level) {
            const indent = level * 24;
            const cpuColor = node.cpu_percent > 50 ? 'text-red' : node.cpu_percent > 20 ? 'text-yellow' : '';
            const memColor = node.memory_percent > 10 ? 'text-red' : node.memory_percent > 5 ? 'text-yellow' : '';
            return `<div style="padding-left:${indent}px;position:relative;border-left:${level>0?'1px solid #30363d':'none'};margin-left:${level>0?'12px':'0'}">
                <div class="info-item" style="padding:8px 12px;background:rgba(33,38,45,0.5);border-radius:6px;margin-bottom:4px">
                    <span class="info-key">${esc(node.name)} <span class="text-muted" style="font-size:11px">(${node.pid})</span></span>
                    <span class="badge ${node.status==='running'?'badge-green':'badge-gray'}">${esc(node.status)}</span>
                    <span class="text-secondary ${cpuColor}" style="margin-left:8px;font-size:11px">CPU: ${node.cpu_percent}%</span>
                    <span class="text-secondary ${memColor}" style="margin-left:8px;font-size:11px">内存: ${node.memory_percent}%</span>
                </div>
                ${node.children && node.children.length ? node.children.map(child => renderNode(child, level+1)).join('') : ''}
            </div>`;
        }
        
        el.innerHTML = `<div class="card" style="padding:12px">${data.roots.map(root => renderNode(root, 0)).join('')}</div>`;
    } catch (e) { emptyState(el, '加载失败: ' + e.message); }
}

// ===== 带宽测试 =====
async function runBandwidthTest() {
    const host = document.getElementById('bw-host').value.trim();
    const port = document.getElementById('bw-port').value;
    const duration = document.getElementById('bw-duration').value;
    const el = document.getElementById('bw-result');
    const statusEl = document.getElementById('bw-status');
    const btn = document.querySelector('#page-bandwidth .btn-primary');
    if (!host || !port) { toast('请填写主机和端口', 'error'); return; }
    setBtnBusy(btn, true);
    statusEl.textContent = '测试中...';
    taskRunning(el, '带宽测试', `正在测试 ${host}:${port} 的延迟和吞吐量...`);
    try {
        const data = await fetchAPI(`/api/network/bandwidth-test?host=${encodeURIComponent(host)}&port=${port}&duration=${duration}`);
        const latRows = `
            <div class="info-item"><span class="info-key">最小延迟</span><span class="info-val mono">${data.latency.min_ms} ms</span></div>
            <div class="info-item"><span class="info-key">平均延迟</span><span class="info-val mono text-accent">${data.latency.avg_ms} ms</span></div>
            <div class="info-item"><span class="info-key">最大延迟</span><span class="info-val mono">${data.latency.max_ms} ms</span></div>
            <div class="info-item"><span class="info-key">成功率</span><span class="info-val">${data.latency.tests_ok}/${data.latency.tests_total}</span></div>
        `;
        const tpRows = `
            <div class="info-item"><span class="info-key">连接数</span><span class="info-val mono">${data.throughput.connections}</span></div>
            <div class="info-item"><span class="info-key">传输字节</span><span class="info-val mono">${fmtNum(data.throughput.bytes)} B</span></div>
            <div class="info-item"><span class="info-key">实际时长</span><span class="info-val">${data.throughput.duration_s} 秒</span></div>
            <div class="info-item"><span class="info-key">吞吐量</span><span class="info-val mono text-accent">${data.throughput.kbps} kbps</span></div>
        `;
        el.innerHTML = `<div class="card">
            <div class="info-list">
                <div class="info-item"><span class="info-key">目标</span><span class="info-val mono">${esc(data.host)}:${data.port}</span></div>
                <div class="info-item"><span class="info-key">测试时长</span><span class="info-val">${data.duration_s} 秒</span></div>
            </div>
            <div style="margin-top:16px">
                <div class="card-header"><span class="card-title">延迟测试（10 次采样）</span></div>
                <div class="info-list">${latRows}</div>
            </div>
            <div style="margin-top:16px">
                <div class="card-header"><span class="card-title">吞吐量测试</span></div>
                <div class="info-list">${tpRows}</div>
            </div>
        </div>`;
        statusEl.textContent = '测试完成';
        toast('带宽测试完成', 'success');
    } catch (e) { emptyState(el, '测试失败: ' + e.message); statusEl.textContent = '失败'; }
    finally { setBtnBusy(btn, false); }
}

// ===== 仪表盘 =====
async function loadDashboard() {
    const grid = document.getElementById('gauge-grid');
    const sysInfo = document.getElementById('sys-info');
    const diskList = document.getElementById('disk-list');
    loading(grid, '获取系统指标...');
    loading(sysInfo); loading(diskList);
    try {
        const [overview, disks] = await Promise.all([fetchAPI('/api/system/overview'), fetchAPI('/api/system/disks')]);
        grid.innerHTML = `
            <div class="card">${gaugeRingSVG(overview.cpu_percent, getGaugeColor(overview.cpu_percent))}<div class="gauge-label">CPU 使用率</div></div>
            <div class="card">${gaugeRingSVG(overview.memory_percent, getGaugeColor(overview.memory_percent))}<div class="gauge-label">内存使用率</div></div>
            <div class="card">${gaugeRingSVG(overview.disk_percent, getGaugeColor(overview.disk_percent))}<div class="gauge-label">磁盘使用率</div></div>
            <div class="card"><div class="gauge-ring" style="display:flex;align-items:center;justify-content:center"><div style="font-size:30px;font-family:var(--mono);color:var(--accent)">${overview.uptime_hours}<span style="font-size:14px;color:var(--text-secondary)">h</span></div></div><div class="gauge-label">运行时间</div></div>
        `;
        sysInfo.innerHTML = `
            <div class="info-item"><span class="info-key">操作系统</span><span class="info-val">${overview.os}</span></div>
            <div class="info-item"><span class="info-key">版本</span><span class="info-val">${overview.os_version}</span></div>
            <div class="info-item"><span class="info-key">主机名</span><span class="info-val">${overview.hostname}</span></div>
            <div class="info-item"><span class="info-key">架构</span><span class="info-val">${overview.arch}</span></div>
            <div class="info-item"><span class="info-key">处理器</span><span class="info-val" style="font-size:11px">${overview.processor}</span></div>
            <div class="info-item"><span class="info-key">物理核心</span><span class="info-val">${overview.cpu_count_physical}</span></div>
            <div class="info-item"><span class="info-key">逻辑核心</span><span class="info-val">${overview.cpu_count_logical}</span></div>
            <div class="info-item"><span class="info-key">开机时间</span><span class="info-val">${overview.boot_time}</span></div>
            <div class="info-item"><span class="info-key">内存总量</span><span class="info-val">${overview.memory_total_gb} GB</span></div>
            <div class="info-item"><span class="info-key">磁盘总量</span><span class="info-val">${overview.disk_total_gb} GB</span></div>
        `;
        if (disks.partitions.length === 0) { emptyState(diskList, '无分区信息'); }
        else {
            diskList.innerHTML = disks.partitions.map(p => `
                <div style="margin-bottom:14px">
                    <div style="display:flex;justify-content:space-between;margin-bottom:4px"><span class="mono">${p.device} <span class="text-muted">(${p.fstype})</span></span><span class="mono">${p.used_gb} / ${p.total_gb} GB</span></div>
                    <div class="progress-bar"><div class="progress-fill ${getProgressClass(p.percent)}" style="width:${p.percent}%"></div></div>
                </div>`).join('');
        }
    } catch (e) { grid.innerHTML = `<div class="empty-state">加载失败: ${e.message}</div>`; }
}

// ===== 实时监控 =====
let rtTimer = null, rtCpuData = [], rtMemData = [];
const RT_MAX = 60;

document.getElementById('rt-toggle').addEventListener('click', () => {
    if (rtTimer) { stopRealtime(); } else { startRealtime(); }
});

function startRealtime() {
    document.getElementById('rt-toggle').textContent = '⏸ 停止监控';
    document.getElementById('rt-status').textContent = '监控中...';
    const interval = Math.max(500, parseInt(document.getElementById('rt-interval').value) || 2000);
    rtCpuData = []; rtMemData = [];
    rtTick(); // 立即执行一次
    rtTimer = setInterval(rtTick, interval);
}

function stopRealtime() {
    clearInterval(rtTimer);
    rtTimer = null;
    document.getElementById('rt-toggle').textContent = '▶ 开始监控';
    document.getElementById('rt-status').textContent = '已停止';
}

async function rtTick() {
    try {
        const h = await fetchAPI('/api/system/history');
        rtCpuData = h.cpu; rtMemData = h.memory;
        document.getElementById('rt-cpu-val').textContent = rtCpuData[rtCpuData.length-1] + '%';
        document.getElementById('rt-mem-val').textContent = rtMemData[rtMemData.length-1] + '%';
        drawLineChart('rt-cpu-chart', rtCpuData, '#2dd4bf', 100);
        drawLineChart('rt-mem-chart', rtMemData, '#a855f7', 100);
        // 网络 I/O
        const net = await fetchAPI('/api/system/network-interfaces');
        const io = psutilNetToInfo(net);
        document.getElementById('rt-net-info').innerHTML = io;
    } catch (e) {}
}

function psutilNetToInfo(data) {
    let html = '';
    const total = { sent: 0, recv: 0 };
    for (const [name, iface] of Object.entries(data.interfaces)) {
        if (iface.bytes_sent_mb) total.sent += iface.bytes_sent_mb;
        if (iface.bytes_recv_mb) total.recv += iface.bytes_recv_mb;
        if (iface.ipv4 && iface.ipv4.length) {
            html += `<div class="info-item"><span class="info-key">${name} (${iface.ipv4[0]})</span><span class="info-val">↑${iface.bytes_sent_mb||0}MB ↓${iface.bytes_recv_mb||0}MB</span></div>`;
        }
    }
    return html;
}

function drawLineChart(canvasId, data, color, maxY) {
    const canvas = document.getElementById(canvasId);
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth, h = canvas.clientHeight || 200;
    canvas.width = w * dpr; canvas.height = h * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);
    if (data.length < 2) return;
    const pad = { l: 35, r: 10, t: 10, b: 20 };
    const cw = w - pad.l - pad.r, ch = h - pad.t - pad.b;
    // 网格
    ctx.strokeStyle = '#21262d'; ctx.lineWidth = 1;
    ctx.font = '10px monospace'; ctx.fillStyle = '#6e7681';
    for (let i = 0; i <= 4; i++) {
        const y = pad.t + (ch / 4) * i;
        ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(pad.l + cw, y); ctx.stroke();
        const val = Math.round(maxY - (maxY / 4) * i);
        ctx.fillText(val + '%', 4, y + 3);
    }
    // 折线
    const stepX = cw / Math.max(1, RT_MAX - 1);
    // 渐变填充
    const grad = ctx.createLinearGradient(0, pad.t, 0, pad.t + ch);
    grad.addColorStop(0, color + '40');
    grad.addColorStop(1, color + '00');
    ctx.beginPath();
    ctx.moveTo(pad.l, pad.t + ch);
    data.forEach((v, i) => {
        const x = pad.l + stepX * i;
        const y = pad.t + ch - (Math.min(v, maxY) / maxY) * ch;
        if (i === 0) ctx.lineTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.lineTo(pad.l + stepX * (data.length - 1), pad.t + ch);
    ctx.closePath();
    ctx.fillStyle = grad; ctx.fill();
    // 线条
    ctx.beginPath();
    data.forEach((v, i) => {
        const x = pad.l + stepX * i;
        const y = pad.t + ch - (Math.min(v, maxY) / maxY) * ch;
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.stroke();
}

// ===== CPU =====
async function loadCPU() {
    const gaugeEl = document.getElementById('cpu-gauge');
    const infoEl = document.getElementById('cpu-info');
    const coresEl = document.getElementById('cpu-cores');
    loading(gaugeEl); loading(infoEl); loading(coresEl);
    try {
        const cpu = await fetchAPI('/api/system/cpu');
        gaugeEl.innerHTML = gaugeRingSVG(cpu.overall, getGaugeColor(cpu.overall));
        infoEl.innerHTML = `
            <div class="info-item"><span class="info-key">逻辑核心数</span><span class="info-val">${cpu.logical_count}</span></div>
            <div class="info-item"><span class="info-key">物理核心数</span><span class="info-val">${cpu.physical_count}</span></div>
            ${cpu.freq_current?`<div class="info-item"><span class="info-key">当前频率</span><span class="info-val">${cpu.freq_current} MHz</span></div>`:''}
            ${cpu.freq_max?`<div class="info-item"><span class="info-key">最大频率</span><span class="info-val">${cpu.freq_max} MHz</span></div>`:''}
            ${cpu.freq_min?`<div class="info-item"><span class="info-key">最小频率</span><span class="info-val">${cpu.freq_min} MHz</span></div>`:''}
        `;
        coresEl.innerHTML = cpu.per_cpu.map((v, i) => {
            const pct = Math.round(v);
            return `<div class="core-bar"><div class="core-fill" style="height:${pct}%"></div><div class="core-label">${i}</div></div>`;
        }).join('');
    } catch (e) { gaugeEl.innerHTML = `<div class="empty-state">加载失败: ${e.message}</div>`; }
}

// ===== 内存 & 磁盘 =====
async function loadMemory() {
    const vEl = document.getElementById('mem-virtual');
    const sEl = document.getElementById('mem-swap');
    const dEl = document.getElementById('disk-table-wrap');
    loading(vEl); loading(sEl); loading(dEl);
    try {
        const [mem, disks] = await Promise.all([fetchAPI('/api/system/memory'), fetchAPI('/api/system/disks')]);
        const memBar = (title, data) => `
            <div style="margin-bottom:12px"><div style="display:flex;justify-content:space-between;margin-bottom:6px"><span class="text-secondary">${title}</span><span class="mono">${data.used_gb} / ${data.total_gb} GB</span></div><div class="progress-bar"><div class="progress-fill ${getProgressClass(data.percent)}" style="width:${data.percent}%"></div></div></div>
            <div class="info-item"><span class="info-key">可用</span><span class="info-val">${data.available||data.free} GB</span></div>
            <div class="info-item"><span class="info-key">已用</span><span class="info-val">${data.used_gb} GB</span></div>
            <div class="info-item"><span class="info-key">使用率</span><span class="info-val">${data.percent}%</span></div>`;
        vEl.innerHTML = memBar('物理内存', mem.virtual);
        sEl.innerHTML = memBar('交换分区', mem.swap);
        dEl.innerHTML = disks.partitions.length ? `<table><thead><tr><th>设备</th><th>挂载点</th><th>类型</th><th>总量</th><th>已用</th><th>可用</th><th>使用率</th></tr></thead><tbody>${disks.partitions.map(p=>`<tr><td class="mono">${p.device}</td><td class="mono">${p.mountpoint}</td><td>${p.fstype}</td><td class="mono">${p.total_gb}GB</td><td class="mono">${p.used_gb}GB</td><td class="mono">${p.free_gb}GB</td><td><span class="badge ${p.percent>85?'badge-red':p.percent>60?'badge-yellow':'badge-green'}">${p.percent}%</span></td></tr>`).join('')}</tbody></table>` : '<div class="empty-state">无分区</div>';
    } catch (e) { vEl.innerHTML = `<div class="empty-state">加载失败: ${e.message}</div>`; }
}

// ===== 网络接口 =====
async function loadInterfaces() {
    const el = document.getElementById('interfaces-table');
    loading(el);
    try {
        const data = await fetchAPI('/api/system/network-interfaces');
        const names = Object.keys(data.interfaces);
        if (!names.length) { emptyState(el, '无网络接口'); return; }
        el.innerHTML = `<table><thead><tr><th>接口名</th><th>IPv4</th><th>IPv6</th><th>MAC</th><th>发送</th><th>接收</th></tr></thead><tbody>${names.map(name=>{const i=data.interfaces[name];return `<tr><td class="mono text-accent">${name}</td><td class="mono">${(i.ipv4||[]).join(', ')||'—'}</td><td class="mono" style="font-size:11px;max-width:200px;overflow:hidden;text-overflow:ellipsis">${(i.ipv6||[]).slice(0,1).join(', ')||'—'}</td><td class="mono">${i.mac||'—'}</td><td class="mono">${i.bytes_sent_mb?i.bytes_sent_mb+' MB':'—'}</td><td class="mono">${i.bytes_recv_mb?i.bytes_recv_mb+' MB':'—'}</td></tr>`;}).join('')}</tbody></table>`;
    } catch (e) { emptyState(el, '加载失败: ' + e.message); }
}

// ===== 环境变量 =====
async function loadEnv() {
    const el = document.getElementById('env-table');
    loading(el);
    try {
        const data = await fetchAPI('/api/system/env');
        const search = (document.getElementById('env-search').value || '').toLowerCase();
        let entries = Object.entries(data.variables).filter(([k,v]) => !search || k.toLowerCase().includes(search) || String(v).toLowerCase().includes(search));
        entries.sort((a,b) => a[0].localeCompare(b[0]));
        el.innerHTML = `<table><thead><tr><th>变量名</th><th>值</th></tr></thead><tbody>${entries.map(([k,v])=>`<tr><td class="mono text-accent">${esc(k)}</td><td class="mono" style="font-size:12px;word-break:break-all">${esc(v)}</td></tr>`).join('')}</tbody></table>`;
    } catch (e) { emptyState(el, '加载失败: ' + e.message); }
}
document.getElementById('env-search').addEventListener('input', () => loadEnv());

// ===== 电源 & 补丁 =====
async function loadSysPower() {
    const pEl = document.getElementById('power-output');
    const sEl = document.getElementById('sensor-info');
    const hEl = document.getElementById('hotfix-output');
    loading(pEl); loading(sEl); loading(hEl);
    try {
        const [power, sensors, hotfixes] = await Promise.all([
            fetchAPI('/api/system/power'), fetchAPI('/api/system/sensors'), fetchAPI('/api/security/hotfixes')
        ]);
        pEl.textContent = power.active + '\n\n' + power.plans;
        if (Object.keys(sensors).length === 0) {
            sEl.innerHTML = `<div class="info-item"><span class="info-key">状态</span><span class="info-val text-muted">无传感器数据（Windows 通常不支持）</span></div>`;
        } else {
            let html = '';
            if (sensors.battery) html += `<div class="info-item"><span class="info-key">电池</span><span class="info-val">${sensors.battery.percent}% ${sensors.battery.plugged?'(充电中)':'(电池)'}</span></div>`;
            sEl.innerHTML = html || '<div class="info-item"><span class="text-muted">无数据</span></div>';
        }
        hEl.textContent = hotfixes.output;
    } catch (e) { pEl.textContent = '加载失败: ' + e.message; }
}

// ===== Ping =====
async function runPing() {
    const host = document.getElementById('ping-host').value.trim();
    const count = document.getElementById('ping-count').value || 4;
    const el = document.getElementById('ping-output');
    if (!host) { toast('请输入主机名', 'error'); return; }
    loading(el, `正在 Ping ${host}...`);
    try { el.textContent = (await fetchAPI(`/api/network/ping?host=${encodeURIComponent(host)}&count=${count}`)).output; }
    catch (e) { el.textContent = '执行失败: ' + e.message; }
}

// ===== DNS =====
async function runDns() {
    const domain = document.getElementById('dns-domain').value.trim();
    const type = document.getElementById('dns-type').value;
    const el = document.getElementById('dns-output');
    if (!domain) { toast('请输入域名', 'error'); return; }
    loading(el, `解析 ${domain}...`);
    try { el.textContent = (await fetchAPI(`/api/network/dns?domain=${encodeURIComponent(domain)}&record_type=${type}`)).output; }
    catch (e) { el.textContent = '执行失败: ' + e.message; }
}

// ===== Tracert =====
async function runTracert() {
    const host = document.getElementById('tracert-host').value.trim();
    const hops = document.getElementById('tracert-hops').value || 15;
    const el = document.getElementById('tracert-output');
    if (!host) { toast('请输入目标主机', 'error'); return; }
    loading(el, `路由追踪 ${host}（可能需要 30-60 秒）...`);
    try { el.textContent = (await fetchAPI(`/api/network/tracert?host=${encodeURIComponent(host)}&max_hops=${hops}`)).output; }
    catch (e) { el.textContent = '执行失败: ' + e.message; }
}

// ===== Whois =====
async function runWhois() {
    const domain = document.getElementById('whois-domain').value.trim();
    const el = document.getElementById('whois-output');
    if (!domain) { toast('请输入域名', 'error'); return; }
    loading(el, `查询 ${domain}...`);
    try { el.textContent = (await fetchAPI(`/api/network/whois?domain=${encodeURIComponent(domain)}`)).output; }
    catch (e) { el.textContent = '执行失败: ' + e.message; }
}

// ===== 端口检测 =====
async function runPortCheck() {
    const host = document.getElementById('port-host').value.trim();
    const port = document.getElementById('port-port').value;
    const el = document.getElementById('port-result');
    if (!host || !port) { toast('请填写主机和端口', 'error'); return; }
    loading(el, `检测 ${host}:${port}...`);
    try {
        const data = await fetchAPI(`/api/network/port-check?host=${encodeURIComponent(host)}&port=${port}`);
        el.innerHTML = `<div class="card" style="text-align:center;padding:30px"><div style="font-size:14px;color:var(--text-secondary)">${data.host}:${data.port}</div><div style="font-size:36px;font-weight:700" class="${data.open?'text-green':'text-red'}">${data.status}</div><span class="badge ${data.open?'badge-green':'badge-red'}" style="margin-top:8px">${data.open?'端口开放':'端口关闭'}</span></div>`;
    } catch (e) { emptyState(el, '检测失败: ' + e.message); }
}

// ===== 端口扫描（SSE 流式，实时显示扫描进度与已发现端口）=====
let portScanES = null;
async function runPortScan() {
    const host = document.getElementById('scan-host').value.trim();
    const start = parseInt(document.getElementById('scan-start').value);
    const end = parseInt(document.getElementById('scan-end').value);
    const el = document.getElementById('scan-result');
    const statusEl = document.getElementById('scan-status');
    const btn = document.querySelector('#page-portscan .btn-primary');
    if (!host || !start || !end) { toast('请填写完整', 'error'); return; }
    if (portScanES) { portScanES.close(); portScanES = null; }
    setBtnBusy(btn, true);
    statusEl.textContent = `扫描中 ${host}:${start}-${end}（200 线程并发，单次最多 1024 端口）...`;
    const total = Math.min(1024, Math.max(0, end - start + 1));
    taskRunning(el, `扫描 ${host} 端口 ${start}-${end}`, `正在建立连接...`, 0);

    portScanES = new EventSource(`/api/network/scan-stream?host=${encodeURIComponent(host)}&start_port=${start}&end_port=${end}`);
    portScanES.addEventListener('start', e => {
        const d = JSON.parse(e.data);
        renderScanProgress(el, d, host, 0, false);
    });
    portScanES.addEventListener('progress', e => {
        const d = JSON.parse(e.data);
        statusEl.textContent = `扫描中 ${host} · ${d.scanned}/${d.total} · 已发现 ${d.open.length} 个开放端口`;
        renderScanProgress(el, d, host, 0, false);
    });
    portScanES.addEventListener('found', e => {
        const d = JSON.parse(e.data);
        statusEl.textContent = `扫描中 ${host} · ${d.scanned}/${d.total} · 发现开放端口 ${d.port}`;
        renderScanProgress(el, d, host, d.port, true);
    });
    portScanES.addEventListener('done', e => {
        const d = JSON.parse(e.data);
        portScanES.close(); portScanES = null;
        setBtnBusy(btn, false);
        statusEl.textContent = `扫描完成：范围 ${d.range}，发现 ${d.count} 个开放端口`;
        renderScanResult(el, d, host, true);
        toast(`扫描完成，发现 ${d.count} 个开放端口`, d.count ? 'success' : 'info');
    });
    portScanES.onerror = () => {
        portScanES.close(); portScanES = null;
        setBtnBusy(btn, false);
        statusEl.textContent = '扫描连接中断';
    };
}

// 渲染扫描进行中：进度卡 + 实时开放端口列表
function renderScanProgress(el, d, host, newPort, flash) {
    const open = d.open || [];
    const pct = (typeof d.percent === 'number') ? d.percent : 0;
    const openHTML = open.length
        ? `<div class="info-list">${open.map((p, i) => {
            const svc = d.port_info && d.port_info.find(x => x.port === p);
            const svcName = svc ? svc.service : '';
            return `<div class="info-item${flash && i === open.length - 1 ? ' found-flash' : ''}"><span class="info-key">端口 ${p}${svcName ? ' <span class="text-muted" style="font-size:11px">('+svcName+')</span>' : ''}</span><span class="badge badge-green">开放</span><button class="btn btn-sm" style="margin-left:auto" onclick="quickPortCheck('${esc(host)}',${p})">检测</button></div>`;
        }).join('')}</div>`
        : `<div class="empty-state">尚未发现开放端口...</div>`;
    el.innerHTML = `<div class="card task-running">
        <div class="task-running-head"><div class="spinner"></div><div class="task-running-title">扫描中 <span class="mono text-accent" style="font-size:13px">${Math.round(pct)}%</span></div></div>
        <div class="task-running-sub">已扫描 ${d.scanned || 0}/${d.total || 0} · 发现 ${open.length} 个开放端口</div>
        <div class="progress-bar" style="margin:0"><div class="progress-fill accent" style="width:${Math.min(100, Math.max(0, pct))}%"></div></div>
    </div>
    <div class="card" style="margin-top:12px"><div class="card-header"><span class="card-title">开放端口（${open.length}）</span></div>${openHTML}</div>`;
}

// 渲染扫描完成结果
function renderScanResult(el, d, host, done) {
    const open = d.open_ports || [];
    const portInfo = d.port_info || [];
    if (!open.length) {
        el.innerHTML = `<div class="card task-running"><div class="task-running-head"><div class="check-icon pass" style="width:22px;height:22px">✓</div><div class="task-running-title">扫描完成</div></div><div class="task-running-sub">范围 ${d.range}，未发现开放端口</div></div>`;
        return;
    }
    el.innerHTML = `<div class="card task-running">
        <div class="task-running-head"><div class="check-icon pass" style="width:22px;height:22px">✓</div><div class="task-running-title">扫描完成</div></div>
        <div class="task-running-sub">范围 ${d.range} · 发现 ${d.count} 个开放端口</div>
    </div>
    <div class="card" style="margin-top:12px"><div class="card-header"><span class="card-title">开放端口列表（${open.length}）</span></div>
        <div class="info-list">${open.map(p => {
            const svc = portInfo.find(x => x.port === p);
            const svcName = svc ? svc.service : 'Unknown';
            return `<div class="info-item"><span class="info-key">端口 ${p} <span class="text-muted" style="font-size:11px">(${esc(svcName)})</span></span><span class="badge badge-green">开放</span><button class="btn btn-sm" style="margin-left:auto" onclick="quickPortCheck('${esc(host)}',${p})">检测</button></div>`;
        }).join('')}</div>
    </div>`;
}

// 跳转到端口检测并预填
function quickPortCheck(host, port) {
    document.querySelector('[data-page="network"]').click();
    document.querySelector('[data-tab="port"]').click();
    document.getElementById('port-host').value = host;
    document.getElementById('port-port').value = port;
    setTimeout(runPortCheck, 120);
}

// 设置端口扫描范围（常用快捷）
function setScanRange(start, end) {
    document.getElementById('scan-start').value = start;
    document.getElementById('scan-end').value = end;
    toast(`已设置范围 ${start}-${end}`, 'info');
}

// ===== SSL =====
async function runSslCheck() {
    const host = document.getElementById('ssl-host').value.trim();
    const port = document.getElementById('ssl-port').value || 443;
    const el = document.getElementById('ssl-result');
    if (!host) { toast('请输入域名', 'error'); return; }
    loading(el, `检查 ${host}:${port} 的 SSL 证书...`);
    try {
        const data = await fetchAPI(`/api/network/ssl-cert?host=${encodeURIComponent(host)}&port=${port}`);
        if (data.error) { el.innerHTML = `<div class="card"><div class="empty-state">证书获取失败: ${esc(data.error)}</div></div>`; return; }
        el.innerHTML = `<div class="card"><div class="info-list">
            <div class="info-item"><span class="info-key">主机</span><span class="info-val">${data.host}:${data.port}</span></div>
            <div class="info-item"><span class="info-key">主题</span><span class="info-val" style="font-size:12px">${esc(data.subject)}</span></div>
            <div class="info-item"><span class="info-key">签发者</span><span class="info-val" style="font-size:12px">${esc(data.issuer)}</span></div>
            <div class="info-item"><span class="info-key">生效时间</span><span class="info-val">${esc(data.not_before)}</span></div>
            <div class="info-item"><span class="info-key">过期时间</span><span class="info-val">${esc(data.not_after)}</span></div>
            ${data.serial?`<div class="info-item"><span class="info-key">序列号</span><span class="info-val" style="font-size:11px">${esc(data.serial)}</span></div>`:''}
            ${data.version?`<div class="info-item"><span class="info-key">版本</span><span class="info-val">${esc(data.version)}</span></div>`:''}
        </div></div>`;
    } catch (e) { emptyState(el, '检查失败: ' + e.message); }
}

// ===== HTTP 头 =====
async function runHttpCheck() {
    const url = document.getElementById('http-url').value.trim();
    const el = document.getElementById('http-result');
    if (!url) { toast('请输入URL', 'error'); return; }
    loading(el, `检测 HTTP 头...`);
    try {
        const data = await fetchAPI(`/api/network/http-headers?url=${encodeURIComponent(url)}`);
        if (data.error) { el.innerHTML = `<div class="card"><div class="empty-state">检测失败: ${esc(data.error)}</div></div>`; return; }
        let rows = Object.entries(data.headers).map(([k,v])=>`<div class="info-item"><span class="info-key">${esc(k)}</span><span class="info-val" style="font-size:12px">${esc(v)}</span></div>`).join('');
        el.innerHTML = `<div class="card"><div class="info-list">
            <div class="info-item"><span class="info-key">URL</span><span class="info-val" style="font-size:12px">${esc(data.final_url||data.url)}</span></div>
            <div class="info-item"><span class="info-key">状态码</span><span class="info-val"><span class="badge ${data.status<400?'badge-green':'badge-red'}">${data.status} ${esc(data.reason||'')}</span></span></div>
            ${rows}
        </div></div>`;
    } catch (e) { emptyState(el, '检测失败: ' + e.message); }
}

// ===== Wi-Fi =====
async function loadWifi() {
    const iEl = document.getElementById('wifi-iface');
    const pEl = document.getElementById('wifi-profiles');
    loading(iEl, '获取 Wi-Fi 接口...'); loading(pEl, '获取 Wi-Fi 配置...');
    try {
        const data = await fetchAPI('/api/network/wifi');
        iEl.textContent = data.interfaces || '无 Wi-Fi 接口';
        pEl.textContent = data.profiles || '无配置文件';
    } catch (e) { iEl.textContent = '加载失败: ' + e.message; }
}

// ===== 子网计算 =====
async function runSubnetCalc() {
    const ip = document.getElementById('subnet-ip').value.trim();
    const prefix = document.getElementById('subnet-prefix').value;
    const el = document.getElementById('subnet-result');
    if (!ip || !prefix) { toast('请输入 IP 和前缀', 'error'); return; }
    loading(el, '计算中...');
    try {
        const data = await fetchAPI(`/api/network/subnet?ip=${encodeURIComponent(ip)}&prefix=${prefix}`);
        if (data.error) { el.innerHTML = `<div class="card"><div class="empty-state">计算失败: ${esc(data.error)}</div></div>`; return; }
        let hostsHtml = '';
        if (data.hosts) {
            hostsHtml = `<div class="card" style="margin-top:16px"><div class="card-header"><span class="card-title">主机地址列表（${data.hosts.length} 个）</span></div><div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:4px;padding:8px">${data.hosts.map(h=>`<span class="mono text-secondary" style="font-size:12px">${h}</span>`).join('')}</div></div>`;
        }
        el.innerHTML = `<div class="card"><div class="info-list">
            <div class="info-item"><span class="info-key">输入</span><span class="info-val mono">${data.input}</span></div>
            <div class="info-item"><span class="info-key">类型</span><span class="info-val">${data.version}</span></div>
            <div class="info-item"><span class="info-key">网络地址</span><span class="info-val mono">${data.network}</span></div>
            <div class="info-item"><span class="info-key">广播地址</span><span class="info-val mono">${data.broadcast}</span></div>
            <div class="info-item"><span class="info-key">子网掩码</span><span class="info-val mono">${data.netmask}</span></div>
            <div class="info-item"><span class="info-key">反掩码</span><span class="info-val mono">${data.hostmask}</span></div>
            <div class="info-item"><span class="info-key">前缀长度</span><span class="info-val mono">/${data.prefix}</span></div>
            <div class="info-item"><span class="info-key">地址总数</span><span class="info-val mono">${fmtNum(data.num_addresses)}</span></div>
            <div class="info-item"><span class="info-key">可用主机数</span><span class="info-val mono text-accent">${fmtNum(data.num_hosts)}</span></div>
        </div></div>${hostsHtml}`;
    } catch (e) { emptyState(el, '计算失败: ' + e.message); }
}

// ===== IP 配置 / 路由 / ARP =====
async function runIpconfig() { const el=document.getElementById('ipconfig-output'); loading(el); try{el.textContent=(await fetchAPI('/api/network/ipconfig')).output;}catch(e){el.textContent='失败:'+e.message;} }
async function runRoute() { const el=document.getElementById('route-output'); loading(el); try{el.textContent=(await fetchAPI('/api/network/route')).output;}catch(e){el.textContent='失败:'+e.message;} }
async function runArp() { const el=document.getElementById('arp-output'); loading(el); try{el.textContent=(await fetchAPI('/api/network/arp')).output;}catch(e){el.textContent='失败:'+e.message;} }

// ===== 网络连接 =====
async function loadConnections() {
    const el = document.getElementById('conn-table');
    const countEl = document.getElementById('conn-count');
    loading(el);
    try {
        const data = await fetchAPI('/api/network/connections');
        countEl.textContent = `共 ${data.total} 个连接`;
        if (data.error) { emptyState(el, data.error); return; }
        if (!data.connections.length) { emptyState(el, '无连接'); return; }
        el.innerHTML = `<table><thead><tr><th>本地地址</th><th>远程地址</th><th>状态</th><th>类型</th><th>PID</th></tr></thead><tbody>${data.connections.map(c=>{const b=c.status==='ESTABLISHED'?'badge-green':c.status==='LISTEN'?'badge-blue':c.status==='TIME_WAIT'?'badge-yellow':'badge-gray';return `<tr><td class="mono">${c.laddr}</td><td class="mono">${c.raddr}</td><td><span class="badge ${b}">${c.status}</span></td><td class="text-secondary">${c.type}</td><td class="mono">${c.pid}</td></tr>`;}).join('')}</tbody></table>`;
    } catch (e) { emptyState(el, '加载失败: ' + e.message); }
}

// ===== 进程管理 =====
async function loadProcesses() {
    const el = document.getElementById('proc-table');
    const countEl = document.getElementById('proc-count');
    const sortBy = document.getElementById('proc-sort').value;
    loading(el);
    try {
        const data = await fetchAPI(`/api/processes?sort_by=${sortBy}`);
        countEl.textContent = `共 ${data.total} 个进程（显示前 100）`;
        el.innerHTML = `<table><thead><tr><th>PID</th><th>进程名</th><th>CPU%</th><th>内存%</th><th>内存(MB)</th><th>用户</th><th>状态</th><th>启动时间</th><th>操作</th></tr></thead><tbody>${data.processes.map(p=>`<tr><td class="mono">${p.pid}</td><td>${esc(p.name)}</td><td class="mono ${p.cpu_percent>50?'text-red':p.cpu_percent>20?'text-yellow':''}">${p.cpu_percent}</td><td class="mono ${p.memory_percent>10?'text-red':p.memory_percent>5?'text-yellow':''}">${p.memory_percent}</td><td class="mono">${p.memory_mb}</td><td class="text-secondary" style="font-size:12px">${esc(p.username)}</td><td><span class="badge ${p.status==='running'?'badge-green':'badge-gray'}">${p.status}</span></td><td class="mono text-secondary">${p.create_time}</td><td><button class="btn btn-sm btn-danger" onclick="killProcess(${p.pid}, '${esc(p.name).replace(/'/g,"\\'")}')">结束</button></td></tr>`).join('')}</tbody></table>`;
    } catch (e) { emptyState(el, '加载失败: ' + e.message); }
}

async function killProcess(pid, name) {
    if (!confirm(`确定要结束进程 "${name}" (PID: ${pid}) 吗？`)) return;
    try {
        const data = await postAPI(`/api/processes/${pid}/kill`);
        if (data.success) { toast(data.message, 'success'); loadProcesses(); } else { toast(data.message, 'error'); }
    } catch (e) { toast('操作失败: ' + e.message, 'error'); }
}

document.getElementById('proc-sort').addEventListener('change', () => loadProcesses());

// ===== 服务管理 =====
async function loadServices() {
    const el = document.getElementById('svc-table');
    const countEl = document.getElementById('svc-count');
    const state = document.getElementById('svc-state').value;
    const search = document.getElementById('svc-search').value.toLowerCase().trim();
    loading(el);
    try {
        const data = await fetchAPI(`/api/services?state=${state}`);
        let services = data.services;
        if (search) services = services.filter(s => s.name.toLowerCase().includes(search) || s.display_name.toLowerCase().includes(search));
        countEl.textContent = `共 ${services.length} 个服务`;
        if (data.error) { emptyState(el, data.error); return; }
        if (!services.length) { emptyState(el, '无匹配服务'); return; }
        el.innerHTML = `<table><thead><tr><th>服务名</th><th>显示名称</th><th>状态</th><th>启动类型</th><th>PID</th><th>操作</th></tr></thead><tbody>${services.map(s=>`<tr><td class="mono text-accent" style="font-size:12px">${esc(s.name)}</td><td style="font-size:12px">${esc(s.display_name)}</td><td><span class="badge ${s.status==='running'?'badge-green':'badge-gray'}">${s.status}</span></td><td class="text-secondary">${s.start_type}</td><td class="mono">${s.pid}</td><td>${s.status==='running'?`<button class="btn btn-sm btn-danger" onclick="stopService('${esc(s.name)}')">停止</button>`:`<button class="btn btn-sm btn-primary" onclick="startService('${esc(s.name)}')">启动</button>`}</td></tr>`).join('')}</tbody></table>`;
    } catch (e) { emptyState(el, '加载失败: ' + e.message); }
}

document.getElementById('svc-search').addEventListener('input', () => loadServices());
document.getElementById('svc-state').addEventListener('change', () => loadServices());

async function startService(name) {
    try { await postAPI(`/api/services/${encodeURIComponent(name)}/start`); toast(`服务 ${name} 启动指令已发送`, 'success'); setTimeout(loadServices, 1000); }
    catch (e) { toast('操作失败: ' + e.message, 'error'); }
}
async function stopService(name) {
    if (!confirm(`确定要停止服务 "${name}" 吗？`)) return;
    try { await postAPI(`/api/services/${encodeURIComponent(name)}/stop`); toast(`服务 ${name} 停止指令已发送`, 'success'); setTimeout(loadServices, 1000); }
    catch (e) { toast('操作失败: ' + e.message, 'error'); }
}

// ===== 计划任务 =====
async function loadTasks() {
    const el = document.getElementById('task-table');
    const countEl = document.getElementById('task-count');
    loading(el);
    try {
        const data = await fetchAPI('/api/security/tasks');
        let tasks = data.tasks;
        const search = document.getElementById('task-search').value.toLowerCase().trim();
        if (search) tasks = tasks.filter(t => (t.name||'').toLowerCase().includes(search));
        countEl.textContent = `共 ${tasks.length} 个任务`;
        if (!tasks.length) { emptyState(el, '无任务'); return; }
        el.innerHTML = `<table><thead><tr><th>任务名</th><th>下次运行</th><th>上次运行</th><th>状态</th></tr></thead><tbody>${tasks.slice(0,200).map(t=>`<tr><td class="mono text-accent" style="font-size:12px">${esc(t.name||'')}</td><td class="mono text-secondary" style="font-size:12px">${esc(t.next||'—')}</td><td class="mono text-secondary" style="font-size:12px">${esc(t.lastrun||'—')}</td><td><span class="badge badge-gray">${esc(t.status||'—')}</span></td></tr>`).join('')}</tbody></table>`;
    } catch (e) { emptyState(el, '加载失败: ' + e.message); }
}
document.getElementById('task-search').addEventListener('input', () => loadTasks());

// ===== 命令终端 =====
async function runTerminal() {
    const cmd = document.getElementById('term-cmd').value.trim();
    const el = document.getElementById('term-output');
    if (!cmd) { toast('请输入命令', 'error'); return; }
    loading(el, `执行: ${cmd}...`);
    try {
        const data = await postAPI(`/api/terminal/run?cmd=${encodeURIComponent(cmd)}`);
        const prefix = data.blocked ? '[已拦截] ' : '';
        el.textContent = `${prefix}> ${esc(data.cmd)}\n\n${data.output}`;
    } catch (e) { el.textContent = '执行失败: ' + e.message; }
}

function quickCmd(cmd) {
    document.getElementById('term-cmd').value = cmd;
    runTerminal();
}

// ===== 文件哈希 =====
async function runHash() {
    const path = document.getElementById('hash-path').value.trim();
    const algo = document.getElementById('hash-algo').value;
    const el = document.getElementById('hash-result');
    if (!path) { toast('请输入文件路径', 'error'); return; }
    loading(el, `计算 ${algo} 哈希...`);
    try {
        const data = await fetchAPI(`/api/files/hash?path=${encodeURIComponent(path)}&algo=${algo}`);
        if (data.error) { el.innerHTML = `<div class="card"><div class="empty-state">${esc(data.error)}</div></div>`; return; }
        el.innerHTML = `<div class="card"><div class="info-list">
            <div class="info-item"><span class="info-key">文件</span><span class="info-val" style="font-size:12px;word-break:break-all">${esc(data.path)}</span></div>
            <div class="info-item"><span class="info-key">算法</span><span class="info-val">${data.algorithm.toUpperCase()}</span></div>
            <div class="info-item"><span class="info-key">大小</span><span class="info-val">${data.size_mb} MB</span></div>
            <div class="info-item"><span class="info-key">哈希值</span><span class="info-val mono" style="font-size:12px;word-break:break-all">${esc(data.hash)}</span></div>
        </div></div>`;
    } catch (e) { emptyState(el, '计算失败: ' + e.message); }
}

// ===== 大文件查找 =====
async function runLargeFiles() {
    const dir = document.getElementById('lf-dir').value.trim();
    const minSize = document.getElementById('lf-min').value || 100;
    const el = document.getElementById('lf-table');
    const countEl = document.getElementById('lf-count');
    if (!dir) { toast('请输入目录', 'error'); return; }
    const btn = document.querySelector('#page-largefiles .btn-primary');
    setBtnBusy(btn, true);
    taskRunning(el, '扫描大文件', '正在遍历目录 ' + dir);
    try {
        const data = await fetchAPI(`/api/files/large?dir=${encodeURIComponent(dir)}&min_size_mb=${minSize}`);
        if (data.error) { emptyState(el, data.error); countEl.textContent=''; return; }
        countEl.textContent = `${data.count} 个大文件`;
        if (!data.files.length) { emptyState(el, `未找到大于 ${minSize}MB 的文件`); return; }
        el.innerHTML = `<table><thead><tr><th>路径</th><th>大小</th></tr></thead><tbody>${data.files.map(f=>`<tr><td class="mono" style="font-size:12px;word-break:break-all">${esc(f.path)}</td><td class="mono">${f.size_mb} MB (${f.size_gb} GB)</td></tr>`).join('')}</tbody></table>`;
    } catch (e) { emptyState(el, '查找失败: ' + e.message); }
    finally { setBtnBusy(btn, false); }
}

// ===== 磁盘分析 =====
async function runDiskAnalyze() {
    const dir = document.getElementById('da-dir').value.trim();
    const sumEl = document.getElementById('da-summary');
    const tblEl = document.getElementById('da-table');
    if (!dir) { toast('请输入目录', 'error'); return; }
    const btn = document.querySelector('#page-diskanalyze .btn-primary');
    setBtnBusy(btn, true);
    taskRunning(sumEl, '磁盘分析', '正在分析目录 ' + dir);
    tblEl.innerHTML = '';
    try {
        const data = await fetchAPI(`/api/files/analyze?dir=${encodeURIComponent(dir)}`);
        if (data.error) { sumEl.innerHTML=`<div class="info-item"><span class="text-muted">${esc(data.error)}</span></div>`; return; }
        sumEl.innerHTML = `
            <div class="info-item"><span class="info-key">目录</span><span class="info-val" style="font-size:12px">${esc(data.dir)}</span></div>
            <div class="info-item"><span class="info-key">总占用</span><span class="info-val text-accent">${data.total_size_gb} GB</span></div>
            <div class="info-item"><span class="info-key">文件总数</span><span class="info-val">${fmtNum(data.total_files)}</span></div>
            <div class="info-item"><span class="info-key">扫描目录</span><span class="info-val">${fmtNum(data.scanned_dirs)}</span></div>
        `;
        tblEl.innerHTML = `<table><thead><tr><th>目录</th><th>占用</th></tr></thead><tbody>${data.top_dirs.map(d=>`<tr><td class="mono" style="font-size:11px;word-break:break-all">${esc(d.path)}</td><td class="mono">${d.size_mb} MB</td></tr>`).join('')}</tbody></table>`;
    } catch (e) { sumEl.innerHTML = `<div class="info-item"><span class="text-muted">分析失败</span></div>`; }
    finally { setBtnBusy(btn, false); }
}

// ===== 重复文件 =====
async function runDuplicates() {
    const dir = document.getElementById('dup-dir').value.trim();
    const el = document.getElementById('dup-result');
    const statusEl = document.getElementById('dup-status');
    if (!dir) { toast('请输入目录', 'error'); return; }
    const btn = document.querySelector('#page-duplicates .btn-primary');
    setBtnBusy(btn, true);
    statusEl.textContent = '检测中（按内容哈希对比，可能耗时）...';
    taskRunning(el, '检测重复文件', '正在计算文件哈希，可能耗时...');
    try {
        const data = await fetchAPI(`/api/files/duplicates?dir=${encodeURIComponent(dir)}`);
        if (data.error) { el.innerHTML=`<div class="card"><div class="empty-state">${esc(data.error)}</div></div>`; statusEl.textContent=''; return; }
        statusEl.textContent = `扫描 ${data.scanned} 个文件，发现 ${data.duplicate_groups} 组重复，共 ${data.total_dup_mb} MB 可清理`;
        if (!data.duplicates.length) { el.innerHTML = '<div class="card"><div class="empty-state">未发现重复文件</div></div>'; return; }
        el.innerHTML = data.duplicates.map((g,i)=>`<div class="card" style="margin-bottom:12px"><div class="card-header"><span class="card-title">第 ${i+1} 组 · ${g.size_mb} MB/个</span></div><div class="info-list">${g.files.map(f=>`<div class="info-item"><span class="info-key" style="font-size:11px">${esc(f)}</span></div>`).join('')}</div></div>`).join('');
    } catch (e) { emptyState(el, '检测失败: ' + e.message); }
    finally { setBtnBusy(btn, false); }
}

// ===== 清理临时 =====
async function runCleanTemp() {
    const el = document.getElementById('clean-result');
    if (!confirm('确定要清理临时文件吗？')) return;
    loading(el, '清理中...');
    try {
        const data = await postAPI('/api/files/clean-temp');
        el.innerHTML = `<div class="card" style="text-align:center;padding:30px"><div style="font-size:36px;font-weight:700" class="text-green">${data.freed_mb} MB</div><div style="color:var(--text-secondary);margin-top:8px">${esc(data.message)}</div><div class="text-muted" style="margin-top:8px;font-size:12px">${data.errors} 个文件因占用跳过</div></div>`;
        toast(data.message, 'success');
    } catch (e) { emptyState(el, '清理失败: ' + e.message); }
}

// ===== 安全中心 =====
async function loadSecurity() {
    const el = document.getElementById('security-cards');
    const dEl = document.getElementById('defender-output');
    const pEl = document.getElementById('policy-output');
    el.innerHTML = `
        <div class="card"><div class="card-header"><span class="card-title">防火墙状态</span></div><div id="sec-firewall"><div class="loading-overlay"><div class="spinner"></div></div></div></div>
        <div class="card"><div class="card-header"><span class="card-title">本地用户</span></div><div id="sec-users"><div class="loading-overlay"><div class="spinner"></div></div></div></div>
        <div class="card"><div class="card-header"><span class="card-title">启动项</span></div><div id="sec-startup"><div class="loading-overlay"><div class="spinner"></div></div></div></div>`;
    const fwEl=document.getElementById('sec-firewall'), userEl=document.getElementById('sec-users'), startEl=document.getElementById('sec-startup');
    loading(dEl); loading(pEl);
    try { const fw=await fetchAPI('/api/security/firewall');
        if(fw.profiles&&!fw.profiles.raw){fwEl.innerHTML=Object.entries(fw.profiles).map(([name,info])=>{const st=info.status||'未知';const on=st.toLowerCase().includes('on')||st.includes('启用');return `<div class="info-item"><span class="info-key">${name}</span><span class="badge ${on?'badge-green':'badge-red'}">${st}</span></div>`;}).join('');}else{fwEl.innerHTML=`<pre class="terminal" style="max-height:200px">${esc(fw.raw)}</pre>`;}
    } catch(e){ fwEl.innerHTML='<div class="empty-state">加载失败</div>'; }
    try { const u=await fetchAPI('/api/security/users'); userEl.innerHTML=u.users.length?u.users.map(x=>`<div class="info-item"><span class="info-key">${esc(x)}</span><span class="badge badge-blue">用户</span></div>`).join(''):'<div class="empty-state">无</div>'; } catch(e){ userEl.innerHTML='<div class="empty-state">加载失败</div>'; }
    try { const s=await fetchAPI('/api/security/startup'); startEl.innerHTML=s.items.length?s.items.map(x=>`<div class="info-item"><span class="info-key">${esc(x.name)}<br><span class="text-muted" style="font-size:11px">${esc(x.location)}</span></span><span class="info-val" style="font-size:11px;max-width:60%;word-break:break-all">${esc(x.command)}</span></div>`).join(''):'<div class="empty-state">无启动项</div>'; } catch(e){ startEl.innerHTML='<div class="empty-state">加载失败</div>'; }
    try { dEl.textContent=(await fetchAPI('/api/security/defender')).output||'无 Defender 数据'; } catch(e){ dEl.textContent='加载失败'; }
    try { pEl.textContent=(await fetchAPI('/api/security/password-policy')).output; } catch(e){ pEl.textContent='加载失败'; }
}

// ===== 事件日志 =====
async function loadEventLog() {
    const log = document.getElementById('log-type').value;
    const count = document.getElementById('log-count').value || 20;
    const el = document.getElementById('eventlog-output');
    loading(el, `读取 ${log} 日志...`);
    try { el.textContent = (await fetchAPI(`/api/security/eventlog?log=${log}&count=${count}`)).output; }
    catch (e) { el.textContent = '加载失败: ' + e.message; }
}

// ===== 已装程序 =====
async function loadPrograms() {
    const el = document.getElementById('programs-output');
    const countEl = document.getElementById('prog-count');
    loading(el, '扫描已安装程序...');
    try {
        const data = await fetchAPI('/api/security/programs');
        countEl.textContent = `共 ${data.count} 个程序`;
        el.textContent = data.raw || '无数据';
    } catch (e) { el.textContent = '扫描失败: ' + e.message; }
}

// ===== 共享文件夹 =====
async function loadShares() {
    const el = document.getElementById('shares-output');
    loading(el, '获取共享文件夹...');
    try { el.textContent = (await fetchAPI('/api/security/shares')).output; }
    catch (e) { el.textContent = '加载失败: ' + e.message; }
}

// ===== 风险等级配色 =====
const RISK_COLOR = {
    '极高': 'badge-red', '高危': 'badge-red',
    '高': 'badge-red', '中': 'badge-yellow', '中危': 'badge-yellow',
    '低': 'badge-blue', '低危': 'badge-blue', '信息': 'badge-green',
    '安全': 'badge-green', '未知': 'badge-gray', 'warn': 'badge-gray'
};
function riskBadge(level) {
    const cls = RISK_COLOR[level] || 'badge-gray';
    return `<span class="badge ${cls}">${esc(level)}</span>`;
}

// 导出当前页面结果为 HTML 报告（去除按钮等交互元素）
function exportReport(page) {
    const meta = {
        assessment: {file:'安全评估报告.html', title:'安全评估报告', id:'assess-result'},
        privesc: {file:'提权路径扫描报告.html', title:'提权路径扫描报告', id:'privesc-result'},
        persistence: {file:'持久化检查报告.html', title:'持久化检查报告', id:'persist-result'},
        weakcred: {file:'弱口令审计报告.html', title:'弱口令审计报告', id:'weak-result'},
        antiforen: {file:'反取证检测报告.html', title:'反取证检测报告', id:'antiforen-result'}
    }[page];
    const wrap = document.getElementById(meta.id);
    if (!wrap) { toast('无可导出内容', 'error'); return; }
    const clone = wrap.cloneNode(true);
    clone.querySelectorAll('.report-bar, button').forEach(n => n.remove());
    exportHTML(meta.file, meta.title, clone.innerHTML);
}

// ===== 安全评估（评分卡 + 检查项 + 攻击面） =====
async function runAssessment() {
    const wrap = document.getElementById('assess-result');
    const status = document.getElementById('assess-status');
    const btn = document.querySelector('#page-assessment .btn-primary');
    setBtnBusy(btn, true);
    taskRunning(wrap, '安全评估', '正在执行基线检查与攻击面分析...');
    status.textContent = '';
    try {
        const [bl, as] = await Promise.all([
            fetchAPI('/api/security/baseline'),
            fetchAPI('/api/security/attack-surface')
        ]);
        const scoreColor = bl.score >= 85 ? '#22c55e' : bl.score >= 60 ? '#eab308' : '#ef4444';
        const checksHTML = bl.checks.map(c => {
            const icon = c.pass === true ? '✓' : c.pass === false ? '✗' : '?';
            const iconCls = c.pass === true ? 'pass' : c.pass === false ? 'fail' : 'warn';
            return `<div class="check-row">
                <div class="check-icon ${iconCls}">${icon}</div>
                <div class="check-body">
                    <div class="check-title">${esc(c.name)} <span class="text-muted" style="font-size:11px">[${esc(c.category)}]</span> ${riskBadge(c.severity)}</div>
                    <div class="text-secondary" style="font-size:12px;margin-top:2px">${esc(c.detail)}</div>
                </div>
            </div>`;
        }).join('');
        const listenHTML = as.listening.length ? as.listening.slice(0, 50).map(l => `
            <tr>
                <td class="mono">${esc(l.address)}:${l.port}</td>
                <td>${l.exposed ? '<span class="badge badge-red">对外</span>' : '<span class="badge badge-green">本地</span>'}</td>
                <td class="mono">${esc(l.process)}</td>
                <td class="mono">${l.pid || '—'}</td>
            </tr>`).join('') : '<tr><td colspan="4" class="empty-state">无监听</td></tr>';
        const riskyHTML = as.risky_services.length ? as.risky_services.map(r => `
            <tr>
                <td class="mono">${r.port}</td>
                <td>${esc(r.service)}</td>
                <td>${r.exposed ? '<span class="badge badge-red">对外</span>' : '<span class="badge badge-gray">本地</span>'}</td>
                <td class="mono">${esc(r.process)}</td>
                <td>${riskBadge(r.risk)}</td>
            </tr>`).join('') : '<tr><td colspan="5" class="empty-state">无高风险服务</td></tr>';
        const extHTML = as.external_connections.length ? as.external_connections.slice(0, 30).map(c => `
            <tr>
                <td class="mono">${esc(c.remote)}</td>
                <td class="mono">${esc(c.process)}</td>
                <td class="mono">${c.pid || '—'}</td>
            </tr>`).join('') : '<tr><td colspan="3" class="empty-state">无外部连接</td></tr>';

        wrap.innerHTML = `
            <div class="report-bar"><span class="text-secondary">评估完成</span><button class="btn btn-sm btn-primary" onclick="exportReport('assessment')">导出报告</button></div>
            <div class="grid grid-3">
                <div class="card assess-score-card">
                    <div class="card-header"><span class="card-title">综合评分</span></div>
                    <div class="score-ring" style="--score-color:${scoreColor}">
                        <svg viewBox="0 0 100 100"><circle class="bg" cx="50" cy="50" r="42"/><circle class="fg" cx="50" cy="50" r="42" stroke="${scoreColor}" stroke-dasharray="${2*Math.PI*42}" stroke-dashoffset="${2*Math.PI*42 - bl.score/100*2*Math.PI*42}"/></svg>
                        <div class="score-text"><div class="score-num" style="color:${scoreColor}">${bl.score}</div><div class="score-label">${esc(bl.risk_level)}</div></div>
                    </div>
                    <div class="info-list" style="margin-top:12px">
                        <div class="info-item"><span class="info-key">通过</span><span class="badge badge-green">${bl.passed}/${bl.total}</span></div>
                        <div class="info-item"><span class="info-key">失败</span><span class="badge badge-red">${bl.failed}</span></div>
                        <div class="info-item"><span class="info-key">高风险项</span><span class="badge badge-red">${bl.high_issues}</span></div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header"><span class="card-title">攻击面概览</span></div>
                    <div class="info-list">
                        <div class="info-item"><span class="info-key">监听端口</span><span class="info-val mono">${as.listening_total}</span></div>
                        <div class="info-item"><span class="info-key">对外暴露</span><span class="badge badge-red">${as.exposed_count}</span></div>
                        <div class="info-item"><span class="info-key">外部连接</span><span class="info-val mono">${as.external_count}</span></div>
                        <div class="info-item"><span class="info-key">高风险服务</span><span class="badge badge-red">${as.risky_services.length}</span></div>
                        <div class="info-item"><span class="info-key">暴露等级</span>${riskBadge(as.exposure_level)}</div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header"><span class="card-title">关键风险项</span></div>
                    <div class="info-list">
                        ${bl.checks.filter(c => c.severity === 'high' && c.pass === false).slice(0, 6).map(c => `
                            <div class="info-item"><span class="info-key" style="max-width:70%">${esc(c.name)}</span><span class="badge badge-red">${esc(c.category)}</span></div>
                        `).join('') || '<div class="empty-state">无高风险项</div>'}
                    </div>
                </div>
            </div>
            <div class="card" style="margin-top:16px">
                <div class="card-header"><span class="card-title">安全基线检查项</span></div>
                <div class="check-list">${checksHTML}</div>
            </div>
            <div class="card" style="margin-top:16px">
                <div class="card-header"><span class="card-title">监听端口</span><span class="text-secondary">对外 ${as.exposed_count} / 共 ${as.listening_total}</span></div>
                <div class="table-wrap"><table>
                    <thead><tr><th>本地地址</th><th>暴露</th><th>进程</th><th>PID</th></tr></thead>
                    <tbody>${listenHTML}</tbody>
                </table></div>
            </div>
            <div class="card" style="margin-top:16px">
                <div class="card-header"><span class="card-title">高风险服务</span><span class="badge badge-red">${as.risky_services.length}</span></div>
                <div class="table-wrap"><table>
                    <thead><tr><th>端口</th><th>服务</th><th>暴露</th><th>进程</th><th>风险</th></tr></thead>
                    <tbody>${riskyHTML}</tbody>
                </table></div>
            </div>
            <div class="card" style="margin-top:16px">
                <div class="card-header"><span class="card-title">外部连接</span><span class="badge badge-yellow">${as.external_count}</span></div>
                <div class="table-wrap"><table>
                    <thead><tr><th>远端</th><th>进程</th><th>PID</th></tr></thead>
                    <tbody>${extHTML}</tbody>
                </table></div>
            </div>
        `;
        status.textContent = `评估完成：${bl.risk_level} / 暴露 ${as.exposure_level}`;
    } catch (e) {
        wrap.innerHTML = `<div class="empty-state">评估失败：${esc(e.message)}</div>`;
        status.textContent = '失败';
    }
    finally { setBtnBusy(btn, false); }
}

// ===== 提权路径扫描 =====
async function runPrivesc() {
    const wrap = document.getElementById('privesc-result');
    const status = document.getElementById('privesc-status');
    const btn = document.querySelector('#page-privesc .btn-primary');
    setBtnBusy(btn, true);
    taskRunning(wrap, '提权路径扫描', '扫描可写目录/未签名服务/令牌特权/LOLBins...');
    status.textContent = '';
    try {
        const data = await fetchAPI('/api/pentest/privesc');
        const findHTML = data.findings.map(f => `
            <div class="check-row">
                <div class="check-icon ${f.exploitable===true?'fail':f.exploitable===false?'pass':'warn'}">${f.exploitable===true?'!':f.exploitable===false?'✓':'?'}</div>
                <div class="check-body">
                    <div class="check-title">${esc(f.name)} <span class="text-muted" style="font-size:11px">[${esc(f.category)}]</span> ${riskBadge(f.severity)}</div>
                    <div class="text-secondary" style="font-size:12px;margin-top:2px">${esc(f.detail)}</div>
                    ${f.remediation && f.remediation!=='—' ? `<div class="text-muted" style="font-size:11px;margin-top:4px">修复：${esc(f.remediation)}</div>` : ''}
                </div>
            </div>`).join('');
        const unsignedHTML = data.unsigned_services.length ? data.unsigned_services.slice(0,20).map(s => `
            <tr><td class="mono">${esc(s.name)}</td><td class="mono" style="max-width:50%;word-break:break-all">${esc(s.path)}</td><td><span class="badge badge-yellow">${esc(s.signature)}</span></td></tr>
        `).join('') : '<tr><td colspan="3" class="empty-state">无未签名服务</td></tr>';
        const toolsHTML = data.found_tools.length ? data.found_tools.map(t => `
            <div class="info-item"><span class="info-key mono">${esc(t.tool)}</span><span class="info-val" style="font-size:12px">${esc(t.desc)}</span></div>
        `).join('') : '<div class="empty-state">无</div>';
        wrap.innerHTML = `
            <div class="report-bar"><span class="text-secondary">扫描完成</span><button class="btn btn-sm btn-primary" onclick="exportReport('privesc')">导出报告</button></div>
            <div class="grid grid-2">
                <div class="card"><div class="card-header"><span class="card-title">扫描结果</span>${riskBadge(data.risk_level)}</div>
                    <div class="info-list">
                        <div class="info-item"><span class="info-key">总检测项</span><span class="info-val mono">${data.total_findings}</span></div>
                        <div class="info-item"><span class="info-key">可利用</span><span class="badge badge-red">${data.exploitable}</span></div>
                    </div>
                </div>
                <div class="card"><div class="card-header"><span class="card-title">LOLBins 工具</span></div><div class="info-list">${toolsHTML}</div></div>
            </div>
            <div class="card" style="margin-top:16px"><div class="card-header"><span class="card-title">提权向量详情</span></div><div class="check-list">${findHTML}</div></div>
            <div class="card" style="margin-top:16px"><div class="card-header"><span class="card-title">未签名服务（前 20）</span></div>
                <div class="table-wrap"><table>
                    <thead><tr><th>服务名</th><th>可执行路径</th><th>签名状态</th></tr></thead>
                    <tbody>${unsignedHTML}</tbody>
                </table></div>
            </div>`;
        status.textContent = `完成：${data.risk_level}，可利用 ${data.exploitable} 项`;
    } catch (e) {
        wrap.innerHTML = `<div class="empty-state">扫描失败：${esc(e.message)}</div>`;
        status.textContent = '失败';
    }
    finally { setBtnBusy(btn, false); }
}

// ===== 持久化检查 =====
async function runPersistence() {
    const wrap = document.getElementById('persist-result');
    const status = document.getElementById('persist-status');
    const btn = document.querySelector('#page-persistence .btn-primary');
    setBtnBusy(btn, true);
    taskRunning(wrap, '持久化检查', '扫描注册表/任务/服务/WMI/IFEO...');
    status.textContent = '';
    try {
        const data = await fetchAPI('/api/pentest/persistence');
        const grouped = {};
        data.items.forEach(it => { (grouped[it.type] = grouped[it.type] || []).push(it); });
        const cards = Object.keys(grouped).map(type => {
            const list = grouped[type];
            const isRisky = type === 'WMI 事件订阅' || type === 'IFEO 调试器劫持';
            const rows = list.slice(0, 30).map(it => `
                <tr>
                    <td class="mono" style="max-width:40%;word-break:break-all">${esc(it.item)}</td>
                    <td class="mono" style="max-width:50%;word-break:break-all">${esc(it.value)}</td>
                    <td class="mono" style="font-size:11px">${esc(it.key)}</td>
                </tr>`).join('');
            return `<div class="card" style="margin-top:12px">
                <div class="card-header"><span class="card-title">${esc(type)}</span>
                    <span class="badge ${isRisky?'badge-red':'badge-blue'}">${list.length}</span>
                </div>
                <div class="table-wrap"><table>
                    <thead><tr><th>名称</th><th>值/路径</th><th>来源</th></tr></thead>
                    <tbody>${rows}</tbody>
                </table></div>
            </div>`;
        }).join('');
        wrap.innerHTML = `
            <div class="report-bar"><span class="text-secondary">扫描完成</span><button class="btn btn-sm btn-primary" onclick="exportReport('persistence')">导出报告</button></div>
            <div class="card">
                <div class="card-header"><span class="card-title">持久化点汇总</span>${riskBadge(data.risk_level)}</div>
                <div class="info-list">
                    <div class="info-item"><span class="info-key">总条目</span><span class="info-val mono">${data.total}</span></div>
                    <div class="info-item"><span class="info-key">类型数</span><span class="info-val mono">${Object.keys(grouped).length}</span></div>
                </div>
            </div>
            ${cards || '<div class="empty-state">无持久化点</div>'}`;
        status.textContent = `完成：${data.risk_level}，${data.total} 个条目`;
    } catch (e) {
        wrap.innerHTML = `<div class="empty-state">扫描失败：${esc(e.message)}</div>`;
        status.textContent = '失败';
    }
    finally { setBtnBusy(btn, false); }
}

// ===== 弱口令审计 =====
async function runWeakCred() {
    const wrap = document.getElementById('weak-result');
    const status = document.getElementById('weak-status');
    const btn = document.querySelector('#page-weakcred .btn-primary');
    setBtnBusy(btn, true);
    taskRunning(wrap, '弱口令审计', '审计账户与密码策略...');
    status.textContent = '';
    try {
        const data = await fetchAPI('/api/pentest/weak-credentials');
        const rows = data.findings.map(f => `
            <tr>
                <td class="mono">${esc(f.user)}</td>
                <td>${esc(f.issue)}</td>
                <td>${riskBadge(f.severity)}</td>
                <td class="text-secondary" style="font-size:12px">${esc(f.detail||'—')}</td>
            </tr>`).join('') || '<tr><td colspan="4" class="empty-state">无审计项</td></tr>';
        wrap.innerHTML = `
            <div class="report-bar"><span class="text-secondary">扫描完成</span><button class="btn btn-sm btn-primary" onclick="exportReport('weakcred')">导出报告</button></div>
            <div class="card">
                <div class="card-header"><span class="card-title">弱口令审计结果</span>${riskBadge(data.risk_level)}</div>
                <div class="info-list">
                    <div class="info-item"><span class="info-key">总发现</span><span class="info-val mono">${data.total}</span></div>
                </div>
            </div>
            <div class="card" style="margin-top:12px">
                <div class="card-header"><span class="card-title">详细审计项</span></div>
                <div class="table-wrap"><table>
                    <thead><tr><th>对象</th><th>问题</th><th>风险</th><th>说明</th></tr></thead>
                    <tbody>${rows}</tbody>
                </table></div>
            </div>`;
        status.textContent = `完成：${data.risk_level}，${data.total} 项`;
    } catch (e) {
        wrap.innerHTML = `<div class="empty-state">审计失败：${esc(e.message)}</div>`;
        status.textContent = '失败';
    }
    finally { setBtnBusy(btn, false); }
}

// ===== 反取证检测 =====
async function runAntiForen() {
    const wrap = document.getElementById('antiforen-result');
    const status = document.getElementById('antiforen-status');
    const btn = document.querySelector('#page-antiforen .btn-primary');
    setBtnBusy(btn, true);
    taskRunning(wrap, '反取证检测', '检测嗅探器/隐蔽通道/日志清除/绕过工具...');
    status.textContent = '';
    try {
        const data = await fetchAPI('/api/pentest/anti-forensics');
        const findHTML = data.findings.map(f => `
            <div class="check-row">
                <div class="check-icon ${f.severity==='极高'||f.severity==='高'?'fail':f.severity==='信息'?'pass':'warn'}">${f.severity==='极高'||f.severity==='高'?'!':f.severity==='信息'?'✓':'?'}</div>
                <div class="check-body">
                    <div class="check-title">${esc(f.name)} <span class="text-muted" style="font-size:11px">[${esc(f.category)}]</span> ${riskBadge(f.severity)}</div>
                    <div class="text-secondary" style="font-size:12px;margin-top:2px">${esc(f.detail)}</div>
                </div>
            </div>`).join('');
        const procHTML = data.suspicious_processes.length ? data.suspicious_processes.map(p => `
            <tr><td class="mono">${esc(p.name)}</td><td class="mono">${p.pid}</td><td class="mono" style="max-width:50%;word-break:break-all">${esc(p.exe)}</td><td><span class="badge badge-red">${esc(p.desc)}</span></td></tr>
        `).join('') : '<tr><td colspan="4" class="empty-state">无可疑进程</td></tr>';
        const extHTML = data.external_connections.length ? data.external_connections.slice(0,30).map(c => `
            <tr><td class="mono">${esc(c.remote)}</td><td class="mono">${esc(c.process)}</td><td class="mono">${c.pid||'—'}</td></tr>
        `).join('') : '<tr><td colspan="3" class="empty-state">无非标准外联</td></tr>';
        wrap.innerHTML = `
            <div class="report-bar"><span class="text-secondary">扫描完成</span><button class="btn btn-sm btn-primary" onclick="exportReport('antiforen')">导出报告</button></div>
            <div class="grid grid-2">
                <div class="card"><div class="card-header"><span class="card-title">检测结果</span>${riskBadge(data.risk_level)}</div>
                    <div class="info-list"><div class="info-item"><span class="info-key">总检测项</span><span class="info-val mono">${data.total_findings}</span></div></div>
                </div>
                <div class="card"><div class="card-header"><span class="card-title">可疑进程</span><span class="badge badge-red">${data.suspicious_processes.length}</span></div>
                    <div class="table-wrap"><table>
                        <thead><tr><th>进程</th><th>PID</th><th>路径</th><th>分类</th></tr></thead>
                        <tbody>${procHTML}</tbody>
                    </table></div>
                </div>
            </div>
            <div class="card" style="margin-top:16px"><div class="card-header"><span class="card-title">检测项详情</span></div><div class="check-list">${findHTML}</div></div>
            <div class="card" style="margin-top:16px"><div class="card-header"><span class="card-title">非标准端口外联</span><span class="badge badge-yellow">${data.external_connections.length}</span></div>
                <div class="table-wrap"><table>
                    <thead><tr><th>远端</th><th>进程</th><th>PID</th></tr></thead>
                    <tbody>${extHTML}</tbody>
                </table></div>
            </div>`;
        status.textContent = `完成：${data.risk_level}`;
    } catch (e) {
        wrap.innerHTML = `<div class="empty-state">检测失败：${esc(e.message)}</div>`;
        status.textContent = '失败';
    }
    finally { setBtnBusy(btn, false); }
}

// ===== 时钟 =====
function updateClock() {
    document.getElementById('footer-time').textContent = new Date().toTimeString().slice(0,5);
}
setInterval(updateClock, 1000);
updateClock();

// ===== 初始化 =====
initMobileMenu();
loadDashboard();
