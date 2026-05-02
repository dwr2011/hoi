from __future__ import annotations

import argparse
import asyncio
import json
import websockets


async def run(host: str, port: int, name: str) -> None:
    uri = f"ws://{host}:{port}/ws/{name}"
    async with websockets.connect(uri) as ws:
        print("connected", uri)

        async def recv() -> None:
            async for msg in ws:
                data = json.loads(msg)
                if data.get("type") == "state":
                    print(f"[tick={data['tick']}] provinces={len(data['provinces'])} nations={len(data['nations'])}")
                else:
                    print(data)

        async def send() -> None:
            while True:
                raw = await asyncio.to_thread(input, "> ")
                parts = raw.strip().split()
                if not parts:
                    continue
                cmd = parts[0]
                if cmd == "recruit":
                    await ws.send(json.dumps({"cmd": "recruit", "args": {"province_id": int(parts[1]), "amount": int(parts[2])}}))
                elif cmd == "attack":
                    await ws.send(json.dumps({"cmd": "attack", "args": {"from_id": int(parts[1]), "to_id": int(parts[2]), "amount": int(parts[3])}}))
                elif cmd == "research":
                    await ws.send(json.dumps({"cmd": "research", "args": {"tech_id": parts[1]}}))
                elif cmd == "war":
                    await ws.send(json.dumps({"cmd": "diplomacy", "args": {"target": parts[1], "action": "declare_war"}}))

        await asyncio.gather(recv(), send())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    asyncio.run(run(args.host, args.port, args.name))


if __name__ == "__main__":
    main()
