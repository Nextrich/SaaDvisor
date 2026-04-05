#Created by Na9ash1 (ArtProgs), 2026
#Refactored by Krist1nA(created by Na9ash1 (Artprogs), 2024), 2026
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, models, auth, services
from ..database import get_db

router = APIRouter(prefix="/businesses", tags=["Businesses"])


@router.get("/", response_model=List[schemas.BusinessResponse])
def get_businesses(
        current_user: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    businesses = db.query(models.Business).filter(
        models.Business.user_id == current_user.id
    ).all()
    return businesses


@router.post("/", response_model=schemas.BusinessResponse)
def create_business(
        business_data: schemas.BusinessCreate,
        current_user: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    db_business = models.Business(
        user_id=current_user.id,
        **business_data.model_dump()
    )
    db.add(db_business)
    db.commit()
    db.refresh(db_business)
    return db_business


@router.get("/{business_id}", response_model=schemas.BusinessResponse)
def get_business(
        business_id: int,
        current_user: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    business = db.query(models.Business).filter(
        models.Business.id == business_id,
        models.Business.user_id == current_user.id
    ).first()

    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    return business


@router.put("/{business_id}", response_model=schemas.BusinessResponse)
def update_business(
        business_id: int,
        business_data: schemas.BusinessUpdate,
        current_user: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    business = db.query(models.Business).filter(
        models.Business.id == business_id,
        models.Business.user_id == current_user.id
    ).first()

    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    for key, value in business_data.model_dump(exclude_unset=True).items():
        setattr(business, key, value)

    db.commit()
    db.refresh(business)
    return business


@router.delete("/{business_id}")
def delete_business(
        business_id: int,
        current_user: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    business = db.query(models.Business).filter(
        models.Business.id == business_id,
        models.Business.user_id == current_user.id
    ).first()

    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    db.delete(business)
    db.commit()

    return {"message": "Business deleted"}


@router.post("/search", response_model=schemas.SearchResponse)
async def search_business(
        search_data: schemas.SearchRequest,
        current_user: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    # Поиск информации
    info = await services.SearchService.find_business_info(search_data.name, search_data.city)

    # Создаём бизнес с найденной информацией
    business = models.Business(
        user_id=current_user.id,
        name=search_data.name,
        city=search_data.city,
        phone=search_data.phone,
        website=info['found_website']
    )
    db.add(business)
    db.commit()
    db.refresh(business)

    return {
        "business_id": business.id,
        "found_website": info['found_website'],
        "found_social": info['found_social'],
        "confidence": info['confidence']
    }


@router.get("/{business_id}/audits")
def get_business_audits(
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


@router.get("/{business_id}/audits")
def get_business_audits(
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