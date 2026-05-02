from __future__ import annotations

import argparse
import asyncio
import json
import random
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import traceback

from shared import Nation, Province

TICK_SECONDS = 1.0


class RealtimeGame:
    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.players: Dict[str, WebSocket] = {}
        self.ai_names = ["AI-苏联", "AI-英国"]
        self.nations: Dict[str, Nation] = {}
        self.provinces: Dict[int, Province] = self._init_map()
        self.front_lines: List[Dict[str, Any]] = []
        self.tech_tree = {
            "industry_1": {"name": "工业优化", "cost": 20, "desc": "工业产出+20%"},
            "doctrine_1": {"name": "机动学说", "cost": 25, "desc": "进攻+2"},
            "radar_1": {"name": "雷达", "cost": 15, "desc": "情报质量提高"},
        }
        self.started = False
        self.tick = 0

    def _init_map(self) -> Dict[int, Province]:
        return {
            1: Province(1, "柏林", "", 20, 5, 5, [2, 3]),
            2: Province(2, "华沙", "", 18, 4, 6, [1, 4, 5]),
            3: Province(3, "巴黎", "", 18, 5, 4, [1, 4]),
            4: Province(4, "布拉格", "", 14, 3, 5, [2, 3, 6]),
            5: Province(5, "明斯克", "", 12, 3, 6, [2, 6]),
            6: Province(6, "维也纳", "", 12, 4, 4, [4, 5]),
        }

    def add_nation(self, name: str, is_ai: bool = False) -> None:
        self.nations[name] = Nation(name=name, industry=30, manpower=40, supply=30, research=0, techs=[])
        free = [p for p in self.provinces.values() if not p.owner]
        if free:
            home = random.choice(free)
            home.owner = name
            home.troops += 15
        if is_ai:
            self.nations[name].diplomacy_stance = "hostile"

    def start_if_needed(self) -> None:
        if self.started:
            return
        self.started = True
        for ai in self.ai_names:
            self.add_nation(ai, is_ai=True)

    def owned(self, name: str) -> List[Province]:
        return [p for p in self.provinces.values() if p.owner == name]

    async def tick_once(self) -> None:
        async with self.lock:
            self.tick += 1
            for n in self.nations.values():
                provs = self.owned(n.name)
                industry_gain = sum(p.industry for p in provs)
                manpower_gain = sum(p.manpower for p in provs)
                tech_bonus = 1.2 if "industry_1" in n.techs else 1.0
                n.industry += int(industry_gain * tech_bonus)
                n.manpower += manpower_gain
                n.supply += max(1, len(provs))
                n.research += max(1, industry_gain // 2)
            self._ai_actions()
            self._resolve_front_lines()
            await self.broadcast_state()

    def _ai_actions(self) -> None:
        for ai in [x for x in self.nations if x.startswith("AI-")]:
            ai_n = self.nations[ai]
            mine = self.owned(ai)
            if not mine:
                continue
            p = random.choice(mine)
            if ai_n.manpower >= 5 and ai_n.industry >= 5:
                p.troops += 5
                ai_n.manpower -= 5
                ai_n.industry -= 5
            # auto declare war if neutral relations
            for other in self.nations:
                if other == ai:
                    continue
                key = self._dip_key(ai, other)
                if self.front_lines and any(fl["a"] == ai and fl["b"] == other for fl in self.front_lines):
                    continue
                if self.nations[ai].diplomacy.get(key, "war") == "war":
                    self.front_lines.append({"a": ai, "b": other, "intensity": 1})
                    break

    def _resolve_front_lines(self) -> None:
        for fl in self.front_lines:
            a, b = fl["a"], fl["b"]
            borders = [(x, y) for x in self.owned(a) for y in self.owned(b) if y.id in x.neighbors]
            if not borders:
                continue
            frm, to = random.choice(borders)
            atk = min(frm.troops // 3, 10)
            if atk <= 0:
                continue
            bonus = 2 if "doctrine_1" in self.nations[a].techs else 0
            atk_power = atk + random.randint(0, 6) + bonus
            def_power = to.troops + random.randint(0, 5)
            frm.troops -= atk
            if atk_power > def_power:
                to.owner = a
                to.troops = max(3, atk_power - def_power)
            else:
                to.troops = max(1, to.troops - atk // 2)

    def _dip_key(self, a: str, b: str) -> str:
        return "|".join(sorted([a, b]))

    async def handle(self, player: str, msg: Dict[str, Any]) -> Dict[str, Any]:
        async with self.lock:
            if player not in self.nations:
                self.add_nation(player)
                self.start_if_needed()

            cmd = msg.get("cmd")
            args = msg.get("args", {})

            if cmd == "recruit":
                return {"ok": True, "message": self._recruit(player, args)}
            if cmd == "attack":
                return {"ok": True, "message": self._attack(player, args)}
            if cmd == "move":
                return {"ok": True, "message": self._move(player, args)}
            if cmd == "research":
                return {"ok": True, "message": self._research(player, args)}
            if cmd == "diplomacy":
                return {"ok": True, "message": self._diplomacy(player, args)}
            return {"ok": True, "message": "unknown cmd"}

    def _recruit(self, player: str, args: Dict[str, Any]) -> str:
        pid = int(args.get("province_id", 0))
        amount = int(args.get("amount", 0))
        p = self.provinces.get(pid)
        if not p or p.owner != player:
            return "province invalid"
        n = self.nations[player]
        if n.industry < amount or n.manpower < amount:
            return "resource not enough"
        n.industry -= amount
        n.manpower -= amount
        p.troops += amount
        return f"recruit +{amount}"


    def _move(self, player: str, args: Dict[str, Any]) -> str:
        frm = self.provinces.get(int(args.get("from_id", 0)))
        to = self.provinces.get(int(args.get("to_id", 0)))
        amount = int(args.get("amount", 0))
        if not frm or not to or frm.owner != player or to.owner != player:
            return "move invalid owner"
        if to.id not in frm.neighbors:
            return "move not adjacent"
        if amount <= 0 or frm.troops < amount:
            return "move troops insufficient"
        frm.troops -= amount
        to.troops += amount
        return "move success"

    def _attack(self, player: str, args: Dict[str, Any]) -> str:
        a, b = args.get("from_id"), args.get("to_id")
        frm, to = self.provinces.get(int(a)), self.provinces.get(int(b))
        if not frm or not to or frm.owner != player or to.id not in frm.neighbors:
            return "invalid attack"
        if to.owner == player:
            return "cannot attack self"
        # diplomacy check
        if self.nations[player].diplomacy.get(self._dip_key(player, to.owner), "peace") != "war":
            return "not at war, use diplomacy declare_war"
        atk = min(frm.troops // 2, int(args.get("amount", 0)))
        if atk <= 0:
            return "troops insufficient"
        frm.troops -= atk
        bonus = 2 if "doctrine_1" in self.nations[player].techs else 0
        if atk + random.randint(0, 6) + bonus > to.troops + random.randint(0, 4):
            to.owner = player
            to.troops = max(2, atk // 2)
            return "captured"
        to.troops = max(1, to.troops - atk // 2)
        return "failed"

    def _research(self, player: str, args: Dict[str, Any]) -> str:
        tech_id = args.get("tech_id")
        if tech_id not in self.tech_tree:
            return "tech not found"
        n = self.nations[player]
        if tech_id in n.techs:
            return "already researched"
        cost = self.tech_tree[tech_id]["cost"]
        if n.research < cost:
            return "research points not enough"
        n.research -= cost
        n.techs.append(tech_id)
        return f"researched {tech_id}"

    def _diplomacy(self, player: str, args: Dict[str, Any]) -> str:
        target = args.get("target")
        action = args.get("action")
        if target not in self.nations or target == player:
            return "invalid target"
        key = self._dip_key(player, target)
        if action == "declare_war":
            self.nations[player].diplomacy[key] = "war"
            self.nations[target].diplomacy[key] = "war"
            self.front_lines.append({"a": player, "b": target, "intensity": 2})
            return f"{player} declared war on {target}"
        if action == "offer_peace":
            self.nations[player].diplomacy[key] = "peace"
            self.nations[target].diplomacy[key] = "peace"
            self.front_lines = [f for f in self.front_lines if set([f['a'], f['b']]) != set([player, target])]
            return "peace established"
        return "unsupported diplomacy action"

    def state(self) -> Dict[str, Any]:
        return {
            "type": "state",
            "tick": self.tick,
            "tech_tree": self.tech_tree,
            "nations": [asdict(n) for n in self.nations.values()],
            "provinces": [asdict(p) for p in self.provinces.values()],
            "front_lines": self.front_lines,
            "server_time": int(time.time()),
        }

    async def broadcast_state(self) -> None:
        payload = json.dumps(self.state(), ensure_ascii=False)
        stale = []
        for name, ws in self.players.items():
            try:
                await ws.send_text(payload)
            except Exception:
                stale.append(name)
        for name in stale:
            self.players.pop(name, None)


GAME = RealtimeGame()
app = FastAPI()
static_dir = Path(__file__).parent / "web"
app.mount("/web", StaticFiles(directory=str(static_dir)), name="web")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.websocket("/ws/{player}")
async def ws_endpoint(websocket: WebSocket, player: str) -> None:
    await websocket.accept()
    async with GAME.lock:
        GAME.players[player] = websocket
        if player not in GAME.nations:
            GAME.add_nation(player)
            GAME.start_if_needed()
    await websocket.send_json(GAME.state())
    try:
        while True:
            data = await websocket.receive_json()
            result = await GAME.handle(player, data)
            await websocket.send_json({"type": "result", **result})
    except WebSocketDisconnect:
        async with GAME.lock:
            GAME.players.pop(player, None)


async def ticker() -> None:
    while True:
        await asyncio.sleep(TICK_SECONDS)
        await GAME.tick_once()


@app.on_event("startup")
async def startup_event() -> None:
    asyncio.create_task(ticker())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9000)
    args = parser.parse_args()
    print(f"[启动] HOI realtime server 正在启动: http://{args.host}:{args.port}")
    print("[启动] 浏览器打开: http://127.0.0.1:%d" % args.port)
    print("[启动] WebSocket 地址: ws://127.0.0.1:%d/ws/<你的名字>" % args.port)
    try:
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    except Exception as exc:
        print("[错误] 服务器启动失败:", exc)
        traceback.print_exc()
        print("[提示] 请先安装依赖: pip install fastapi uvicorn websockets")


if __name__ == "__main__":
    main()
