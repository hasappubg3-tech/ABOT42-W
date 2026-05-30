from bot.shared import *
from bot.loader import load_bot_symbols

globals().update(load_bot_symbols())

def main():
    if not BOT_TOKEN:
        logging.error("TELEGRAM_BOT_TOKEN غير موجود!"); return
    init_db()
    from telegram.ext import JobQueue
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).job_queue(JobQueue()).build()

    media_filter = (filters.TEXT | filters.PHOTO | filters.Document.ALL |
                    filters.VIDEO | filters.AUDIO | filters.VOICE) & ~filters.COMMAND

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("myid", cmd_myid))
    app.add_handler(CommandHandler("storage_status", cmd_storage_status))
    app.add_handler(CommandHandler("repair_storage", cmd_repair_storage))
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    app.add_handler(PollAnswerHandler(on_poll_answer))
    app.add_handler(CallbackQueryHandler(cb_manage))
    app.add_handler(MessageHandler(media_filter, on_message))

    logging.info("البوت يعمل...")
    _webhook_domain = os.environ.get("REPLIT_DEV_DOMAIN", "").strip()
    if _webhook_domain:
        _wh_url = f"https://{_webhook_domain}/{BOT_TOKEN}"
        logging.info(f"Webhook → {_wh_url[:60]}...")
        app.run_webhook(
            listen="0.0.0.0",
            port=8080,
            url_path=BOT_TOKEN,
            webhook_url=_wh_url,
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
        )
    else:
        app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
