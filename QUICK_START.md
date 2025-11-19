# 🚀 Быстрый старт (5 минут)

## Вариант 1: БЕЗ GigaChat (проще, для начала)

```bash
# 1. Запустить веб-интерфейс
python web_app.py

# 2. Открыть в браузере
http://localhost:5000

# 3. Загрузить видео и НЕ ставить галочку "Использовать LLM"
```

**Готово!** Система будет работать с T5 моделью (без API ключей).

---

## Вариант 2: С GigaChat (лучше качество)

### Шаг 1: Получить credentials (5 минут)
1. https://developers.sber.ru/studio/workspaces
2. Войти через Сбер ID
3. Создать проект "GigaChat API"
4. Скопировать **Client Secret**

### Шаг 2: Настроить .env
```bash
# Создать файл .env
nano .env

# Вставить:
GIGACHAT_CREDENTIALS=ваш_client_secret_здесь
GIGACHAT_SCOPE=GIGACHAT_API_PERS
```

### Шаг 3: Запустить
```bash
python web_app.py

# В веб-интерфейсе поставить галочку "Использовать LLM"
```

---

## 🐛 Если что-то не работает

```bash
# Проверить логи
tail -f logs/app_*.log

# Проверить что модели загрузились
ls -lh models/

# Тест логгера
python src/logger.py
```

---

## 📖 Подробнее

- **GigaChat суммаризация:** `GIGACHAT_SUMMARIZATION.md` ⭐ НОВОЕ!
- Полная инструкция по GigaChat: `GIGACHAT_SETUP.md`
- README с примерами: `README.md`
- Исправленные баги: `BUGFIXES.md`
- Структура кода: см. коммит с ревью
