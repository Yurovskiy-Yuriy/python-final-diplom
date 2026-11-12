# Используем официальный образ Python 3.12
FROM python:3.12-slim

# Устанавливаем переменные окружения
# PYTHONUNBUFFERED=1 - отключает буферизацию вывода (важно для логов)
# PYTHONDONTWRITEBYTECODE=1 - не создает .pyc файлы
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Устанавливаем системные зависимости для PostgreSQL и сборки пакетов
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt /app/

# Устанавливаем Python-зависимости
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Копируем весь проект в контейнер
COPY . /app/

# Открываем порт 8000
EXPOSE 8000

# Команда для запуска приложения
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]