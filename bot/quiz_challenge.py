from .shared import *
import time as _time
import uuid as _uuid
import asyncio as _asyncio

# ── إدارة جلسات التحدي (في ذاكرة البوت) ─────────────────────────
def _challenges(ctx) -> dict:
    return ctx.bot_data.setdefault("challenge_sessions", {})

def create_challenge_session(ctx, challenger_uid: int, challenger_name: str,
                              challenger_chat_id: int, bid: int,
                              question_limit=None) -> str:
    """ينشئ جلسة تحدي جديدة ويُرجع معرّفها."""
    import random as _rnd
    challenge_id = _uuid.uuid4().hex[:12]
    all_qs = get_quiz_questions(bid)
    if question_limit and question_limit < len(all_qs):
        picked = _rnd.sample(all_qs, question_limit)
    else:
        picked = list(all_qs)
    b = get_btn(bid)
    session = {
        "id": challenge_id,
        "bid": bid,
        "quiz_label": b["label"] if b else "كويز",
        "questions": [q["id"] for q in picked],
        "challenger": {"uid": challenger_uid, "chat_id": challenger_chat_id, "name": challenger_name},
        "challenged": None,
        "status": "pending",
        "current_idx": 0,
        "scores": {str(challenger_uid): 0},
        "current_answers": {},
        "advance_task": None,
        "advancing": False,
    }
    _challenges(ctx)[challenge_id] = session
    return challenge_id

def get_challenge_session(ctx, challenge_id: str):
    return _challenges(ctx).get(challenge_id)

# ── شاشة اختيار وضع الكويز ───────────────────────────────────────
async def send_quiz_mode_select(m, bid):
    b = get_btn(bid)
    title = b["label"] if b else "الكويز"
    qs = get_quiz_questions(bid)
    count_text = f"_{len(qs)} سؤال_" if qs else "_لا توجد أسئلة_"
    await m.reply_text(
        f"📊 *{title}*\n{count_text}\n\nكيف تريد أداء الاختبار؟",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("👤 بمفردي", callback_data=f"quiz_solo_{bid}"),
            InlineKeyboardButton("⚔️ تحدي شخص", callback_data=f"quiz_ch_{bid}"),
        ]])
    )

# ── إرسال سؤال التحدي لكلا الطرفين ──────────────────────────────
async def send_challenge_question_to_both(bot, ctx, challenge_id: str):
    session = get_challenge_session(ctx, challenge_id)
    if not session or session["status"] != "active":
        return
    idx = session["current_idx"]
    total_q = len(session["questions"])
    if idx >= total_q:
        await finish_challenge(bot, ctx, challenge_id)
        return
    qid = session["questions"][idx]
    question = get_quiz_question(qid)
    opts = get_quiz_options(qid)
    if not question or len(opts) < 2:
        session["current_idx"] += 1
        await send_challenge_question_to_both(bot, ctx, challenge_id)
        return
    correct_idx = question.get("correct_option", 0)
    if correct_idx >= len(opts):
        correct_idx = 0
    session["current_answers"] = {}
    session["advancing"] = False
    prev_task = session.get("advance_task")
    current_task = _asyncio.current_task()
    if prev_task and not prev_task.done() and prev_task is not current_task:
        prev_task.cancel()
    header = f"⚔️ *سؤال {idx + 1} / {total_q}*"
    for role in ("challenger", "challenged"):
        p = session[role]
        if not p:
            continue
        try:
            await bot.send_message(p["chat_id"], header, parse_mode="Markdown")
            sent_poll = await bot.send_poll(
                chat_id=p["chat_id"],
                question=question["question"],
                options=[o["text"] for o in opts],
                type="quiz",
                correct_option_id=correct_idx,
                is_anonymous=False,
            )
            ctx.bot_data.setdefault("quiz_poll_map", {})[sent_poll.poll.id] = {
                "user_id": p["uid"],
                "chat_id": p["chat_id"],
                "bid": session["bid"],
                "qid": qid,
                "correct_idx": correct_idx,
                "challenge_id": challenge_id,
            }
        except Exception as e:
            logging.warning(f"تعذّر إرسال سؤال التحدي لـ {p['uid']}: {e}")
    session["advance_task"] = _asyncio.create_task(
        _timeout_advance(bot, ctx, challenge_id, timeout=90)
    )

