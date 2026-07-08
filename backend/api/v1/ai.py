from fastapi import APIRouter, HTTPException, BackgroundTasks
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional
from datetime import date, timedelta
from uuid import UUID
import json

from core.deps import CurrentUser, DB
from core.config import settings
from models.project import Project, WBSItem, EarnedValueSnapshot
from models.core import DailyReport, Risk, AIRecommendation, ActualCost
from models.employee import Employee, Attendance

router = APIRouter()


class AnalysisRequest(BaseModel):
    project_id: Optional[UUID] = None
    analysis_type: str  # schedule | cost | productivity | risk | executive
    language: str = "ar"  # ar | en
    question: Optional[str] = None  # for free-form Q&A


async def _get_project_context(project_id: UUID, db) -> dict:
    """Gather all project data for AI context."""
    proj = await db.execute(select(Project).where(Project.id == project_id))
    project = proj.scalar_one_or_none()
    if not project:
        return {}

    # Schedule stats
    act_result = await db.execute(
        select(
            func.count().label("total"),
            func.count().filter(WBSItem.is_critical == True).label("critical"),
            func.avg(WBSItem.percent_complete).label("avg_progress"),
            func.count().filter(
                WBSItem.actual_finish.is_(None),
                WBSItem.planned_finish < date.today()
            ).label("overdue"),
            func.sum(WBSItem.total_float).label("total_float_sum"),
        ).where(WBSItem.project_id == project_id, WBSItem.is_activity == True)
    )
    act = act_result.first()

    # Critical path activities
    critical_acts = await db.execute(
        select(WBSItem.name, WBSItem.percent_complete, WBSItem.planned_finish, WBSItem.total_float)
        .where(WBSItem.project_id == project_id, WBSItem.is_critical == True)
        .order_by(WBSItem.planned_finish)
        .limit(10)
    )
    critical_list = [
        {
            "name": r.name,
            "progress": float(r.percent_complete or 0),
            "planned_finish": r.planned_finish.isoformat() if r.planned_finish else None,
            "float": r.total_float,
        }
        for r in critical_acts
    ]

    # Latest EV
    ev_result = await db.execute(
        select(EarnedValueSnapshot)
        .where(EarnedValueSnapshot.project_id == project_id)
        .order_by(EarnedValueSnapshot.snapshot_date.desc())
        .limit(1)
    )
    ev = ev_result.scalar_one_or_none()

    # Open risks
    risks_result = await db.execute(
        select(Risk.title, Risk.probability, Risk.impact, Risk.status)
        .where(Risk.project_id == project_id, Risk.status == "open")
        .limit(10)
    )
    open_risks = [{"title": r.title, "probability": r.probability, "impact": r.impact}
                  for r in risks_result]

    # Actual cost
    cost_result = await db.execute(
        select(func.sum(ActualCost.amount)).where(ActualCost.project_id == project_id)
    )
    total_cost = float(cost_result.scalar() or 0)

    # Recent reports
    reports_result = await db.execute(
        select(func.count())
        .where(DailyReport.project_id == project_id,
               DailyReport.report_date >= date.today() - timedelta(days=7))
    )
    reports_last_week = int(reports_result.scalar() or 0)

    return {
        "project": {
            "name": project.name,
            "name_ar": project.name_ar,
            "contract_number": project.contract_number,
            "client": project.client,
            "status": project.status,
            "start_date": project.start_date.isoformat() if project.start_date else None,
            "planned_end": project.planned_end_date.isoformat() if project.planned_end_date else None,
            "contract_value": float(project.contract_value or 0),
            "currency": project.currency,
            "data_date": date.today().isoformat(),
        },
        "schedule": {
            "total_activities": int(act.total or 0),
            "critical_activities": int(act.critical or 0),
            "overdue_activities": int(act.overdue or 0),
            "avg_progress": round(float(act.avg_progress or 0), 2),
            "critical_path": critical_list,
        },
        "cost": {
            "total_actual": total_cost,
            "contract_value": float(project.contract_value or 0),
            "spi": round(float(ev.spi or 1), 3) if ev else None,
            "cpi": round(float(ev.cpi or 1), 3) if ev else None,
            "bcws": float(ev.bcws or 0) if ev else None,
            "bcwp": float(ev.bcwp or 0) if ev else None,
            "acwp": float(ev.acwp or 0) if ev else None,
            "eac": float(ev.eac or 0) if ev else None,
        },
        "risks": {"open_count": len(open_risks), "items": open_risks},
        "reporting": {"reports_last_7_days": reports_last_week},
    }


