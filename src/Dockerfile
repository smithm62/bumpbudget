FROM python:3.11-slim

WORKDIR /app

# Copy requirements correctly
COPY src/backend/requirements.txt .
RUN pip install -r requirements.txt

# Copy full project correctly
COPY src/backend/ ./backend/
COPY src/frontend/ ./frontend/

WORKDIR /app/backend

RUN mkdir -p staticfiles
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "bumpbudget_project.wsgi:application", "--bind", "0.0.0.0:8000", "--timeout", "120"]