async def _timeout_advance(bot, ctx, challenge_id: str, timeout: int):
    """يتقدم تلقائياً بعد انتهاء وقت السؤال."""
    await _asyncio.sleep(timeout)
    session = get_challenge_session(ctx, challenge_id)
    if not session or session["status"] != "active" or session.get("advancing"):
        return
    for role in ("challenger", "challenged"):
        p = session[role]
        if p and str(p["uid"]) not in session.get("current_answers", {}):
            try:
                await bot.send_message(p["chat_id"], "⏰ انتهى وقت السؤال!")
            except Exception:
                pass
    await _compute_and_advance(bot, ctx, challenge_id, delay=2)

# ── معالجة إجابة في وضع التحدي ────────────────────────────────────
async def handle_challenge_answer(bot, ctx, challenge_id: str,
                                   uid: int, selected: int, correct_idx: int):
    session = get_challenge_session(ctx, challenge_id)
    if not session or session["status"] != "active":
        return
    uid_key = str(uid)
    if uid_key in session["current_answers"]:
        return
    session["current_answers"][uid_key] = {
        "correct": (selected == correct_idx),
        "time": _time.time(),
    }
    participants = [
        str(session[r]["uid"])
        for r in ("challenger", "challenged") if session[r]
    ]
    if all(p in session["current_answers"] for p in participants):
        prev_task = session.get("advance_task")
        if prev_task and not prev_task.done():
            prev_task.cancel()
        await _compute_and_advance(bot, ctx, challenge_id, delay=3)

async def _compute_and_advance(bot, ctx, challenge_id: str, delay: int = 3):
    """يحسب نقاط السؤال ويرسل النتيجة ثم ينتقل للسؤال التالي."""
    session = get_challenge_session(ctx, challenge_id)
    if not session or session.get("advancing"):
        return
    session["advancing"] = True
    try:
        answers = dict(session.get("current_answers", {}))
        sorted_ans = sorted(answers.items(), key=lambda x: x[1]["time"])
        # أول من أجاب بأي إجابة (صحيحة أو خاطئة)
        first_overall = sorted_ans[0][0] if sorted_ans else None
        correct_in_order = [uid for uid, a in sorted_ans if a["correct"]]
        # 2 نقاط: أول من أجاب صحيحاً وكان أسبق الجميع (لم يسبقه أحد حتى بإجابة خاطئة)
        # 1 نقطة: أجاب صحيحاً لكن سبقه أحد آخر (سواء بإجابة صحيحة أو خاطئة)
        earned = {}
        for i, uid_key in enumerate(correct_in_order):
            if i == 0 and uid_key == first_overall:
                pts = 2
            else:
                pts = 1
            earned[uid_key] = pts
            session["scores"][uid_key] = session["scores"].get(uid_key, 0) + pts
        names = {
            str(session[r]["uid"]): session[r]["name"]
            for r in ("challenger", "challenged") if session[r]
        }
        participants = list(names.keys())
        result_lines = ["📊 *نتيجة السؤال:*\n"]
        for uid_key, ans in sorted_ans:
            name = names.get(uid_key, "؟")
            if uid_key in correct_in_order:
                rank = correct_in_order.index(uid_key)
                medal = "🥇" if rank == 0 else "🥈"
                pts_earned = earned.get(uid_key, 1)
                result_lines.append(f"{medal} {name} — *+{pts_earned}* ✅")
            else:
                result_lines.append(f"❌ {name} — *+0*")
        for uid_key in participants:
            if uid_key not in answers:
                result_lines.append(f"⏭️ {names[uid_key]} — *لم يجب*")
        result_lines.append("\n🏆 *المجموع:*")
        for uid_key in participants:
            result_lines.append(f"• {names.get(uid_key, uid_key)}: *{session['scores'].get(uid_key, 0)} نقطة*")
        idx = session["current_idx"]
        total_q = len(session["questions"])
        has_next = (idx + 1) < total_q
        suffix = f"\n\n⏳ السؤال التالي خلال *{delay}* ثوانٍ..." if has_next and delay > 0 else ""
        result_text = "\n".join(result_lines) + suffix
        for r in ("challenger", "challenged"):
            p = session[r]
            if p:
                try:
                    await bot.send_message(p["chat_id"], result_text, parse_mode="Markdown")
                except Exception:
                    pass
        if delay > 0:
            await _asyncio.sleep(delay)
        session["current_idx"] += 1
        session["advancing"] = False
        await send_challenge_question_to_both(bot, ctx, challenge_id)
    except _asyncio.CancelledError:
        session["advancing"] = False
    except Exception as e:
        session["advancing"] = False
        logging.error(f"خطأ في حساب نقاط التحدي: {e}")

