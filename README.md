# Video Intelligence System

Система интеллектуального анализа образовательных видео с использованием ML/DL.

## 🚀 Быстрый старт

### Установка

```bash
# 1. Установка зависимостей
bash install.sh

# 2. Активация виртуального окружения
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# 3. (Опционально) Настройка GigaChat API
cp .env.example .env
# Отредактируйте .env и добавьте ваш GIGACHAT_CREDENTIALS
```

### Запуск

#### Веб-интерфейс (рекомендуется)

```bash
python web_app.py
```

Откройте в браузере: `http://localhost:5000`

#### CLI (командная строка)

```bash
# Полный пайплайн
python -m src.cli process-all video.mp4 \
  --model base \
  --language ru \
  --device auto

# Отдельные этапы
python -m src.cli transcribe video.mp4
python -m src.cli segment artifacts/video_XXX/transcript_raw.json
python -m src.cli summarize artifacts/video_XXX/segments_semantic.json
```

## 📋 Пайплайн обработки (8 этапов)

1. **Транскрибация** - Whisper (base/small/medium/large)
2. **Сегментация** - Семантическое разбиение на блоки
3. **Суммаризация** - RuT5 для каждого сегмента
4. **Мета-анализ** - Ключевые тезисы и темы
5. **Извлечение терминов** - SpaCy NER + частотный анализ
6. **Генерация вопросов** - Вопросы разной сложности (опционально с LLM)
7. **Поиск статей** - Wikipedia + Habr по темам
8. **Экспорт** - HTML/PDF отчёт

## 📝 Логирование

Все логи сохраняются в директории `logs/`:
- `app_YYYYMMDD.log` - основной лог
- `errors_YYYYMMDD.log` - только ошибки

Уровни логирования можно изменить в `src/logger.py`:
- `DEBUG` - детальная отладка
- `INFO` - информационные сообщения (по умолчанию)
- `WARNING` - предупреждения
- `ERROR` - ошибки
- `CRITICAL` - критические ошибки

## 🔧 Конфигурация

Основная конфигурация: `config/config.yaml`

```yaml
system:
  device: cuda  # cuda, cpu, auto

transcription:
  model: base  # tiny, base, small, medium, large
  language: ru

summarization:
  model: cointegrated/rut5-base-absum
```

## 🐛 Решение проблем

### Ошибка кодировки на Windows

✅ **Исправлено!** Добавлена явная UTF-8 кодировка в subprocess.

### Проблемы с GPU

```bash
# Проверка доступности CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Если False, используйте CPU:
python -m src.cli process-all video.mp4 --device cpu
```

### Недостаточно памяти

Используйте меньшую модель Whisper:
```bash
--model tiny  # ~40MB VRAM
--model base  # ~150MB VRAM
```

## 📊 Примерная производительность

Для 1 часа видео:
- GPU (RTX 3060): ~10-15 минут
- CPU (Intel i7): ~30-40 минут

## 🔗 Зависимости

Основные:
- PyTorch 2.0+
- Transformers (HuggingFace)
- Faster-Whisper
- SpaCy
- Flask

Опционально:
- GigaChat API (для LLM фич)
- WeasyPrint (для PDF экспорта)

## 📄 Лицензия

Educational project / Дипломная работа

## 🙏 Благодарности

- OpenAI Whisper
- HuggingFace Transformers
- Sberbank GigaChat
