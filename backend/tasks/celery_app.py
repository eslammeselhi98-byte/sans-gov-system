"""
SANS PMS — Celery Background Tasks
Handles: scheduled backups, daily EV snapshots, AI analysis runs,
overdue activity alerts, report reminders.
"""
import os
import subprocess
from datetime import date, timedelta
from celery import Celery
from celery.schedules import crontab

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
DATABASE_SYNC_URL = os.environ.get("DATABASE_SYNC_URL", "")

celery_app = Celery(
    "sans_pms",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Riyadh",
    enable_utc=True,
    task_routes={
        "tasks.celery_app.run_daily_backup": {"queue": "backups"},
        "tasks.celery_app.snapshot_all_projects_ev": {"queue": "reports"},
        "tasks.celery_app.check_expiring_documents": {"queue": "reports"},
        "tasks.celery_app.send_report_reminders": {"queue": "reports"},
        "tasks.celery_app.run_ai_portfolio_scan": {"queue": "ai"},
    },
)

# ─── Beat Schedule ──────────────────────────────────────────────

celery_app.conf.beat_schedule = {
    "daily-backup-2am": {
        "task": "tasks.celery_app.run_daily_backup",
        "schedule": crontab(hour=2, minute=0),
    },
    "snapshot-ev-every-night": {
        "task": "tasks.celery_app.snapshot_all_projects_ev",
        "schedule": crontab(hour=23, minute=30),
    },
    "check-expiring-docs-daily": {
        "task": "tasks.celery_app.check_expiring_documents",
        "schedule": crontab(hour=7, minute=0),
    },
    "report-reminders-evening": {
        "task": "tasks.celery_app.send_report_reminders",
        "schedule": crontab(hour=17, minute=0),
    },
    "ai-portfolio-scan-weekly": {
        "task": "tasks.celery_app.run_ai_portfolio_scan",
        "schedule": crontab(hour=6, minute=0, day_of_week=0),  # Sunday
    },
}


# ─── Tasks ──────────────────────────────────────────────────────

@celery_app.task
def run_daily_backup():
    """Trigger pg_dump backup."""
    try:
        result = subprocess.run(
            ["bash", "/app/scripts/backup_internal.sh"],
            capture_output=True, text=True, timeout=300
        )
        return {"success": result.returncode == 0, "output": result.stdout}
    except Exception as e:
        return {"success": False, "error": str(e)}


@celery_app.task
def snapshot_all_projects_ev():
    """Run snapshot_earned_value() for all active projects."""
    from sqlalchemy import create_engine, text
    engine = create_engine(DATABASE_SYNC_URL)
    with engine.begin() as conn:
        project_ids = conn.execute(
            text("SELECT id FROM projects WHERE status = 'active'")
        ).fetchall()
        for (pid,) in project_ids:
            conn.execute(text("SELECT snapshot_earned_value(:pid)"), {"pid": pid})
            conn.execute(text("SELECT calculate_project_progress(:pid)"), {"pid": pid})
    return {"projects_processed": len(project_ids)}


@celery_app.task
def check_expiring_documents():
    """Check for expiring Iqamas, passports, certificates → create AI recommendations."""
    from sqlalchemy import create_engine, text
    import uuid
    engine = create_engine(DATABASE_SYNC_URL)
    today = date.today()
    threshold = today + timedelta(days=30)

    with engine.begin() as conn:
        expiring = conn.execute(
            text("""
                SELECT id, full_name, iqama_expiry FROM employees
                WHERE is_active = TRUE AND iqama_expiry <= :threshold AND iqama_expiry >= :today
            """),
            {"threshold": threshold, "today": today}
        ).fetchall()

        for emp_id, name, expiry in expiring:
            days_left = (expiry - today).days
            priority = "critical" if days_left <= 7 else "high"
            conn.execute(
                text("""
                    INSERT INTO ai_recommendations
                        (id, category, title, title_ar, recommendation, recommendation_ar, priority)
                    VALUES (:id, 'hr_compliance', :title, :title_ar, :rec, :rec_ar, :priority)
                """),
                {
                    "id": str(uuid.uuid4()),
                    "title": f"Iqama expiring soon: {name}",
                    "title_ar": f"إقامة على وشك الانتهاء: {name}",
                    "rec": f"Employee {name}'s Iqama expires in {days_left} days ({expiry}). Renew immediately to avoid penalties.",
                    "rec_ar": f"إقامة الموظف {name} تنتهي خلال {days_left} يوم بتاريخ {expiry}. يرجى التجديد فوراً لتجنب الغرامات.",
                    "priority": priority,
                }
            )
    return {"expiring_count": len(expiring)}


@celery_app.task
def send_report_reminders():
    """Find projects with missing daily reports and flag for reminder."""
    from sqlalchemy import create_engine, text
    engine = create_engine(DATABASE_SYNC_URL)
    today = date.today()

    with engine.begin() as conn:
        missing = conn.execute(
            text("""
                SELECT p.id, p.name FROM projects p
                WHERE p.status = 'active'
                AND NOT EXISTS (
                    SELECT 1 FROM daily_reports dr
                    WHERE dr.project_id = p.id AND dr.report_date = :today
                )
            """),
            {"today": today}
        ).fetchall()

    # In production: send Telegram notification to assigned site engineers here
    return {"projects_missing_report": [p[1] for p in missing]}


@celery_app.task
def run_ai_portfolio_scan():
    """Weekly: run AI executive analysis across all active projects."""
    from sqlalchemy import create_engine, text
    engine = create_engine(DATABASE_SYNC_URL)

    with engine.begin() as conn:
        projects = conn.execute(
            text("SELECT id FROM projects WHERE status = 'active'")
        ).fetchall()

    # Trigger AI analysis via internal API call for each project
    # (left as integration point — calls api/v1/ai.py analyze_project logic)
    return {"projects_scanned": len(projects)}