async def _call_claude(system_prompt: str, user_message: str) -> str:
    """Call Claude API for AI analysis."""
    if not settings.ANTHROPIC_API_KEY:
        return "AI engine not configured. Please set ANTHROPIC_API_KEY."

    import anthropic
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    message = client.messages.create(
        model=settings.AI_MODEL,
        max_tokens=settings.AI_MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return message.content[0].text


SYSTEM_PROMPTS = {
    "en": """You are an expert Construction Project Management AI acting as:
- Senior Planning Engineer (P6 / CPM / schedule analysis)
- Commercial Manager (EVM, cost control, variations, cash flow)
- Project Director (risk management, executive decisions)

Analyze the provided project data and give:
1. Clear status assessment
2. Key issues and root causes
3. Specific actionable recommendations
4. Risk flags
5. Forecast / predictions

Be concise, data-driven, and professional. Use construction industry standards (PMBOK, PMI).
Format your response with clear sections.""",

    "ar": """أنت نظام ذكاء اصطناعي متخصص في إدارة مشاريع الإنشاء، تعمل بصفة:
- مهندس تخطيط أول (جداول زمنية، CPM، Primavera P6)
- مدير تجاري (تحليل القيمة المكتسبة، التكاليف، المطالبات)
- مدير مشاريع تنفيذي (إدارة المخاطر، القرارات الاستراتيجية)

قم بتحليل بيانات المشروع المقدمة وقدّم:
1. تقييم الوضع الحالي بوضوح
2. المشكلات الرئيسية وأسبابها
3. توصيات عملية ومحددة
4. تحذيرات المخاطر
5. التوقعات والتنبؤات

كن موجزاً ومبنياً على البيانات واحترافياً. استخدم معايير صناعة البناء.
نسّق إجابتك بأقسام واضحة باللغة العربية."""
}


@router.post("/analyze")
async def analyze_project(
    body: AnalysisRequest,
    current_user: CurrentUser,
    db: DB,
    background_tasks: BackgroundTasks,
):
    """Run AI analysis on a project."""
    lang = body.language if body.language in ("ar", "en") else "ar"
    system = SYSTEM_PROMPTS[lang]

    if body.project_id:
        ctx = await _get_project_context(body.project_id, db)
        if not ctx:
            raise HTTPException(status_code=404, detail="Project not found")
        context_str = json.dumps(ctx, ensure_ascii=False, indent=2)
    else:
        context_str = "{}"

    # Build user message
    if body.question:
        user_msg = f"Project Data:\n{context_str}\n\nQuestion: {body.question}"
    else:
        analysis_prompts = {
            "schedule": "Perform a complete schedule analysis. Identify delays, critical path issues, float consumption, and suggest recovery plans.",
            "cost": "Perform a complete cost and EVM analysis. Assess SPI, CPI, forecast at completion, cash flow risk.",
            "productivity": "Analyze manpower productivity, equipment utilization, and daily progress trends.",
            "risk": "Analyze open risks, identify missing risks, and propose mitigation strategies.",
            "executive": "Generate a comprehensive executive summary with KPIs, key decisions needed, and 30-day action plan.",
        }
        prompt = analysis_prompts.get(body.analysis_type, "Provide a general project health assessment.")
        user_msg = f"Project Data:\n{context_str}\n\nTask: {prompt}"

    response_text = await _call_claude(system, user_msg)

    # Save recommendation to DB in background
    if body.project_id:
        background_tasks.add_task(
            _save_recommendation,
            db_url=settings.DATABASE_SYNC_URL,
            project_id=body.project_id,
            category=body.analysis_type,
            content=response_text,
            lang=lang,
        )

    return {
        "analysis_type": body.analysis_type,
        "language": lang,
        "project_id": str(body.project_id) if body.project_id else None,
        "result": response_text,
        "generated_at": date.today().isoformat(),
    }


@router.get("/recommendations")
async def get_recommendations(current_user: CurrentUser, db: DB):
    """Get unacknowledged AI recommendations."""
    result = await db.execute(
        select(AIRecommendation)
        .where(AIRecommendation.acknowledged == False)
        .order_by(AIRecommendation.created_at.desc())
        .limit(50)
    )
    recs = result.scalars().all()

    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    return [
        {
            "id": str(r.id),
            "project_id": str(r.project_id) if r.project_id else None,
            "category": r.category,
            "title": r.title,
            "title_ar": r.title_ar,
            "recommendation": r.recommendation,
            "recommendation_ar": r.recommendation_ar,
            "priority": r.priority,
            "action_required": r.action_required,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in sorted(recs, key=lambda x: priority_order.get(x.priority, 99))
    ]


@router.post("/recommendations/{rec_id}/acknowledge")
async def acknowledge_recommendation(rec_id: UUID, current_user: CurrentUser, db: DB):
    """Mark a recommendation as acknowledged."""
    from datetime import datetime, timezone
    result = await db.execute(select(AIRecommendation).where(AIRecommendation.id == rec_id))
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    rec.acknowledged = True
    rec.acknowledged_by = current_user.id
    rec.acknowledged_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Acknowledged"}


@router.post("/chat")
async def ai_chat(body: AnalysisRequest, current_user: CurrentUser, db: DB):
    """Free-form AI chat about a project or general PM questions."""
    if not body.question:
        raise HTTPException(status_code=400, detail="Question is required for chat")

    lang = body.language if body.language in ("ar", "en") else "ar"
    ctx = {}
    if body.project_id:
        ctx = await _get_project_context(body.project_id, db)

    context_str = f"\nProject Data:\n{json.dumps(ctx, ensure_ascii=False)}\n" if ctx else ""
    user_msg = f"{context_str}\nQuestion: {body.question}"

    response = await _call_claude(SYSTEM_PROMPTS[lang], user_msg)
    return {"question": body.question, "answer": response, "language": lang}


async def _save_recommendation(db_url: str, project_id: UUID, category: str, content: str, lang: str):
    """Background task: save AI output as recommendation."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    engine = create_engine(db_url)
    with Session(engine) as session:
        rec = AIRecommendation(
            project_id=project_id,
            category=category,
            recommendation=content if lang == "en" else "",
            recommendation_ar=content if lang == "ar" else "",
            priority="medium",
        )
        session.add(rec)
        session.commit()
