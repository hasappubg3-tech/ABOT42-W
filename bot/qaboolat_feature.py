"""
ميزة حاسبة القبول الجامعي
يقرأ البيانات من data/qaboolat.csv ويُرجع قائمة الكليات المتاحة بحسب المعدل والفرع.
"""
import csv
import os
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

# ── رقم الزر الذي يُشغّل الميزة ────────────────────────────────
QABOOLAT_BTN_ID = 9670

_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "qaboolat.csv")
_data_cache = None


# ── تحميل البيانات ───────────────────────────────────────────────
def _load_data() -> list:
    global _data_cache
    if _data_cache is not None:
        return _data_cache
    rows = []
    try:
        with open(_CSV_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    rows.append({
                        "university":  row["university"].strip(),
                        "college":     row["college"].strip(),
                        "department":  row["department"].strip(),
                        "branch":      row["branch"].strip(),
                        "min_grade":   float(row["min_grade"]),
                    })
                except (ValueError, KeyError):
                    continue
    except FileNotFoundError:
        pass
    _data_cache = rows
    return rows


def reload_data():
    """إعادة تحميل البيانات من الملف (بعد تحديث CSV)."""
    global _data_cache
    _data_cache = None
    return _load_data()


# ── بحث ─────────────────────────────────────────────────────────
def search_results(branch: str, grade: float) -> list:
    """يُرجع الكليات التي يُقبل فيها الطالب مرتبةً من أعلى معدل مطلوب للأدنى."""
    data = _load_data()
    results = [r for r in data if r["branch"] == branch and r["min_grade"] <= grade]
    results.sort(key=lambda r: r["min_grade"], reverse=True)
    return results


# ── تنسيق الرسالة ────────────────────────────────────────────────
def format_results(branch: str, grade: float, results: list) -> list[str]:
    """
    يُرجع قائمة برسائل جاهزة للإرسال (مقسّمة لتتجنب حد تيليغرام 4096 حرف).
    """
    if not results:
        return [
            f"😔 *لا توجد كليات متاحة لمعدل {grade:.2f} ({branch})*\n\n"
            "تأكد من إدخال المعدل بشكل صحيح، أو أن المعدل مرتفع بما يكفي."
        ]

    # تجميع حسب الجامعة
    by_uni: dict[str, list[str]] = {}
    for r in results:
        uni = r["university"]
        if uni not in by_uni:
            by_uni[uni] = []
        entry = r["college"]
        if r["department"]:
            entry += f" — {r['department']}"
        entry += f" *({r['min_grade']:.2f})*"
        by_uni[uni].append(entry)

    # بناء الرسالة الأولى (رأس + إحصاء)
    header = (
        f"🎓 *نتائج القبول — معدل {grade:.2f} ({branch})*\n"
        f"✅ عدد الكليات التي تُقبل فيها: *{len(results)}*\n"
        "——————————————"
    )

    chunks = []
    current_lines = [header]
    current_len = len(header)
    LIMIT = 3800  # هامش أمان أسفل 4096

    for uni, colleges in by_uni.items():
        block_lines = [f"\n🏛 *{uni}*"] + [f"  • {c}" for c in colleges]
        block_text = "\n".join(block_lines)

        if current_len + len(block_text) > LIMIT and len(current_lines) > 1:
            chunks.append("\n".join(current_lines))
            current_lines = [block_text]
            current_len = len(block_text)
        else:
            current_lines.append(block_text)
            current_len += len(block_text)

    if current_lines:
        current_lines.append("\n——————————————")
        current_lines.append("_البيانات للسنة الدراسية 2025/2026_")
        chunks.append("\n".join(current_lines))

    return chunks


# ── لوحة اختيار الفرع ────────────────────────────────────────────
def branch_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⚗️ علمي", callback_data="qab_branch_علمي"),
        InlineKeyboardButton("📚 أدبي", callback_data="qab_branch_أدبي"),
    ]])


# ── المُشغّل الرئيسي ─────────────────────────────────────────────
async def handle_qaboolat_trigger(m, ctx, uid):
    """يُرسل رسالة اختيار الفرع عند ضغط زر القبولات."""
    ctx.user_data.pop("qab_branch", None)
    ctx.user_data.pop("state", None)
    await m.reply_text(
        "🎓 *حاسبة القبول الجامعي*\n\n"
        "اختر فرعك الدراسي:",
        parse_mode="Markdown",
        reply_markup=branch_keyboard()
    )
