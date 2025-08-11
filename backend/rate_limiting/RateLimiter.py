## How to have greater control over Rate limits for LLM-API calling apps ## 


import time
import asyncio
from typing import Dict, List, Optional, Callable, Any 
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod 

class LimitType(Enum):
    REQUESTS = "requests"
    TOKENS = "tokens"



class RateLimiter(ABC):
    """Abstract base class defining the rate limiter interface"""
    
    @abstractmethod
    async def can_process_request(self, text: str, **kwargs) -> Dict[str, Any]: 
        """Check if a request can be processed"""
        pass
    
    @abstractmethod
    async def acquire_tokens(self, text: str, **kwargs) -> bool:
        """Actually consume tokens for a request"""
        pass
    
    @abstractmethod
    def record_actual_usage(self, actual_usage: Dict, text: str, **kwargs):
        """Record actual API usage"""
        pass
    
    @abstractmethod
    def get_usage_stats(self) -> Dict:
        """Get current usage statistics"""
        pass



@dataclass
class UsageRecord:
    chunk_length: int
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    timestamp: float
    model: str
    cost_estimate: float = 0.0


@dataclass
class RateLimitConfig:
    # Daily limits
    daily_request_limit: int
    daily_token_limit: int
    
    # Burst limits (token bucket)
    request_burst_capacity: int
    request_refill_rate: float  # requests per second
    token_burst_capacity: int
    token_refill_rate: float    # tokens per second
    
    # Estimation
    max_tokens_per_request: int
    safety_buffer: float = 0.1  # 10% buffer for estimates



class TokenBucket:
    """Thread-safe token bucket for burst rate limiting"""
    
    def __init__(self, capacity: int, refill_rate: float) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    def _refill(self):
        """Private method to refill tokens based on elapsed time"""
        now = time.time()
        time_since_refill = now - self.last_refill
        tokens_to_add = time_since_refill * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    async def consume(self, required_tokens: int) -> bool:
        """Consume tokens if available"""
        async with self._lock:
            self._refill()
            if self.tokens >= required_tokens:
                self.tokens -= required_tokens
                return True
            return False
    
    async def has_capacity(self, required_tokens: int) -> bool:
        """Check if tokens are available without consuming"""
        async with self._lock:
            self._refill()
            return self.tokens >= required_tokens
    
    async def get_available_tokens(self) -> float:
        """Get current token count"""
        async with self._lock:
            self._refill()
            return self.tokens