# ── النتائج النهائية للتحدي ───────────────────────────────────────
async def finish_challenge(bot, ctx, challenge_id: str):
    session = get_challenge_session(ctx, challenge_id)
    if not session or session["status"] == "finished":
        return
    session["status"] = "finished"
    scores = session.get("scores", {})
    names = {
        str(session[r]["uid"]): session[r]["name"]
        for r in ("challenger", "challenged") if session[r]
    }
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_scores) >= 2 and sorted_scores[0][1] == sorted_scores[1][1]:
        winner_line = "🤝 *تعادل!* كلاكما رائع!"
    elif sorted_scores:
        winner_name = names.get(sorted_scores[0][0], "؟")
        winner_line = f"🏆 الفائز: *{winner_name}* 🎉"
    else:
        winner_line = "🏁 انتهى التحدي"
    lines = ["🎯 *النتائج النهائية*\n", winner_line, ""]
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid_key, pts) in enumerate(sorted_scores):
        medal = medals[min(i, 2)]
        lines.append(f"{medal} {names.get(uid_key, uid_key)}: *{pts} نقطة*")
    result_text = "\n".join(lines)
    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("⚔️ تحدي مرة أخرى", callback_data=f"quiz_ch_{session['bid']}")
    ]])
    for r in ("challenger", "challenged"):
        p = session[r]
        if p:
            try:
                await bot.send_message(p["chat_id"], result_text,
                                       parse_mode="Markdown", reply_markup=markup)
            except Exception:
                pass
    async def _cleanup():
        await _asyncio.sleep(300)
        _challenges(ctx).pop(challenge_id, None)
    _asyncio.create_task(_cleanup())

# ── معالجة دعوة التحدي عند ضغط الرابط (/start ch_...) ───────────
async def handle_challenge_invite(update, ctx, challenge_id: str):
    uid = update.effective_user.id
    session = get_challenge_session(ctx, challenge_id)
    kb = build_kb(uid, None)
    start_msg = get_start_message()
    if not session:
        await update.message.reply_text("❌ هذا التحدي غير موجود أو انتهت صلاحيته.")
        if kb:
            await update.message.reply_text(start_msg, reply_markup=kb)
        return
    if session["status"] != "pending":
        await update.message.reply_text("❌ هذا التحدي لم يعد متاحاً — بدأ بالفعل أو انتهى.")
        if kb:
            await update.message.reply_text(start_msg, reply_markup=kb)
        return
    if uid == session["challenger"]["uid"]:
        me = await ctx.bot.get_me()
        link = f"https://t.me/{me.username}?start=ch_{challenge_id}"
        await update.message.reply_text(
            f"😅 هذا تحديك أنت!\n\nأرسل هذا الرابط للشخص الذي تريد تحديه:\n`{link}`",
            parse_mode="Markdown"
        )
        return
    challenger_name = session["challenger"]["name"]
    quiz_label = session["quiz_label"]
    q_count = len(session["questions"])
    if kb:
        await update.message.reply_text(start_msg, reply_markup=kb)
    await update.message.reply_text(
        f"⚔️ أرسل لك *{challenger_name}* تحدياً!\n\n"
        f"📊 الاختبار: *{quiz_label}*\n"
        f"❓ عدد الأسئلة: *{q_count}*\n\n"
        f"هل تقبل التحدي؟",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ قبول", callback_data=f"ch_accept_{challenge_id}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"ch_reject_{challenge_id}"),
        ]])
    )
