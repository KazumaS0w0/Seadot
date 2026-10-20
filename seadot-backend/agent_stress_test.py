"""Stress-test the Seadot start endpoint and monitor backend RSS."""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import aiohttp
import psutil

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DOWNLOAD_COUNT = 10
MONITOR_SECONDS = 30
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


def find_backend_pid(port: int) -> int:
    """Find the process listening on the API port."""
    try:
        listeners = [
            connection
            for connection in psutil.net_connections(kind="inet")
            if connection.status == psutil.CONN_LISTEN
            and connection.laddr
            and connection.laddr.port == port
            and connection.pid is not None
        ]
    except (psutil.AccessDenied, OSError) as exc:
        raise RuntimeError(
            "Tidak dapat membaca PID listener. Jalankan PowerShell dengan izin yang sesuai "
            "atau berikan --pid <PID_BACKEND>."
        ) from exc

    pids = sorted({connection.pid for connection in listeners})
    if not pids:
        raise RuntimeError(
            f"Tidak menemukan proses yang listen pada port {port}; "
            "pastikan backend berjalan atau berikan --pid <PID_BACKEND>."
        )
    if len(pids) > 1:
        raise RuntimeError(
            f"Ada beberapa PID yang listen pada port {port}: {pids}. "
            "Pilih proses backend dengan --pid <PID_BACKEND>."
        )
    return pids[0]


async def read_response(response: aiohttp.ClientResponse) -> dict | str:
    try:
        return await response.json()
    except (aiohttp.ContentTypeError, ValueError):
        return await response.text()


async def create_test_downloads(
    session: aiohttp.ClientSession,
    base_url: str,
    dummy_url: str,
    output_dir: Path,
    download_ids: list[str],
) -> None:
    for index in range(DOWNLOAD_COUNT):
        download_id = uuid.uuid4().hex[:8]
        payload = {
            "download_id": download_id,
            "url": dummy_url,
            "dest_path": str(output_dir / f"stress-{index + 1}-{download_id}.bin"),
            "status": "pending",
        }
        async with session.post(
            f"{base_url}/api/v1/download/create",
            json=payload,
        ) as response:
            body = await read_response(response)
            if response.status != 201:
                raise RuntimeError(
                    f"Gagal membuat record {download_id}: HTTP {response.status}: {body}"
                )
        download_ids.append(download_id)
        print(f"[SETUP] Record {index + 1}/{DOWNLOAD_COUNT} dibuat: {download_id}")


async def start_one_download(
    session: aiohttp.ClientSession,
    base_url: str,
    download_id: str,
) -> tuple[str, int, dict | str]:
    try:
        async with session.post(
            f"{base_url}/api/downloads/start",
            params={"download_id": download_id},
        ) as response:
            return download_id, response.status, await read_response(response)
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        return download_id, 0, str(exc)


async def remove_test_download(
    session: aiohttp.ClientSession,
    base_url: str,
    download_id: str,
) -> bool:
    try:
        async with session.delete(
            f"{base_url}/api/downloads/remove/{download_id}",
        ) as response:
            body = await read_response(response)
            if 200 <= response.status < 300:
                print(f"[CLEANUP] Transfer {download_id} dihentikan.")
                return True
            print(
                f"[PERINGATAN] Cleanup {download_id} gagal: "
                f"HTTP {response.status}: {body}"
            )
            return False
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        print(f"[PERINGATAN] Cleanup {download_id} gagal: {exc}")
        return False


async def monitor_backend(pid: int, duration: int) -> None:
    try:
        process = psutil.Process(pid)
        process.memory_info()
    except psutil.NoSuchProcess as exc:
        raise RuntimeError(f"PID backend {pid} tidak ditemukan.") from exc
    except psutil.AccessDenied as exc:
        raise RuntimeError(
            "Akses untuk membaca RAM backend ditolak. Jalankan PowerShell "
            "dengan izin yang sesuai."
        ) from exc

    print(f"[RAM] Memantau RSS proses backend PID {pid} selama {duration} detik.")
    for second in range(duration + 1):
        try:
            rss_mb = process.memory_info().rss / (1024 * 1024)
            print(f"[RAM] t={second:02d}s | PID={pid} | RSS={rss_mb:.1f} MB")
        except psutil.NoSuchProcess:
            print(f"[RAM] PID {pid} sudah berhenti.")
            return
        except psutil.AccessDenied as exc:
            raise RuntimeError(
                "Akses untuk membaca RAM backend ditolak. Jalankan PowerShell "
                "dengan izin yang sesuai."
            ) from exc
        if second < duration:
            await asyncio.sleep(1)


async def run(args: argparse.Namespace) -> int:
    base_url = args.base_url.rstrip("/")
    parsed_url = urlsplit(base_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
        raise RuntimeError("--base-url harus berupa URL HTTP(S) yang valid.")
    try:
        port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)
    except ValueError as exc:
        raise RuntimeError("--base-url memiliki nomor port yang tidak valid.") from exc
    backend_pid = args.pid or find_backend_pid(port)
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    timeout = aiohttp.ClientTimeout(total=30)
    dummy_server, dummy_url = await start_dummy_server()

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            download_ids: list[str] = []
            print(f"[INFO] Backend: {base_url} (PID {backend_pid})")
            print(f"[INFO] File uji lokal 1 GB: {dummy_url}")
            print(
                "[INFO] Fixture hanya mengirim data melalui loopback; "
                "tidak ada unduhan dari server pihak ketiga."
            )
            try:
                await create_test_downloads(
                    session,
                    base_url,
                    dummy_url,
                    output_dir,
                    download_ids,
                )
                print(
                    f"[START] Mengirim {DOWNLOAD_COUNT} request POST /api/downloads/start "
                    "secara bersamaan..."
                )
                start_requests = asyncio.gather(
                    *(
                        start_one_download(session, base_url, download_id)
                        for download_id in download_ids
                    )
                )
                start_results, _ = await asyncio.gather(
                    start_requests,
                    monitor_backend(backend_pid, args.monitor_seconds),
                )
            finally:
                cleanup_results = await asyncio.gather(
                    *(
                        remove_test_download(session, base_url, download_id)
                        for download_id in download_ids
                    )
                )

            failures = 0
            for download_id, status, body in start_results:
                if 200 <= status < 300:
                    print(f"[OK] Start {download_id}: HTTP {status} | {body}")
                else:
                    failures += 1
                    print(f"[GAGAL] Start {download_id}: HTTP {status} | {body}")

            cleanup_succeeded = all(cleanup_results)
            passed = DOWNLOAD_COUNT - failures
            print(f"[RINGKASAN] Start berhasil: {passed}/{DOWNLOAD_COUNT}")
            return 1 if failures or not cleanup_succeeded else 0
    finally:
        dummy_server.close()
        await dummy_server.wait_closed()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stress-test 10 start request bersamaan dan pantau RAM backend."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument(
        "--pid",
        type=int,
        help="PID backend (opsional; otomatis dideteksi dari port API).",
    )
    parser.add_argument("--monitor-seconds", type=int, default=MONITOR_SECONDS)
    parser.add_argument(
        "--output-dir",
        default=str(Path.home() / "Downloads" / "Seadot-QA"),
        help="Folder tujuan sementara untuk file uji.",
    )
    args = parser.parse_args()
    if args.monitor_seconds < 1:
        parser.error("--monitor-seconds harus minimal 1.")
    if args.pid is not None and args.pid < 1:
        parser.error("--pid harus berupa bilangan bulat positif.")
    return args


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(run(parse_args())))
    except (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError, OSError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
