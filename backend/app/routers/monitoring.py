#Created by Na9ash1 (ArtProgs), 2026
#Refactored by Krist1nA(created by Na9ash1 (Artprogs), 2024), 2026
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from .. import schemas, models, auth
from ..database import get_db

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.post("/{business_id}/schedule", response_model=schemas.ScheduleResponse)
def setup_monitoring(
        business_id: int,
        schedule_data: schemas.ScheduleRequest,
        current_user: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    # Проверяем бизнес
    business = db.query(models.Business).filter(
        models.Business.id == business_id,
        models.Business.user_id == current_user.id
    ).first()

    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    # Создаём или обновляем задачу
    task = db.query(models.ScheduledTask).filter(
        models.ScheduledTask.business_id == business_id
    ).first()

    if task:
        task.interval_days = schedule_data.interval_days
        task.is_active = schedule_data.is_active
    else:
        task = models.ScheduledTask(
            business_id=business_id,
            interval_days=schedule_data.interval_days,
            is_active=schedule_data.is_active
        )
        db.add(task)

    db.commit()

    return {
        "message": "Мониторинг настроен",
        "interval_days": schedule_data.interval_days,
        "next_run": f"Через {schedule_data.interval_days} дней"
    }


@router.get("/dashboard")
def get_dashboard(
        current_user: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    businesses = db.query(models.Business).filter(
        models.Business.user_id == current_user.id
    ).all()

    result = []
    total_score = 0

    for business in businesses:
        latest_audit = db.query(models.Audit).filter(
            models.Audit.business_id == business.id
        ).order_by(models.Audit.created_at.desc()).first()

        score = latest_audit.overall_score if latest_audit else 0
        total_score += score

        result.append({
            "id": business.id,
            "name": business.name,
            "score": score,
            "last_check": latest_audit.created_at if latest_audit else None,
            "top_advice": latest_audit.recommendations[0] if latest_audit and latest_audit.recommendations else None
        })

    return {
        "businesses": result,
        "total_score": total_score / len(result) if result else 0
    }