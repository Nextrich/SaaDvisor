#Created by Na9ash1 (ArtProgs), 2026
#Refactored by Krist1nA(created by Na9ash1 (Artprogs), 2024), 2026
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    businesses = relationship("Business", back_populates="user", cascade="all, delete-orphan")


class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, index=True)
    city = Column(String, default="")
    phone = Column(String, default="")
    email = Column(String, default="")
    website = Column(String, default="")
    business_type = Column(String, default="other")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="businesses")
    audits = relationship("Audit", back_populates="business", cascade="all, delete-orphan")
    schedules = relationship("ScheduledTask", back_populates="business", cascade="all, delete-orphan")


class Audit(Base):
    __tablename__ = "audits"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    status = Column(String, default="pending")  # pending, processing, done, error
    overall_score = Column(Integer, default=0)
    results = Column(JSON, default=dict)
    recommendations = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    business = relationship("Business", back_populates="audits")


class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    interval_days = Column(Integer, default=7)
    is_active = Column(Boolean, default=True)
    last_run = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    business = relationship("Business", back_populates="schedules")