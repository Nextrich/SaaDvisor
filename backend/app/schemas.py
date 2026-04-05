#Created by Na9ash1 (ArtProgs), 2026
#Refactored by Krist1nA(created by Na9ash1 (Artprogs), 2024), 2026
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime


# Auth schemas
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int


# Business schemas
class BusinessCreate(BaseModel):
    name: str
    city: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    website: Optional[str] = ""
    business_type: Optional[str] = "other"


class BusinessUpdate(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    business_type: Optional[str] = None


class BusinessResponse(BaseModel):
    id: int
    name: str
    city: str
    phone: str
    email: str
    website: str
    business_type: str
    created_at: datetime

    class Config:
        from_attributes = True


# Search schemas
class SearchRequest(BaseModel):
    name: str
    city: Optional[str] = ""
    phone: Optional[str] = ""


class SearchResponse(BaseModel):
    business_id: int
    found_website: str
    found_social: Dict[str, str]
    confidence: str


# Audit schemas
class AuditResult(BaseModel):
    audit_id: int
    score: int
    recommendations: List[Dict[str, Any]]
    details: Dict[str, Any]
    created_at: datetime


# Monitoring schemas
class ScheduleRequest(BaseModel):
    interval_days: int = 7
    is_active: bool = True


class ScheduleResponse(BaseModel):
    message: str
    interval_days: int
    next_run: str


# Dashboard schemas
class DashboardBusiness(BaseModel):
    id: int
    name: str
    score: int
    last_check: Optional[datetime]
    top_advice: Optional[Dict[str, Any]]


class DashboardResponse(BaseModel):
    businesses: List[DashboardBusiness]
    total_score: float