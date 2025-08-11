# tasks_full.py
import os
import json
import time as time_module
import time
import logging
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Any, List

import redis
import aiohttp
from email.mime.text import MIMEText
import smtplib
from smtplib import SMTPException

from celery import Celery
# your project imports (models, scheduler, providers, rate limiter)
from models import PDFRequest, ProcessingMode, Chunk
from insights_api.providers_registry import INSIGHT_PROVIDERS
from rate_limiting.RateLimiter import LLMRateLimiter, RateLimitConfig
from scheduling import UserScheduler

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ---------------------------
# Env / SMTP config
# ---------------------------
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")
EMAIL_FROM = os.environ.get("EMAIL_FROM")
SEND_EMAIL_RETRY_DELAY = int(os.environ.get("SEND_EMAIL_RETRY_DELAY", "60"))

# ---------------------------
# Redis config
# ---------------------------

## Redis config ## 
redis_config = {
    'host': os.environ.get("REDIS_HOST", "localhost"),
    'port': int(os.environ.get("REDIS_PORT", 6379)),
    'db': int(os.environ.get("REDIS_DB", 0)),
    'max_connections': 20
}


## Redis client ## 
redis_client = redis.Redis(
    host=os.environ.get("REDIS_HOST", "localhost"),
    port=int(os.environ.get("REDIS_PORT", 6379)),
    db=int(os.environ.get("REDIS_DB", 0)),
    decode_responses=False,  # store bytes (we use json.dumps/loads)
    max_connections=20
)

# ---------------------------
# Simple text chunking (no external tokenizer needed)
# ---------------------------
MAX_CHARS_PER_CHUNK = int(os.environ.get("MAX_CHARS_PER_CHUNK", 4800))  # ~1200 tokens worth

def simple_chunk_text(text: str, max_chars: int = MAX_CHARS_PER_CHUNK) -> List[str]:
    """
    Simple text chunking based on character count and sentence boundaries.
    Aims to create chunks of roughly equal size while respecting sentence boundaries.
    """
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    current_pos = 0
    
    while current_pos < len(text):
        # Calculate the end position for this chunk
        end_pos = min(current_pos + max_chars, len(text))
        
        # If we're not at the end of the text, try to find a good breaking point
        if end_pos < len(text):
            # Look for sentence endings within the last 20% of the chunk
            search_start = max(current_pos + int(max_chars * 0.8), current_pos + 100)
            
            # Look for sentence endings (., !, ?, \n\n)
            for i in range(end_pos, search_start, -1):
                if text[i-1:i+1] in ['. ', '! ', '? '] or text[i-1:i+1] == '\n\n':
                    end_pos = i
                    break
            # If no sentence ending found, look for any period, newline, or space
            else:
                for i in range(end_pos, search_start, -1):
                    if text[i] in '.!?\n ':
                        end_pos = i + 1
                        break
        
        chunk = text[current_pos:end_pos].strip()
        if chunk:  # Only add non-empty chunks
            chunks.append(chunk)
        
        current_pos = end_pos
    
    return chunks

def estimate_token_count(text: str) -> int:
    """
    Simple token count estimation: roughly 4 characters per token for English text.
    This is a reasonable approximation for most use cases.
    """
    return max(1, len(text) // 4)

# ---------------------------
# Rate limiter config & objects
# ---------------------------
ratelimitconfig = RateLimitConfig(
    daily_request_limit=1000,
    daily_token_limit=200000,
    request_burst_capacity=5,
    request_refill_rate=0.5,
    token_burst_capacity=8000,
    token_refill_rate=1000,
    max_tokens_per_request=1700,
    safety_buffer=0.1
)

groq_rate_limiter = LLMRateLimiter(config=ratelimitconfig)
groq_semaphore = asyncio.Semaphore(ratelimitconfig.request_burst_capacity)

# ---------------------------
# Celery app
# ---------------------------
readpdf_app = Celery(
    "server",
    broker=os.environ.get("CELERY_BROKER", "redis://localhost:6379/0"),
    backend=os.environ.get("CELERY_BACKEND", "redis://localhost:6379/1"),
)

readpdf_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=os.environ.get("CELERY_TZ", "Asia/Kolkata"),
    enable_utc=False
)

# ---------------------------
# User scheduler instance (your existing implementation)
# ---------------------------
user_scheduler = UserScheduler(readpdf_app, redis_config) 

def setup_user_schedule(user_data: dict):
    return user_scheduler.setup_user_schedule(user_data)

