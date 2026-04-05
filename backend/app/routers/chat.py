#Created by Na9ash1 (ArtProgs), 2026
#Refactored by Krist1nA(created by Na9ash1 (Artprogs), 2024), 2026
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import re
import ollama
from datetime import datetime

from .. import models, auth
from ..database import get_db

router = APIRouter(prefix="/chat", tags=["Chat"])


# Модели запросов/ответов
class ChatMessage(BaseModel):
    role: str  # 'user' или 'assistant'
    content: str


class ChatRequest(BaseModel):
    business_id: int
    message: str
    history: Optional[List[ChatMessage]] = []


class ChatResponse(BaseModel):
    response: str
    context_used: Dict[str, Any] = {}


# Сервис для работы с чатом
class ChatService:
    @staticmethod
    async def get_business_context(business_id: int, db: Session) -> Dict[str, Any]:
        """Получение контекста бизнеса из последнего аудита"""
        business = db.query(models.Business).filter(models.Business.id == business_id).first()
        if not business:
            return {"error": "Бизнес не найден"}

        # Получаем последний завершённый аудит
        latest_audit = db.query(models.Audit).filter(
            models.Audit.business_id == business_id,
            models.Audit.status == "done"
        ).order_by(models.Audit.created_at.desc()).first()

        context = {
            "business_name": business.name,
            "city": business.city or "не указан",
            "website": business.website or "не указан",
            "has_audit": latest_audit is not None
        }

        if latest_audit:
            context["audit_score"] = latest_audit.overall_score
            context["audit_date"] = latest_audit.created_at.strftime("%d.%m.%Y")

            # Извлекаем ключевые проблемы из аудита
            details = latest_audit.results or {}
            all_issues = []

            for key, result in details.items():
                if isinstance(result, dict) and result.get('issues'):
                    all_issues.extend(result['issues'])

            context["main_issues"] = all_issues[:5]  # Топ-5 проблем

            # Извлекаем рекомендации
            if latest_audit.recommendations:
                context["recommendations"] = latest_audit.recommendations[:3]

        return context

    @staticmethod
    def format_context_for_prompt(context: Dict[str, Any]) -> str:
        """Форматирование контекста для промпта"""
        if not context.get("has_audit"):
            return f"""
Бизнес: {context.get('business_name', 'Неизвестно')}
Город: {context.get('city', 'Не указан')}
Сайт: {context.get('website', 'Не указан')}

Аудит ещё не проводился. Предложи пользователю пройти бесплатный аудит бизнеса.
"""

        prompt = f"""
ИНФОРМАЦИЯ О БИЗНЕСЕ:
- Название: {context.get('business_name')}
- Город: {context.get('city')}
- Сайт: {context.get('website')}

РЕЗУЛЬТАТЫ АУДИТА (от {context.get('audit_date')}):
- Общая оценка: {context.get('audit_score')}/100

ОСНОВНЫЕ ПРОБЛЕМЫ:
"""
        for issue in context.get('main_issues', []):
            prompt += f"- {issue}\n"

        if context.get('recommendations'):
            prompt += "\nРАНЕЕ ДАННЫЕ РЕКОМЕНДАЦИИ:\n"
            for rec in context.get('recommendations', []):
                prompt += f"- {rec.get('title', 'Совет')}: {rec.get('description', '')[:100]}...\n"

        return prompt

    @staticmethod
    async def generate_response(
            business_name: str,
            user_message: str,
            context: str,
            history: List[Dict] = None
    ) -> str:
        """Генерация ответа через Ollama"""

        system_prompt = f"""Ты - AI-ассистент SaaDvisor, эксперт по цифровому маркетингу и развитию бизнеса.

{context}

ПРАВИЛА ОТВЕТОВ:
1. Отвечай на русском языке, дружелюбно и профессионально
2. Используй данные из контекста бизнеса (оценка, проблемы, город)
3. Давай конкретные, практичные советы
4. Если не знаешь ответа - честно скажи и предложи обратиться к поддержке
5. Будь краток, но информативен (2-4 предложения для простых вопросов)
6. Если пользователь спрашивает не про бизнес - вежливо направь в тему

Ты помогаешь предпринимателю {business_name} развивать бизнес в интернете.
"""

        messages = [
            {'role': 'system', 'content': system_prompt}
        ]

        # Добавляем историю (последние 5 сообщений)
        if history:
            for msg in history[-5:]:
                messages.append({'role': msg.get('role', 'user'), 'content': msg.get('content', '')})

        # Добавляем текущее сообщение
        messages.append({'role': 'user', 'content': user_message})

        try:
            response = ollama.chat(
                model='llama3',
                messages=messages,
                stream=False,
                options={
                    'temperature': 0.7,
                    'top_p': 0.9,
                    'max_tokens': 500
                }
            )
            return response['message']['content']
        except Exception as e:
            print(f"Ollama error: {e}")
            return await ChatService._generate_fallback_response(business_name, user_message, context)

    @staticmethod
    async def _generate_fallback_response(business_name: str, user_message: str, context: str) -> str:
        """Fallback ответы если Ollama недоступен"""
        user_message_lower = user_message.lower()

        # Определяем тему вопроса
        if any(word in user_message_lower for word in ['аудит', 'анализ', 'оценка', 'балл', 'score']):
            import re
            score_match = re.search(r'(\d+)/100', context)
            if score_match:
                score = score_match.group(1)
                return f"По результатам последнего аудита ваш бизнес набрал {score} баллов из 100. Основные проблемы: медленный сайт, плохая видимость в поиске и недостаточная активность в соцсетях. Хотите получить детальный план исправления?"
            return "Аудит вашего бизнеса показал несколько ключевых областей для улучшения: скорость сайта, SEO-оптимизация и присутствие в соцсетях. Рекомендую начать с ускорения сайта - это самый быстрый способ улучшить конверсию."

        elif any(word in user_message_lower for word in ['сайт', 'site', 'скорость', 'загрузка']):
            return "Скорость загрузки сайта критически важна для удержания клиентов. Рекомендую: 1) Оптимизировать изображения в WebP, 2) Включить кэширование, 3) Использовать CDN. Это может ускорить сайт на 30-50%."

        elif any(word in user_message_lower for word in ['seo', 'поиск', 'google', 'яндекс']):
            return "Для улучшения позиций в поиске: 1) Добавьте мета-теги на все страницы, 2) Создайте качественный контент с ключевыми словами, 3) Настройте карту сайта. Хотите получить чек-лист по SEO?"

        elif any(word in user_message_lower for word in ['vk', 'вк', 'соцсеть', 'сообщество']):
            return "Активное VK-сообщество увеличивает лояльность клиентов. Советую: публиковать посты 3-4 раза в неделю, отвечать на комментарии в течение часа, проводить конкурсы. Это повысит охват на 40%."

        elif any(word in user_message_lower for word in ['2гис', '2gis', 'карта', 'карты']):
            return "2ГИС - важный канал для локального бизнеса. Убедитесь, что карточка заполнена полностью: адрес, телефон, часы работы, фото. Попросите клиентов оставлять отзывы - это повышает доверие."

        else:
            return f"Спасибо за вопрос о {business_name}! Я могу помочь вам с:\n• Анализом сайта и SEO\n• Продвижением в соцсетях\n• Работой с 2ГИС\n• Увеличением продаж\n\nУточните, какая тема вас интересует?"


