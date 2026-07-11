# Telegram Bot — Ab18

بوت تيليغرام متكامل لإدارة المحتوى التعليمي، الاختبارات، والمحادثة بالذكاء الاصطناعي.

## كيفية التشغيل

```
python main.py
```

يُشغَّل عبر workflow باسم **Start application** تلقائياً عند فتح المشروع.

## المتطلبات (Secrets)

| المتغير | الوصف |
|---|---|
| `TELEGRAM_BOT_TOKEN` | توكن البوت من @BotFather |
| `MONGODB_URI` | رابط قاعدة بيانات MongoDB |
| `GEMINI_API_KEY` | مفتاح Google Gemini AI |
| `SUPER_ADMIN_ID` | معرّف المشرف الرئيسي (مضبوط في env vars) |

## Stack

- **Python 3.11**
- **python-telegram-bot 20.7** — Long Polling mode
- **MongoDB (pymongo)** — قاعدة البيانات الرئيسية
- **Google Gemini** — ميزات الذكاء الاصطناعي
- **Flask + Gunicorn** — موجود في الكود (للـ webhook إذا احتجت)

## هيكل المشروع

```
main.py              — نقطة الدخول الرئيسية
bot/
  shared.py          — الإعدادات العامة والمتغيرات
  loader.py          — تحميل الوحدات ديناميكياً
  data_access.py     — كل عمليات MongoDB
  content_delivery.py — إرسال المحتوى للمستخدمين
  quiz_challenge.py   — نظام الاختبارات
  study_sessions.py   — جلسات الدراسة (Pomodoro)
  callback_handlers/  — معالجات أزرار الـ inline keyboard
  features/           — ميزات إضافية (AI chat, حاسبة, عداد...)
```

## ملاحظات

- إذا ظهر خطأ **Conflict** فهذا يعني وجود نسخة أخرى من البوت تعمل في مكان آخر — أوقفها أولاً.
- البوت يستخدم أحرف Unicode غير مرئية لتشفير معرّفات الأزرار داخل نص الرسائل.

## User preferences

- المستخدم يريد إجراء تعديلات بسيطة على البوت بعد إعداده.

## حالة الإعداد على Replit

- تم تثبيت جميع حزم Python (كانت مفقودة `httpx` وغيرها عن بيئة uv الجديدة بعد الاستيراد).
- تم ضبط الأسرار (Secrets): `TELEGRAM_BOT_TOKEN`، `MONGODB_URI`، `GEMINI_API_KEY`. `SUPER_ADMIN_ID` كان مضبوطاً كمتغير بيئة عادي مسبقاً.
- البوت يعمل الآن عبر workflow "Start application" بنظام Long Polling ومتصل بـ MongoDB وTelegram بنجاح.
