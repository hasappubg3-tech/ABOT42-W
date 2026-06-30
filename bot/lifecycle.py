from .shared import *
from .study_sessions import ses_recover_active_rooms

# ── إعداد البوت ──────────────────────────────────────────────────
async def post_init(app):
    sid = os.environ.get("SUPER_ADMIN_ID", "").strip()
    if sid.isdigit() and not is_admin(int(sid)):
        add_admin(int(sid)); logging.info(f"Super admin {sid} added.")
    import datetime as _dt
    if sid.isdigit() or get_storage_channel_id():
        app.job_queue.run_daily(
            _auto_backup_job,
            time=_dt.time(hour=3, minute=0, tzinfo=_dt.timezone.utc),
            name="auto_backup"
        )
        logging.info("تم جدولة النسخ الاحتياطي التلقائي يومياً عند 03:00 UTC.")
    _setup_pomodoro_feature()
    logging.info("تم إعداد ميزة البومودورو.")
    ses_recover_active_rooms(app.job_queue)
    logging.info("تم التحقق من استئناف الجلسات النشطة.")
