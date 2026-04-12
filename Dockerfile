FROM python:3.12-slim

# System deps for psycopg2, Pillow, python-magic, and WeasyPrint.
#
# WeasyPrint requires: Cairo, Pango, GDK-Pixbuf, HarfBuzz, and libffi.
# See https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#debian-ubuntu
#
# fonts-liberation  — Liberation Serif/Sans (metric-compatible Times/Arial substitutes)
# fonts-dejavu-core — DejaVu fonts (good Unicode coverage; used as final fallback)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libharfbuzz0b \
    libffi-dev \
    shared-mime-info \
    libmagic1 \
    fonts-liberation \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements/production.txt requirements/production.txt
RUN pip install --no-cache-dir -r requirements/production.txt

COPY . .

RUN python manage.py collectstatic --noinput 2>/dev/null || true

EXPOSE 5002

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:5002", "--workers", "3"]
