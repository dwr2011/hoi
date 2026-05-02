# 实时联机大战略原型（类钢铁雄心）

本版本已升级为：
- 真正实时 tick 模式（每秒推进）
- 科技树（industry/doctrine/radar）
- AI 国家自动征兵与前线推进
- 外交系统（宣战 / 和平）
- Web 可视化前端（FastAPI + WebSocket + HTML）

## 运行

```bash
pip install fastapi uvicorn websockets
python3 server.py --host 0.0.0.0 --port 9000
```

浏览器打开 `http://127.0.0.1:9000`。

## CLI 客户端（可选）

```bash
python3 client.py --host 127.0.0.1 --port 9000 --name 德国
```

命令：
- `recruit <province_id> <amount>`
- `attack <from_id> <to_id> <amount>`
- `research <tech_id>`
- `war <nation_name>`

## 核心机制

1. **实时 Tick**：服务器后台协程每秒刷新资源、科研点、AI 行动、前线结算。
2. **科技树**：科研点累积后可解锁工业与学说加成。
3. **AI 国家**：自动征兵、自动在战争状态下发起边境攻势。
4. **外交**：玩家可对其他国家宣战/议和，战争会生成前线并自动结算。
5. **WebSocket 同步**：服务器向全部在线玩家广播完整状态。

## 地图交互（图形化）

- **左键**：选中省份（选择出发地后再点目标地，默认执行调兵）
- **Shift + 左键目标省份**：发起攻击
- **右键省份**：快速征兵（+5）
- 地图会实时显示省份归属、兵力、连接关系，并随 tick 自动刷新


## Windows 启动排错（你说“啥都没有”）

如果你在 Windows 的 CMD 中执行：

```bash
python3 server.py --host 0.0.0.0 --port 9000
```

没有任何输出，按下面做：

1. 先确认 Python 命令（Windows 通常是 `py` 或 `python`，不一定有 `python3`）：

```bash
py --version
python --version
```

2. 安装依赖：

```bash
py -m pip install -r requirements.txt
```

3. 启动服务器（推荐）：

```bash
py server.py --host 127.0.0.1 --port 9000
```

4. 看到如下日志即表示启动成功：
- `[启动] HOI realtime server 正在启动...`
- `Uvicorn running on ...`

5. 浏览器打开：
- `http://127.0.0.1:9000`

如果仍无输出，请直接运行：

```bash
py -m uvicorn server:app --host 127.0.0.1 --port 9000 --log-level debug
```


## Python 3.7 兼容说明（你这个报错的根因）

你当前环境是 `Python 3.7` + 很旧的 `pip 20.1.1`，而我之前写的 `fastapi>=0.115.0` 需要更高版本 Python，
所以会出现 `No matching distribution found`。

现在仓库已改成 **Python 3.7 可安装** 版本：
- `fastapi==0.103.2`
- `uvicorn==0.22.0`
- `websockets==10.4`

建议命令（Windows）：

```bash
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
py server.py --host 127.0.0.1 --port 9000
```

如果你后续升级到 Python 3.10+，再把依赖升到更新版本会更稳。


## 你仍然看到 `fastapi>=0.115.0` 怎么办？

这说明你运行的不是我最新文件（旧目录或旧压缩包）。
请先在当前目录执行：

```bash
type requirements.txt
```

如果第一行不是 `fastapi==0.103.2`，就是旧文件。

### 最省事方案（Python 3.7）

直接双击或运行：

```bash
setup_windows_py37.bat
```

它会自动：升级 pip、安装 3.7 兼容依赖、启动服务器。

### 手动方案

```bash
py -3.7 -m pip install --upgrade pip setuptools wheel
py -3.7 -m pip install -r requirements-py37.txt
py -3.7 server.py --host 127.0.0.1 --port 9000
```