class LLMRateLimiter:
    """Generic rate limiter for LLM APIs with precise token tracking"""
    
    def __init__(self, config: RateLimitConfig, token_estimator: Optional[Callable[[str], int]] = None):
        self.config = config
        self.token_estimator = token_estimator or self._default_token_estimator
        
        # Daily usage tracking
        self.daily_requests_used = 0
        self.daily_tokens_used = 0
        self.daily_reset_time = self._get_next_daily_reset()
        
        # Token buckets for burst limiting
        self.request_bucket = TokenBucket(
            capacity=config.request_burst_capacity,
            refill_rate=config.request_refill_rate
        )
        self.token_bucket = TokenBucket(
            capacity=config.token_burst_capacity,
            refill_rate=config.token_refill_rate
        )
        
        # Usage history and analytics
        self.usage_history: List[UsageRecord] = []
        self._lock = asyncio.Lock()
    
    def _default_token_estimator(self, text: str) -> int:
        """Simple token estimation (roughly 4 chars per token)"""
        return max(1, len(text) // 4) + 30  # +30 for system prompts, etc.
    
    def _get_next_daily_reset(self) -> float:
        """Get timestamp for next daily reset (midnight UTC)"""
        now = time.time()
        # Reset at midnight UTC
        reset_time = (now // 86400 + 1) * 86400
        return reset_time
    
    async def _check_daily_reset(self):
        """Reset daily counters if needed"""
        if time.time() >= self.daily_reset_time:

            async with self._lock:
                self.daily_requests_used = 0
                self.daily_tokens_used = 0
                self.daily_reset_time = self._get_next_daily_reset()

    
    async def can_process_request(self, text: str, estimated_completion_tokens: int = 0) -> Dict[str, Any]:
        """
        Comprehensive pre-flight check
        Returns dict with 'allowed' bool and 'reason' for denial
        """
        await self._check_daily_reset()
        
        # Estimate token usage
        prompt_tokens = self.token_estimator(text) 
        total_estimated_tokens = prompt_tokens + estimated_completion_tokens
        
        # Add safety buffer
        buffered_tokens = int(total_estimated_tokens * (1 + self.config.safety_buffer))
        
        # Check daily limits
        if self.daily_requests_used >= self.config.daily_request_limit:
            return {"allowed": False, "reason": "daily_request_limit_exceeded"}
        
        if (self.daily_tokens_used + buffered_tokens) > self.config.daily_token_limit:
            return {"allowed": False, "reason": "daily_token_limit_exceeded"}
        
        # Check burst limits
        if not await self.request_bucket.has_capacity(1):
            return {"allowed": False, "reason": "request_rate_limit_exceeded"}
        
        if not await self.token_bucket.has_capacity(buffered_tokens):
            return {"allowed": False, "reason": "token_rate_limit_exceeded"}
        
        return {
            "allowed": True,
            "estimated_tokens": total_estimated_tokens,
            "buffered_tokens": buffered_tokens
        }


    async def acquire_tokens(self, text: str, estimated_completion_tokens: int = 0) -> bool:
        """
        Actually consume tokens from buckets (call before API request)
        """
        check_result = await self.can_process_request(text, estimated_completion_tokens)
        if not check_result["allowed"]:
            return False
        
        # Consume from buckets
        buffered_tokens = check_result["buffered_tokens"]
        
        request_acquired = await self.request_bucket.consume(1)
        token_acquired = await self.token_bucket.consume(buffered_tokens)
        
        if not (request_acquired and token_acquired):
            # This shouldn't happen if can_process_request was called first
            return False
        
        return True
    
    
    def record_actual_usage(self, actual_usage: Dict, text: str, model: str = "unknown"):
        """
        Record actual API usage for analytics and learning
        
        actual_usage should contain:
        - total_tokens: int
        - prompt_tokens: int (optional)
        - completion_tokens: int (optional)
        """
        total_tokens = actual_usage.get("total_tokens", 0)
        prompt_tokens = actual_usage.get("prompt_tokens", 0)
        completion_tokens = actual_usage.get("completion_tokens", 0)
        
        # Update daily counters with actual usage
        self.daily_requests_used += 1
        self.daily_tokens_used += total_tokens
        
        # Store detailed record
        record = UsageRecord(
            chunk_length=len(text),
            total_tokens=total_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            timestamp=time.time(),
            model=model
        )
        
        self.usage_history.append(record)
        
        # Trim history to last 1000 entries to prevent memory issues
        if len(self.usage_history) > 1000:
            self.usage_history = self.usage_history[-1000:]
    

    def get_usage_stats(self) -> Dict:
        """Get current usage statistics"""
        return {
            "daily_requests_used": self.daily_requests_used,
            "daily_tokens_used": self.daily_tokens_used,
            "daily_requests_remaining": max(0, self.config.daily_request_limit - self.daily_requests_used),
            "daily_tokens_remaining": max(0, self.config.daily_token_limit - self.daily_tokens_used),
            "total_recorded_requests": len(self.usage_history),
            "next_daily_reset": self.daily_reset_time
        }
    

    async def get_burst_capacity_stats(self) -> Dict:
        """Get current burst capacity"""
        return {
            "available_request_tokens": await self.request_bucket.get_available_tokens(),
            "available_token_capacity": await self.token_bucket.get_available_tokens(),
            "max_request_burst": self.config.request_burst_capacity,
            "max_token_burst": self.config.token_burst_capacity
        }
    

    def analyze_token_accuracy(self) -> Dict:
        """Analyze how accurate token estimates are"""
        if not self.usage_history:
            return {"error": "No usage data available"}
        
        # Compare estimated vs actual for recent requests
        recent_records = self.usage_history[-100:]  # Last 100 requests
        
        estimation_errors = []
        for record in recent_records:
            estimated = self.token_estimator(record.chunk_length * "x")  # Rough recreation
            actual = record.total_tokens
            error = abs(estimated - actual) / actual if actual > 0 else 0
            estimation_errors.append(error)
        
        avg_error = sum(estimation_errors) / len(estimation_errors)
        max_error = max(estimation_errors)
        
        return {
            "average_estimation_error": avg_error,
            "max_estimation_error": max_error,
            "sample_size": len(estimation_errors),
            "recommendation": "increase_buffer" if avg_error > 0.2 else "buffer_adequate"
        }
    

    