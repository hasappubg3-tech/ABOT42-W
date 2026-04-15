FROM python:3.11

WORKDIR /app

# نسخ ملفات المشروع
COPY . .

# تثبيت المكتبات
RUN pip install --no-cache-dir -r requirements.txt

# تشغيل البوت
CMD ["python", "main.py"]