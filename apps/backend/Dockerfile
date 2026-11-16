FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "if [ -d seed/media ] && [ -z \"$(find media -type f -print -quit 2>/dev/null)\" ]; then mkdir -p media && cp -R seed/media/. media/; fi && python manage.py migrate --noinput && exec python manage.py runserver 0.0.0.0:8000"]
