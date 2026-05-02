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