# Эндпоинты API
@router.post("/send")
async def send_message(
        request: ChatRequest,
        current_user: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    """Отправка сообщения в чат и получение ответа от ИИ"""

    # Проверяем, что бизнес принадлежит пользователю
    business = db.query(models.Business).filter(
        models.Business.id == request.business_id,
        models.Business.user_id == current_user.id
    ).first()

    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Бизнес не найден"
        )

    # Получаем контекст бизнеса
    context = await ChatService.get_business_context(request.business_id, db)
    formatted_context = ChatService.format_context_for_prompt(context)

    # Генерируем ответ
    history = [{"role": msg.role, "content": msg.content} for msg in request.history] if request.history else []

    response_text = await ChatService.generate_response(
        business_name=business.name,
        user_message=request.message,
        context=formatted_context,
        history=history
    )

    return ChatResponse(
        response=response_text,
        context_used={
            "business_name": business.name,
            "has_audit": context.get("has_audit", False),
            "audit_score": context.get("audit_score")
        }
    )


@router.get("/business/{business_id}/context")
async def get_business_context(
        business_id: int,
        current_user: models.User = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    """Получение контекста бизнеса для отображения в чате"""

    business = db.query(models.Business).filter(
        models.Business.id == business_id,
        models.Business.user_id == current_user.id
    ).first()

    if not business:
        raise HTTPException(status_code=404, detail="Бизнес не найден")

    context = await ChatService.get_business_context(business_id, db)

    return {
        "business_name": business.name,
        "city": business.city,
        "has_audit": context.get("has_audit", False),
        "audit_score": context.get("audit_score"),
        "main_issues": context.get("main_issues", [])[:3]
    }