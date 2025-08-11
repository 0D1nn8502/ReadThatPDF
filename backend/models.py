from pydantic import BaseModel, Field, field_validator
from enum import Enum 
from typing import Optional, Literal, Union 
from zoneinfo import ZoneInfo 
from datetime import time 


## Scheduling options ##   
class ScheduleType(str, Enum): 
    DAILY = "daily" 
    TWICE_DAILY = "twice_daily" 
    EVERY_TWO_DAYS = "every_two_days" 
    MONTHLY = "monthly" 
    WEEKLY = "weekly" 
    NONE = "none" 



class ProcessingMode(str, Enum): 
    SCHEDULE_ONLY = "schedule_only"    # Only set up scheduling, no immediate processing
    IMMEDIATE_AND_SCHEDULE = "immediate_and_schedule"  # Both immediate + scheduling
    IMMEDIATE_ONLY = "immediate_only" 



class Chunk(BaseModel): 
    index: int 
    text: str 
    token_count: int 
    insight: Optional[str] = None 



class PDFRequest(BaseModel): 
    text: str 
    userId: str
    email: str 

    ## Processing control ## 
    processing_mode: ProcessingMode = Field(default=ProcessingMode.IMMEDIATE_AND_SCHEDULE) 
    immediate_chunks_count: int = Field(default=1, ge=0, le=2, description="Number of chunks to process immediately")

    ## Scheduling options ## 
    schedule_type: ScheduleType = Field(default=ScheduleType.DAILY)  
    schedule_time: Optional[str] = Field(default="09:00", description="Time in HH:MM format (24h)") 
    user_timezone: str = Field(default="Asia/Kolkata", description="Timezone for scheduling")
    chunks_per_delivery: int = Field(default=2, ge=1, le=5, description="Chunks to process per scheduled delivery")

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True  # This ensures enums are serialized as their values
    }

    
    @field_validator('schedule_time') 
    @classmethod
    def validate_time_format(cls, v): 
        if v is None: 
            return v 
        
        try: 
            # Parse the time string to validate format
            from datetime import datetime
            datetime.strptime(v, '%H:%M')
            return v 
        
        except ValueError:
            raise ValueError('Time must be in HH:MM format')
        

    @field_validator('user_timezone')
    @classmethod 
    def validate_timezone(cls, v): 
        if v is None:
            return v
        try: 
            # Validate timezone using ZoneInfo
            ZoneInfo(v) 
            return v
        except Exception: 
            raise ValueError(f'Invalid Timezone : {v}. Use IANA timezones like Asia/Kolkata, UTC and America/New_York')    


    @field_validator('processing_mode') 
    @classmethod
    def validate_processing_mode(cls, v): 
        # Ensure we return the value properly
        if isinstance(v, ProcessingMode):
            return v
        if isinstance(v, str):
            return ProcessingMode(v)
        return v
    
    def to_dict(self):
        """Custom serialization method for debugging"""
        return {
            "text": self.text,
            "userId": self.userId,
            "email": self.email,
            "processing_mode": self.processing_mode.value if isinstance(self.processing_mode, ProcessingMode) else self.processing_mode,
            "immediate_chunks_count": self.immediate_chunks_count,
            "schedule_type": self.schedule_type.value if isinstance(self.schedule_type, ScheduleType) else self.schedule_type,
            "schedule_time": self.schedule_time,
            "user_timezone": self.user_timezone,
            "chunks_per_delivery": self.chunks_per_delivery
        } 