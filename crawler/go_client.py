import asyncio
import logging
import os
import subprocess
import time
from typing import AsyncGenerator, Dict, Any, Optional

import grpc
from crawler.proto import crawler_pb2, crawler_pb2_grpc

logger = logging.getLogger(__name__)

_go_crawler_proc = None

class GoCrawlerClient:
    """Async gRPC client communicating with the high-throughput Go Crawl Engine."""

    def __init__(self, host: str = "127.0.0.1", port: int = 50051):
        self.host = host
        self.port = port
        self.target = f"{host}:{port}"
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[crawler_pb2_grpc.CrawlerServiceStub] = None

    async def connect(self):
        if self.channel is None:
            self.channel = grpc.aio.insecure_channel(
                self.target,
                options=[
                    ('grpc.max_receive_message_length', 100 * 1024 * 1024),
                    ('grpc.max_send_message_length', 100 * 1024 * 1024),
                ]
            )
            self.stub = crawler_pb2_grpc.CrawlerServiceStub(self.channel)

    async def close(self):
        if self.channel is not None:
            await self.channel.close()
            self.channel = None
            self.stub = None

    async def is_available(self, timeout_sec: float = 0.5) -> bool:
        """Check if the Go crawler gRPC server is active."""
        try:
            await self.connect()
            fut = self.channel.channel_ready()
            await asyncio.wait_for(fut, timeout=timeout_sec)
            return True
        except Exception:
            return False

    async def ensure_service_running(self, timeout_sec: float = 5.0) -> bool:
        """Check if Go crawler daemon is up; if not, build/launch it in background."""
        global _go_crawler_proc
        if await self.is_available(timeout_sec=0.2):
            return True

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        go_dir = os.path.join(project_root, "go-crawler")
        bin_path = os.path.join(go_dir, "bin", "crawler.exe" if os.name == 'nt' else "crawler")

        if not os.path.exists(bin_path):
            logger.info("Go crawler binary not found. Compiling high-throughput engine...")
            try:
                build_proc = await asyncio.to_thread(
                    subprocess.run,
                    ["go", "build", "-o", bin_path, "./cmd/crawler"],
                    cwd=go_dir,
                    capture_output=True,
                    text=True,
                    check=True
                )
                logger.info("Go crawler binary built successfully.")
            except Exception as e:
                logger.error(f"Failed to build Go crawler binary: {e}")
                return False

        if os.path.exists(bin_path):
            logger.info(f"Starting Go Crawler service on port {self.port}...")
            cmd = [bin_path, f"--port={self.port}"]
            creation_flags = 0
            if os.name == 'nt':
                creation_flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS

            try:
                _go_crawler_proc = subprocess.Popen(
                    cmd,
                    cwd=project_root,
                    creationflags=creation_flags,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception as e:
                logger.error(f"Failed to spawn Go crawler process: {e}")
                return False

            # Wait for service to become responsive
            start_t = time.time()
            while time.time() - start_t < timeout_sec:
                # Re-create channel to avoid stale connections
                if self.channel is not None:
                    try:
                        await self.channel.close()
                    except Exception:
                        pass
                    self.channel = None
                    self.stub = None
                if await self.is_available(timeout_sec=0.3):
                    logger.info("[Go-Crawler] High-throughput Go Crawler service is ready.")
                    return True
                await asyncio.sleep(0.15)

        return await self.is_available(timeout_sec=0.5)

    async def start_crawl(self, config_dict: Dict[str, Any]) -> AsyncGenerator[crawler_pb2.CrawlEvent, None]:
        """Stream crawl progress and page results from Go crawler."""
        await self.connect()

        concurrency = int(config_dict.get("concurrency", 30))
        max_per_host = int(config_dict.get("max_per_host", concurrency))
        host_delay_ms = int(config_dict.get("host_delay_ms", 0))

        req = crawler_pb2.CrawlRequest(
            audit_id=str(config_dict.get("audit_id", "")),
            start_url=str(config_dict.get("start_url", "")),
            max_pages=int(config_dict.get("max_pages", 0)),
            concurrency=concurrency,
            max_per_host=max_per_host,
            host_delay_ms=host_delay_ms,
            user_agent=str(config_dict.get("user_agent", "")),
            crawl_mode=str(config_dict.get("crawl_mode", "spider")),
            urls_list=list(config_dict.get("urls_list", [])),
            include_regex=list(config_dict.get("include_regex", [])),
            exclude_regex=list(config_dict.get("exclude_regex", [])),
            max_crawl_depth=int(config_dict.get("max_crawl_depth", 0)),
            crawl_subdomains=bool(config_dict.get("crawl_subdomains", False)),
            allowed_domains=list(config_dict.get("allowed_domains", [])),
            block_urls=list(config_dict.get("block_urls", [])),
            postgres_dsn=str(config_dict.get("postgres_dsn", "")),
            sqlite_path=str(config_dict.get("sqlite_path", "data/audits.db")),
            respect_robots_crawl_delay=bool(config_dict.get("respect_robots_crawl_delay", False)),
        )

        try:
            async for event in self.stub.StartCrawl(req):
                yield event
        except grpc.RpcError as e:
            logger.error(f"gRPC stream error during StartCrawl: {e}")
            raise

    async def resume_crawl(self, audit_id: str, postgres_dsn: str = "", sqlite_path: str = "data/audits.db") -> AsyncGenerator[crawler_pb2.CrawlEvent, None]:
        """Resume a paused or interrupted crawl."""
        await self.connect()
        req = crawler_pb2.ResumeRequest(audit_id=audit_id, postgres_dsn=postgres_dsn, sqlite_path=sqlite_path)
        try:
            async for event in self.stub.ResumeCrawl(req):
                yield event
        except grpc.RpcError as e:
            logger.error(f"gRPC stream error during ResumeCrawl: {e}")
            raise

    async def stop_crawl(self, audit_id: str) -> bool:
        """Signal Go crawler to gracefully stop an active crawl."""
        await self.connect()
        req = crawler_pb2.StopRequest(audit_id=audit_id)
        try:
            res = await self.stub.StopCrawl(req)
            return res.success
        except grpc.RpcError as e:
            logger.warning(f"Failed to stop crawl for audit {audit_id}: {e}")
            return False

    async def get_status(self, audit_id: str) -> Optional[crawler_pb2.CrawlStatus]:
        """Query current status of an audit."""
        await self.connect()
        req = crawler_pb2.StatusRequest(audit_id=audit_id)
        try:
            return await self.stub.GetStatus(req)
        except grpc.RpcError as e:
            logger.warning(f"Failed to get status for audit {audit_id}: {e}")
            return None