# ---------------------------
# Helper utils
# ---------------------------
def _get_redis_json(key: str):
    raw = redis_client.get(key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None

def _set_redis_json(key: str, value: Any, ex_days: int = 30):
    redis_client.setex(key, timedelta(days=ex_days), json.dumps(value, default=str))

# ---------------------------
# Task: create_chunks_and_process
# ---------------------------
@readpdf_app.task(bind=True)
def create_chunks_and_process(self, request_data: dict):
    """
    Create chunks and handle immediate processing + scheduling setup
    """
    try:
        validated = PDFRequest(**request_data)

        text = validated.text
        user_id = validated.userId
        email = validated.email
        processing_mode = validated.processing_mode
        immediate_chunks_count = validated.immediate_chunks_count

        # Create chunks using simple text chunking
        chunk_texts = simple_chunk_text(text, MAX_CHARS_PER_CHUNK)
        chunks: List[Chunk] = []
        
        for i, chunk_text in enumerate(chunk_texts):
            chunks.append(Chunk(
                index=i,
                text=chunk_text,
                token_count=estimate_token_count(chunk_text)
            ))

            self.update_state(
                state="PROGRESS",
                meta={
                    "current": i + 1,
                    "total": len(chunk_texts),
                    "status": f"Creating chunk {i + 1} of {len(chunk_texts)}"
                }
            )

        user_data = {
            "user_id": user_id,
            "email": email,
            "chunks": [c.model_dump() for c in chunks],
            "processing_mode": processing_mode,
            "immediate_chunks_count": immediate_chunks_count,
            "schedule_type": request_data.get("schedule_type"),
            "schedule_time": request_data.get("schedule_time"),
            "user_timezone": request_data.get("user_timezone", "Asia/Kolkata"),
            "chunks_per_delivery": request_data.get("chunks_per_delivery", 2),
            "created_at": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(),
            "total_chunks": len(chunks),
            "processed_count": 0,
            "current_index": 0
        }

        # Store in Redis
        _set_redis_json(f"user_chunks:{user_id}", user_data, ex_days=30)

        results = {
            "status": "completed",
            "total_chunks": len(chunks),
            "chunks_processed_immediately": 0,
            "schedule_set": False,
            "immediate_task_id": None
        }

        # Immediate processing
        if processing_mode in [ProcessingMode.IMMEDIATE_ONLY, ProcessingMode.IMMEDIATE_AND_SCHEDULE]:
            if immediate_chunks_count > 0:
                serializable_chunks = [c.model_dump() for c in chunks]
                task = generate_insights.delay(userId=user_id, chunks=serializable_chunks)
                results["chunks_processed_immediately"] = immediate_chunks_count
                results["immediate_task_id"] = task.id

        # Scheduling setup
        if processing_mode in [ProcessingMode.SCHEDULE_ONLY, ProcessingMode.IMMEDIATE_AND_SCHEDULE]:
            schedule_success = setup_user_schedule(user_data)
            results["schedule_set"] = schedule_success

        return results

    except Exception as exc:
        self.update_state(state="FAILURE", meta={"error": str(exc)})
        logger.exception("create_chunks_and_process failed")
        raise

# ---------------------------
# Task: generate_insights
# ---------------------------
@readpdf_app.task(bind=True, max_retries=2)
def generate_insights(self, *, userId: str, chunks: list, provider: str = "groq"):
    """
    Generate insights for chunks, store them in Redis, and enqueue send_email_chunk for each processed chunk.
    """
    task_id = self.request.id
    logger.info(f"[generate_insights:{task_id}] Starting for user {userId} - {len(chunks)} chunks")

    provider_fn = INSIGHT_PROVIDERS.get(provider)
    if not provider_fn:
        raise ValueError(f"Unsupported provider: {provider}")

    async def process_chunk(chunk):
        chunk_index = chunk["index"] if isinstance(chunk, dict) else chunk.index
        text = chunk["text"] if isinstance(chunk, dict) else chunk.text

        logger.debug(f"[generate_insights:{task_id}] Processing chunk {chunk_index}")

        # Rate limiter check
        check = await groq_rate_limiter.can_process_request(text, estimated_completion_tokens=500)
        if not check["allowed"]:
            return {"chunk_index": chunk_index, "error": f"Rate limit hit: {check['reason']}"}

        async with groq_semaphore:
            acquired = await groq_rate_limiter.acquire_tokens(text, estimated_completion_tokens=500)
            if not acquired:
                return {"chunk_index": chunk_index, "error": "Token acquisition failed"}

        retries = 2
        for attempt in range(retries):
            try:
                insight, usage = await provider_fn(
                    text=text,
                    rate_limiter=groq_rate_limiter,
                    system_prompt="You are an AI assistant providing insights."
                )
                groq_rate_limiter.record_actual_usage(
                    actual_usage=usage, text=text, model=usage.get("model", "unknown")
                )
                return {"chunk_index": chunk_index, "insight": insight, "usage": usage}
            except aiohttp.ClientResponseError as e:
                if e.status == 429 and attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return {"chunk_index": chunk_index, "error": f"HTTP {e.status}"}
            except Exception as e:
                return {"chunk_index": chunk_index, "error": str(e)}

    async def process_all_chunks():
        tasks = []
        total_chunks = len(chunks)
        for idx, chunk in enumerate(chunks, start=1):
            self.update_state(
                state="PROGRESS",
                meta={"current": idx, "total": total_chunks, "status": f"Queued chunk {idx}/{total_chunks}"}
            )
            tasks.append(process_chunk(chunk))
        return await asyncio.gather(*tasks, return_exceptions=False)

    # Run the async processing
    insights_results = asyncio.run(process_all_chunks())

    # Merge with existing results in Redis (so batches don't overwrite earlier batches)
    key = f"user_insights:{userId}"
    existing = _get_redis_json(key)
    if existing and isinstance(existing, list):
        existing_map = {r.get("chunk_index"): r for r in existing}
    else:
        existing_map = {}

    # update entries
    for r in insights_results:
        existing_map[r.get("chunk_index")] = r

    final_results = [existing_map[k] for k in sorted(existing_map.keys())]
    _set_redis_json(key, final_results, ex_days=30)

    logger.info(f"[generate_insights:{task_id}] Stored {len(final_results)} total insights for user {userId}")

    # Enqueue email tasks for each chunk processed in this invocation.
    for item in insights_results:
        chunk_index = item.get("chunk_index")
        # pass chunk_index and let send_email_chunk pull chunk text + insight from redis
        send_email_chunk.delay(user_id=userId, chunk_index=chunk_index, parent_task_id=task_id)

    return {
        "status": "completed",
        "task_id": task_id,
        "processed": len(insights_results),
        "total_stored": len(final_results)
    }

# ---------------------------
# Task: process_scheduled_chunks
# ---------------------------
@readpdf_app.task(bind=True)
def process_scheduled_chunks(self, user_id: str, chunks_per_delivery: int = 1, start_index: int = 0):
    start_time = time.time()
    try:
        all_chunks_data = user_scheduler.get_user_chunks(user_id)
        if not all_chunks_data:
            user_scheduler.cleanup_user_schedule(user_id)
            logger.warning(f"No chunks found for user {user_id}, schedule removed")
            return {"status": "user_data_not_found", "action": "schedule_removed"}

        user_data_key = f"user_chunks:{user_id}"
        raw = redis_client.get(user_data_key)
        if not raw:
            user_scheduler.cleanup_user_schedule(user_id)
            return {"status": "user_data_not_found", "action": "schedule_removed"}

        user_data = json.loads(raw)
        # just sanity: ensure chunks stored in user_data
        all_chunks = user_data.get("chunks", [])
        if not all_chunks:
            user_scheduler.cleanup_user_schedule(user_id)
            return {"status": "user_data_not_found", "action": "schedule_removed"}

        progress = user_scheduler.get_user_processing_state(user_id, start_index)
        current_index = progress.get("current_index", 0)
        processed_count = progress.get("processed_count", 0)

        end_index = min(current_index + chunks_per_delivery, len(all_chunks))
        chunks_to_process = all_chunks[current_index:end_index]

        if not chunks_to_process:
            user_scheduler.cleanup_user_schedule(user_id)
            execution_time = time.time() - start_time
            user_scheduler.metrics.record_schedule_execution(user_id, 0, execution_time)
            logger.info(f"All chunks processed for user {user_id}, schedule completed")
            return {"status": "completed", "total_processed": processed_count, "action": "schedule_removed"}

        # Enqueue generate_insights as an async task, capture task id
        serializable_chunks = [c if isinstance(c, dict) else c.model_dump() for c in chunks_to_process]
        task = generate_insights.delay(userId=user_id, chunks=serializable_chunks)
        logger.info(f"[process_scheduled_chunks] enqueued generate_insights {task.id} for user {user_id}")

        # Update progress with the async task id for monitoring/tracing
        new_processed_count = processed_count + len(chunks_to_process)
        user_scheduler.update_user_progress(user_id, end_index, new_processed_count, task.id)

        # Record metrics
        execution_time = time.time() - start_time
        user_scheduler.metrics.record_schedule_execution(user_id, len(chunks_to_process), execution_time)

        logger.info(f"Queued generate_insights {task.id} for user {user_id}: {len(chunks_to_process)} chunks")

        return {
            "status": "batch_queued",
            "chunks_queued": len(chunks_to_process),
            "generate_insights_task_id": task.id,
            "batch_range": f"{current_index}-{end_index-1}",
            "total_processed": new_processed_count,
            "remaining": len(all_chunks) - end_index,
            "execution_time": execution_time
        }

    except Exception as exc:
        execution_time = time.time() - start_time
        user_scheduler.metrics.record_error("task_execution_error", user_id, str(exc))
        logger.error(f"Error processing scheduled chunks for user {user_id}: {exc}", exc_info=True)
        self.update_state(state="FAILURE", meta={"error": str(exc)})
        raise

# ---------------------------
# Task: send_email_chunk
# ---------------------------
@readpdf_app.task(bind=True, max_retries=3, default_retry_delay=SEND_EMAIL_RETRY_DELAY)
def send_email_chunk(self, user_id: str, chunk_index: int, parent_task_id: str):
    """
    Sends the chunk (and its insight) to the user's email.
    Uses an idempotency key in Redis to avoid double-sends.
    """
    task_id = self.request.id
    marker_key = f"email_sent:{user_id}:{chunk_index}"

    # Idempotency: if this chunk was already emailed, return
    if redis_client.get(marker_key):
        logger.info(f"[send_email_chunk:{task_id}] Already sent for user {user_id}, chunk {chunk_index}")
        return {"status": "already_sent", "task_id": task_id, "user_id": user_id, "chunk_index": chunk_index}

    try:
        # Read user chunks (to get chunk.text) and insights
        user_chunks_raw = redis_client.get(f"user_chunks:{user_id}")
        if not user_chunks_raw:
            raise ValueError("user_chunks not found in redis")

        all_user_data = json.loads(user_chunks_raw)
        chunks = all_user_data.get("chunks", [])
        if chunk_index >= len(chunks):
            raise IndexError("chunk_index out of range")

        chunk = chunks[chunk_index]
        chunk_text = chunk.get("text", "")

        insights_raw = redis_client.get(f"user_insights:{user_id}")
        insight_text = ""
        if insights_raw:
            insights_list = json.loads(insights_raw)
            # find matching entry for this chunk_index
            for entry in insights_list:
                if entry.get("chunk_index") == chunk_index:
                    insight_text = entry.get("insight", "") or entry.get("error", "")
                    break

        # Build email
        subject = "Your Scheduled Reading Chunk"
        body = f"{chunk_text}\n\n---\nInsights:\n{insight_text}"

        # Get recipient email from stored user data (safe)
        to_email = all_user_data.get("email")
        if not to_email:
            raise ValueError("user email not found")

        # Simple SMTP send (production: use a transactional email provider + TLS + pooled connections)
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = EMAIL_FROM
        msg["To"] = to_email

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            if SMTP_USER and SMTP_PASS:
                server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(msg["From"], [msg["To"]], msg.as_string())

        # mark as sent (set expiry for marker)
        redis_client.setex(marker_key, timedelta(days=30), "1")

        logger.info(f"[send_email_chunk:{task_id}] Email sent user={user_id} chunk={chunk_index} parent={parent_task_id}")
        return {"status": "sent", "task_id": task_id, "user_id": user_id, "chunk_index": chunk_index}

    except (SMTPException, Exception) as exc:
        logger.error(f"[send_email_chunk:{task_id}] Failed email for user {user_id} chunk {chunk_index}: {exc}", exc_info=True)
        # Retry with exponential backoff via Celery
        raise self.retry(exc=exc)

# ---------------------------
# Maintenance tasks
# ---------------------------
@readpdf_app.task
def cleanup_expired_schedules():
    """Periodic cleanup task - add to beat schedule"""
    return user_scheduler.cleanup_expired_data()

@readpdf_app.task
def scheduler_health_check():
    """Health check task for monitoring"""
    return user_scheduler.health_check()
