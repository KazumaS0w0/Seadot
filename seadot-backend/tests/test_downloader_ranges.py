import asyncio
import tempfile
from pathlib import Path

from core.downloader import Downloader


def test_split_downloads_merge_in_original_byte_order():
    payload = bytes(range(256)) * 1024

    async def run_test():
        async def serve(reader, writer):
            await reader.readline()
            headers = {}
            while line := await reader.readline():
                if line in {b"\r\n", b"\n"}:
                    break
                name, value = line.decode("latin-1").split(":", 1)
                headers[name.lower()] = value.strip()

            byte_range = headers.get("range")
            if byte_range:
                start, end = map(int, byte_range.removeprefix("bytes=").split("-"))
                body = payload[start:end + 1]
                response_headers = (
                    f"HTTP/1.1 206 Partial Content\r\n"
                    f"Content-Range: bytes {start}-{end}/{len(payload)}\r\n"
                )
            else:
                body = payload
                response_headers = "HTTP/1.1 200 OK\r\n"
            writer.write(
                (
                    response_headers
                    + f"Content-Length: {len(body)}\r\n"
                    + "Connection: close\r\n\r\n"
                ).encode("ascii")
                + body
            )
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(serve, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        try:
            with tempfile.TemporaryDirectory() as directory:
                destination = Path(directory) / "split.bin"
                state = await Downloader().download_streamed(
                    f"http://127.0.0.1:{port}/file",
                    str(destination),
                    split_count=4,
                )
                assert state.progress == 100
                assert state.downloaded_size == len(payload)
                assert destination.read_bytes() == payload
        finally:
            server.close()
            await server.wait_closed()

    asyncio.run(run_test())


def test_split_download_falls_back_when_server_ignores_ranges():
    payload = b"range support is optional" * 128

    async def run_test():
        async def serve(reader, writer):
            await reader.readline()
            while line := await reader.readline():
                if line in {b"\r\n", b"\n"}:
                    break
            writer.write(
                (
                    "HTTP/1.1 200 OK\r\n"
                    f"Content-Length: {len(payload)}\r\n"
                    "Connection: close\r\n\r\n"
                ).encode("ascii")
                + payload
            )
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(serve, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        try:
            with tempfile.TemporaryDirectory() as directory:
                destination = Path(directory) / "fallback.bin"
                state = await Downloader().download_streamed(
                    f"http://127.0.0.1:{port}/file",
                    str(destination),
                    split_count=4,
                )
                assert state.progress == 100
                assert destination.read_bytes() == payload
        finally:
            server.close()
            await server.wait_closed()

    asyncio.run(run_test())
