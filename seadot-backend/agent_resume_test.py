"""Exercise Seadot's start/pause/resume API with a local 1 GB test stream."""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import aiohttp

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DUMMY_SIZE_BYTES = 1024**3
DUMMY_CHUNK = bytes(64 * 1024)


async def serve_dummy_file(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Stream a slow, local 1 GB test response until the client disconnects."""
    try:
        request_line = await reader.readline()
        if not request_line:
            return
        while await reader.readline() not in (b"\r\n", b"\n", b""):
            pass

        writer.write(
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/octet-stream\r\n"
            + f"Content-Length: {DUMMY_SIZE_BYTES}\r\n".encode("ascii")
            + b"Connection: close\r\n\r\n"
        )
        await writer.drain()

        bytes_sent = 0
        while bytes_sent < DUMMY_SIZE_BYTES:
            writer.write(DUMMY_CHUNK)
            await writer.drain()
            bytes_sent += len(DUMMY_CHUNK)
            await asyncio.sleep(0.25)
    except OSError:
        pass
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass


async def start_dummy_server() -> tuple[asyncio.Server, str]:
    server = await asyncio.start_server(serve_dummy_file, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    return server, f"http://127.0.0.1:{port}/dummy-1gb.bin"


async def read_response(response: aiohttp.ClientResponse) -> dict | str:
    try:
        return await response.json()
    except (aiohttp.ContentTypeError, ValueError):
        return await response.text()


async def post_json(
    session: aiohttp.ClientSession,
    url: str,
    *,
    json_body: dict | None = None,
    params: dict | None = None,
) -> tuple[int, dict | str]:
    async with session.post(url, json=json_body, params=params) as response:
        return response.status, await read_response(response)


async def require_success(
    session: aiohttp.ClientSession,
    action: str,
    url: str,
    *,
    json_body: dict | None = None,
    params: dict | None = None,
) -> dict | str:
    status, body = await post_json(
        session,
        url,
        json_body=json_body,
        params=params,
    )
    if not 200 <= status < 300:
        raise RuntimeError(f"{action} gagal: HTTP {status}: {body}")
    print(f"[OK] {action} (HTTP {status}): {body}")
    return body


async def cleanup_download(
    session: aiohttp.ClientSession,
    base_url: str,
    download_id: str,
) -> bool:
    try:
        async with session.delete(
            f"{base_url}/api/downloads/remove/{download_id}",
        ) as response:
            body = await read_response(response)
            if not 200 <= response.status < 300:
                print(
                    f"[PERINGATAN] Cleanup transfer gagal: "
                    f"HTTP {response.status}: {body}"
                )
                return False
            else:
                print("[CLEANUP] Transfer uji dihentikan.")
                return True
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        print(f"[PERINGATAN] Cleanup transfer gagal: {exc}")
        return False


async def run(args: argparse.Namespace) -> None:
    base_url = args.base_url.rstrip("/")
    parsed_url = urlsplit(base_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
        raise RuntimeError("--base-url harus berupa URL HTTP(S).")
    try:
        parsed_url.port
    except ValueError as exc:
        raise RuntimeError("--base-url memiliki nomor port yang tidak valid.") from exc

    download_id = uuid.uuid4().hex[:8]
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"resume-{download_id}.bin"
    timeout = aiohttp.ClientTimeout(total=30)
    dummy_server, dummy_url = await start_dummy_server()

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            print(f"[INFO] Backend: {base_url}")
            print(f"[INFO] File uji lokal 1 GB: {dummy_url}")
            print("[INFO] Transfer hanya berlangsung melalui loopback.")

            print(f"[1/5] Membuat record download uji: {download_id}")
            status, body = await post_json(
                session,
                f"{base_url}/api/v1/download/create",
                json_body={
                    "download_id": download_id,
                    "url": dummy_url,
                    "dest_path": str(output_path),
                    "status": "pending",
                },
            )
            if status != 201:
                raise RuntimeError(f"Membuat record gagal: HTTP {status}: {body}")
            print(f"[OK] Record dibuat (HTTP {status}): {body}")

            try:
                print("[2/5] Memanggil start...")
                await require_success(
                    session,
                    "Start",
                    f"{base_url}/api/downloads/start",
                    params={"download_id": download_id},
                )

                print("[3/5] Menunggu 5 detik sebelum simulasi koneksi terputus...")
                await asyncio.sleep(5)

                print("[4/5] Memanggil pause...")
                await require_success(
                    session,
                    "Pause",
                    f"{base_url}/api/downloads/pause",
                    params={"download_id": download_id},
                )

                print("[INFO] Koneksi disimulasikan terputus; menunggu 3 detik...")
                await asyncio.sleep(3)

                print("[5/5] Memulihkan koneksi dengan resume...")
                await require_success(
                    session,
                    "Resume",
                    f"{base_url}/api/downloads/resume",
                    params={"download_id": download_id},
                )
            finally:
                cleanup_succeeded = await cleanup_download(
                    session,
                    base_url,
                    download_id,
                )

            if not cleanup_succeeded:
                raise RuntimeError("Transfer uji tidak berhasil dibersihkan.")

    finally:
        dummy_server.close()
        await dummy_server.wait_closed()

    print(f"[SELESAI] Uji lifecycle selesai untuk download_id={download_id}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Uji berurutan API start, pause, dan resume Seadot."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument(
        "--output-dir",
        default=str(Path.home() / "Downloads" / "Seadot-QA"),
        help="Folder tujuan sementara untuk file uji.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    try:
        asyncio.run(run(parse_args()))
    except (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError, OSError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
