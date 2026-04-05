#Created by Na9ash1 (ArtProgs), 2026
#Refactored by Krist1nA(created by Na9ash1 (Artprogs), 2024), 2026
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from .. import schemas, models, auth, services
from ..database import get_db

router = APIRouter(prefix="/audit", tags=["Audit"])


async def run_audit_task(business_id: int, audit_id: int, db: Session):
    """Фоновая задача для аудита"""
    business = db.query(models.Business).filter(models.Business.id == business_id).first()
    audit = db.query(models.Audit).filter(models.Audit.id == audit_id).first()

    if not business or not audit:
        return

    try:
        audit.status = "processing"
        db.commit()

        # Запускаем проверки
        audit_results = await services.AuditService.run_full_audit(business)

        # Генерируем рекомендации
        recommendations = await services.LLMService.generate_advice(
            business.name,
            business.city,
            audit_results
        )

        # Сохраняем результаты
        audit.results = audit_results['details']
        audit.recommendations = recommendations
        audit.overall_score = audit_results['overall_score']
        audit.status = "done"
        audit.completed_at = func.now()
        db.commit()

    except Exception as e:
        audit.status = "error"
        audit.results = {"error": str(e)}
        db.commit()


@router.post("/{business_id}")
async def run_audit(
        business_id: int,
        background_tasks: BackgroundTasks,
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

    # Создаём запись аудита
    audit = models.Audit(
        business_id=business_id,
        status="pending"
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)

    # Запускаем аудит в фоне
    background_tasks.add_task(run_audit_task, business_id, audit.id, db)

    return {"audit_id": audit.id, "status": "started", "message": "Аудит запущен"}


@router.get("/{business_id}/results", response_model=schemas.AuditResult)
def get_audit_results(
        business_id: int,
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

    # Берём последний аудит
    latest_audit = db.query(models.Audit).filter(
        models.Audit.business_id == business_id
    ).order_by(models.Audit.created_at.desc()).first()

    if not latest_audit:
        raise HTTPException(status_code=404, detail="No audits found")

    return {
        "audit_id": latest_audit.id,
        "score": latest_audit.overall_score,
        "recommendations": latest_audit.recommendations,
        "details": latest_audit.results,
        "created_at": latest_audit.created_at
    }


@router.get("/business/{business_id}/all")
def get_all_audits(
        business_id: int,
        current_user: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    """Получение всех аудитов для бизнеса"""
    business = db.query(models.Business).filter(
        models.Business.id == business_id,
        models.Business.user_id == current_user.id
    ).first()

    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    audits = db.query(models.Audit).filter(
        models.Audit.business_id == business_id
    ).order_by(models.Audit.created_at.desc()).all()

    return [
        {
            "id": a.id,
            "score": a.overall_score,
            "status": a.status,
            "created_at": a.created_at,
            "completed_at": a.completed_at
        }
        for a in audits
    ]