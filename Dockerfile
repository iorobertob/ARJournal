FROM python:3.12-slim

# System deps for psycopg2, Pillow, WeasyPrint, pdflatex
RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 libffi-dev shared-mime-info \
    texlive-latex-base texlive-latex-recommended texlive-fonts-recommended \
    texlive-science \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements/production.txt requirements/production.txt
RUN pip install --no-cache-dir -r requirements/production.txt

COPY . .

RUN python manage.py collectstatic --noinput 2>/dev/null || true

EXPOSE 5002

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:5002", "--workers", "3"]
