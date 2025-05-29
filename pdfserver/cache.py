from pdfserver.log import logger
from uuid import uuid4
import asyncio
import time


class ExpiringPDFCache:
    def __init__(self, expiry_minutes=30):
        self.cache = {}
        self.expiry_seconds = expiry_minutes * 60
        self._cleanup_task = None

    async def start_cleanup_task(self):
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop_cleanup_task(self):
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def _cleanup_loop(self):
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self._remove_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def _remove_expired(self):
        """Remove expired PDFs from cache"""
        current_time = time.time()
        expired_keys = [
            key for key, pdf in self.cache.items()
            if current_time - pdf['timestamp'] > self.expiry_seconds
        ]

        for key in expired_keys:
            del self.cache[key]
            logger.info(f"Removed expired PDF: {key}")

        if expired_keys:
            logger.info(f"Cache cleanup: removed {len(expired_keys)} expired PDFs")

    def store_pdf(self, uid, pdf_data, status):
        """Store PDF data with current timestamp"""
        if uid not in self.cache:
            logger.error(f"Attempted to store PDF with unknown UID: {uid}")
            return
        self.cache[uid].update({
            'data': pdf_data,
            'timestamp': time.time(),
            'status': status,
        })
        pdf_data.seek(0)
        logger.info(f"Stored PDF: {uid} ({len(pdf_data.read())} bytes)")

    def init_store(self, pdf_name, status):
        uid = uuid4().hex
        self.cache[uid] = {
            'data': None,
            'filename': pdf_name,
            'timestamp': time.time(),
            'status': status,
            'message': '',
        }
        return uid, self.cache[uid]

    def get_pdf(self, pdf_id):
        """Retrieve PDF data if not expired"""
        if pdf_id not in self.cache:
            return None
        return self.cache[pdf_id]
