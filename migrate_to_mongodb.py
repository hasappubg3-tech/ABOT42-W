"""
سكريبت ترحيل البيانات من SQLite إلى MongoDB
شغّله مرة واحدة فقط: python migrate_to_mongodb.py
"""
import os, sqlite3, logging
from pymongo import MongoClient

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

SQLITE_FILE = "data.db"
MONGODB_URI = os.environ.get("MONGODB_URI", "")

if not MONGODB_URI:
    raise SystemExit("❌ MONGODB_URI غير موجود في متغيرات البيئة!")
if not os.path.exists(SQLITE_FILE):
    raise SystemExit(f"❌ ملف SQLite '{SQLITE_FILE}' غير موجود!")

client = MongoClient(MONGODB_URI)
uri_path = MONGODB_URI.rsplit("@", 1)[-1]
db_name = uri_path.rsplit("/", 1)[-1].split("?")[0] if "/" in uri_path else ""
mdb = client[db_name] if db_name else client["botdb"]

sq = sqlite3.connect(SQLITE_FILE)
sq.row_factory = sqlite3.Row

def rows(query, *args):
    return [dict(r) for r in sq.execute(query, args).fetchall()]

def migrate_collection(col_name, data, id_field="id"):
    if not data:
        log.info(f"  ↳ {col_name}: فارغة، تخطي.")
        return
    col = mdb[col_name]
    col.delete_many({})
    col.insert_many(data)
    log.info(f"  ✅ {col_name}: {len(data)} سجل")

def set_counter(col_name, max_id):
    mdb["_counters"].update_one(
        {"_id": col_name}, {"$set": {"seq": max_id}}, upsert=True
    )

log.info("🚀 بدء الترحيل من SQLite إلى MongoDB...")

# ── admins ────────────────────────────────────────────────────────
admins = rows("SELECT id, username FROM admins")
migrate_collection("admins", admins)

# ── settings ──────────────────────────────────────────────────────
settings = rows("SELECT key, value FROM settings")
migrate_collection("settings", settings, id_field="key")

# ── buttons ───────────────────────────────────────────────────────
buttons = rows("SELECT * FROM buttons")
for b in buttons:
    for col in ("parent_id",):
        if b.get(col) == "" or b.get(col) is None:
            b[col] = None
migrate_collection("buttons", buttons)
max_btn = max((b["id"] for b in buttons), default=0)
set_counter("buttons", max_btn)

# ── content_items ─────────────────────────────────────────────────
items = rows("SELECT * FROM content_items")
migrate_collection("content_items", items)
max_ci = max((i["id"] for i in items), default=0)
set_counter("content_items", max_ci)

# ── caption_buttons ───────────────────────────────────────────────
cap_btns = rows("SELECT * FROM caption_buttons")
migrate_collection("caption_buttons", cap_btns)
max_cb = max((b["id"] for b in cap_btns), default=0)
set_counter("caption_buttons", max_cb)

# ── user_stats ────────────────────────────────────────────────────
user_stats = rows("SELECT * FROM user_stats")
migrate_collection("user_stats", user_stats, id_field="user_id")

# ── daily_stats ───────────────────────────────────────────────────
daily = rows("SELECT * FROM daily_stats")
migrate_collection("daily_stats", daily, id_field="date")

# ── user_button_clicks ────────────────────────────────────────────
clicks = rows("SELECT * FROM user_button_clicks")
migrate_collection("user_button_clicks", clicks)

# ── motivational_phrases ──────────────────────────────────────────
phrases = rows("SELECT * FROM motivational_phrases")
migrate_collection("motivational_phrases", phrases)
max_ph = max((p["id"] for p in phrases), default=0)
set_counter("motivational_phrases", max_ph)

# ── pomodoro_settings ─────────────────────────────────────────────
pom = rows("SELECT * FROM pomodoro_settings")
migrate_collection("pomodoro_settings", pom, id_field="user_id")

# ── item_ratings ──────────────────────────────────────────────────
iratings = rows("SELECT * FROM item_ratings")
migrate_collection("item_ratings", iratings)

# ── button_ratings ────────────────────────────────────────────────
bratings = rows("SELECT * FROM button_ratings")
migrate_collection("button_ratings", bratings)

# ── file_request_admins ───────────────────────────────────────────
fra = rows("SELECT * FROM file_request_admins")
migrate_collection("file_request_admins", fra, id_field="user_id")

# ── quiz_questions ────────────────────────────────────────────────
qq = rows("SELECT * FROM quiz_questions")
migrate_collection("quiz_questions", qq)
max_qq = max((q["id"] for q in qq), default=0)
set_counter("quiz_questions", max_qq)

# ── quiz_options ──────────────────────────────────────────────────
qo = rows("SELECT * FROM quiz_options")
migrate_collection("quiz_options", qo)
max_qo = max((q["id"] for q in qo), default=0)
set_counter("quiz_options", max_qo)

# ── quiz_sent_log ─────────────────────────────────────────────────
qsl = rows("SELECT * FROM quiz_sent_log")
migrate_collection("quiz_sent_log", qsl)

# ── exam_questions ────────────────────────────────────────────────
eq = rows("SELECT * FROM exam_questions")
migrate_collection("exam_questions", eq)
max_eq = max((q["id"] for q in eq), default=0)
set_counter("exam_questions", max_eq)

# ── exam_progress ─────────────────────────────────────────────────
ep = rows("SELECT * FROM exam_progress")
migrate_collection("exam_progress", ep)

sq.close()

# ── إنشاء الفهارس ─────────────────────────────────────────────────
log.info("🔧 إنشاء الفهارس...")
from pymongo import ASCENDING
mdb["buttons"].create_index([("id", ASCENDING)], unique=True)
mdb["buttons"].create_index([("parent_id", ASCENDING), ("ord", ASCENDING), ("id", ASCENDING)])
mdb["content_items"].create_index([("id", ASCENDING)], unique=True)
mdb["content_items"].create_index([("button_id", ASCENDING), ("ord", ASCENDING)])
mdb["admins"].create_index([("id", ASCENDING)], unique=True)
mdb["settings"].create_index([("key", ASCENDING)], unique=True)
mdb["user_stats"].create_index([("user_id", ASCENDING)], unique=True)
mdb["quiz_questions"].create_index([("id", ASCENDING)], unique=True)
mdb["quiz_options"].create_index([("id", ASCENDING)], unique=True)
mdb["exam_questions"].create_index([("id", ASCENDING)], unique=True)
mdb["exam_progress"].create_index([("user_id", ASCENDING), ("exam_button_id", ASCENDING)], unique=True)
mdb["item_ratings"].create_index([("item_id", ASCENDING), ("user_id", ASCENDING)], unique=True)
mdb["button_ratings"].create_index([("button_id", ASCENDING), ("user_id", ASCENDING)], unique=True)
mdb["daily_stats"].create_index([("date", ASCENDING)], unique=True)

log.info("✅ اكتمل الترحيل بنجاح!")
print("\n✅ تم نقل جميع البيانات إلى MongoDB بنجاح!")
