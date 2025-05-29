from pdfserver.log import logger
from pdfserver.utils import TaskStatus
from uuid import uuid4
import asyncio
import time


class ExpiringPDFCache:
    def __init__(self, expiry_minutes=30):
        self.storage = {}
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
            key for key, pdf in self.storage.items()
            if current_time - pdf['timestamp'] > self.expiry_seconds
        ]

        for key in expired_keys:
            del self.storage[key]
            logger.info(f"Removed expired PDF: {key}")

        if expired_keys:
            logger.info(f"Cache cleanup: removed {len(expired_keys)} expired PDFs")

    def save_pdf(self, uid, filename, pdf_data):
        """Store PDF data with current timestamp"""
        if uid not in self.storage:
            logger.error(f"Attempted to store PDF with unknown UID: {uid}")
            return
        self.storage[uid]['filename'] = filename
        self.storage[uid]['status'] = TaskStatus.COMPLETED.value
        self.storage[uid]['timestamp'] = time.time()
        self.storage[uid]['data'] = pdf_data
        pdf_data.seek(0)
        logger.info(f"Stored PDF: {uid} ({len(pdf_data.read())} bytes)")

    def add(self):
        uid = uuid4().hex
        self.storage[uid] = {
            'data': None,
            'filename': '',
            'timestamp': time.time(),
            'status': TaskStatus.RUNNING.value,
            'message': '',
        }
        return uid, self.storage[uid]

    def get_pdf(self, pdf_id):
        """Retrieve PDF data if not expired"""
        if pdf_id not in self.storage:
            return None
        return self.storage[pdf_id]
