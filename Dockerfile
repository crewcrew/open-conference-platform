FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN OCP_DEBUG=1 OCP_MANIFEST_STATIC=1 DJANGO_SETTINGS_MODULE=ocp.settings python manage.py collectstatic --noinput \
    && useradd --uid 10001 --create-home ocp
USER 10001
ENV DJANGO_SETTINGS_MODULE=ocp.settings.production
EXPOSE 8000
CMD ["gunicorn", "--config", "deploy/gunicorn.conf.py", "ocp.wsgi:application"]
