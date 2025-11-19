# 🤖 Суммаризация через GigaChat

## 📖 Обзор

Теперь система поддерживает **два режима суммаризации**:

| Режим | Модель | Скорость | Качество | Требует API |
|-------|--------|----------|----------|-------------|
| **Локальный** (по умолчанию) | T5 (rut5-base-absum) | 🚀 Быстро | ✅ Хорошо | ❌ Нет |
| **GigaChat** (опция) | GigaChat LLM | 🐌 Медленнее | ⭐ Отлично | ✅ Да |

---

## 🎯 Когда использовать GigaChat?

### ✅ Используйте GigaChat если:
- Нужны **качественные суммаризации** для диплома/публикации
- Важна **точность и понимание контекста**
- Есть **доступ к GigaChat API**
- Работаете с **небольшим количеством видео** (экономия токенов)

### ⚠️ Используйте T5 (локально) если:
- Быстрое прототипирование
- Нет доступа к GigaChat API
- Обработка большого количества видео
- Ограниченный бюджет на API вызовы

---

## 🚀 Как использовать GigaChat для суммаризации

### 1. **Настройте GigaChat API**

Следуйте инструкциям в `GIGACHAT_SETUP.md`:

```bash
# Создайте .env файл
cp .env.example .env

# Добавьте ваш Client Secret
nano .env
```

В `.env`:
```bash
GIGACHAT_CREDENTIALS=ваш_client_secret_здесь
GIGACHAT_SCOPE=GIGACHAT_API_PERS
```

### 2. **Запустите суммаризацию с флагом --use-llm**

#### Вариант A: Только суммаризация

```bash
# Сначала создайте сегменты
python -m src.cli segment artifacts/video_id/transcript_raw.json

# Затем суммаризация через GigaChat
python -m src.cli summarize artifacts/video_id/segments_semantic.json --use-llm
```

#### Вариант B: Полный пайплайн

```bash
# Всё сразу: транскрибация → сегментация → суммаризация (GigaChat)
python -m src.cli process-all video.mp4 --use-llm
```

**Что произойдет:**
```
🚀 Запуск полного пайплайна обработки видео

[1/8] 🎬 Транскрибация...
[2/8] 📊 Сегментация...
[3/8] 📝 Суммаризация...
   🤖 Используется GigaChat для суммаризации    ← Это новое!

2025-11-19 16:45:12 [INFO] Using GigaChat LLM for summarization
2025-11-19 16:45:15 [INFO] GigaChat provider initialized successfully
2025-11-19 16:45:20 [INFO] Processing segment 1/25 (ID: 0)
2025-11-19 16:45:23 [INFO] [GIGACHAT] Sending request to GigaChat API
2025-11-19 16:45:28 [INFO] [GIGACHAT] Response received in 5.2s
2025-11-19 16:45:28 [INFO] ✓ Segment 1/25 completed in 8.4s - 1243 → 178 chars (7.0x compression)
...
```

---

## 💰 Экономия токенов с кэшированием

GigaChat суммаризация **автоматически использует кэширование**:

```bash
# Первый запуск - реальные API вызовы
python -m src.cli summarize segments.json --use-llm

# Повторный запуск - результаты из кэша (бесплатно!)
python -m src.cli summarize segments.json --use-llm
```

Логи покажут:
```
[CACHE] Checking cache...
[CACHE] Cache HIT! Using cached response
[CACHE] Tokens saved: ~450
```

**Кэш сохраняется в:** `.llm_cache/`

---

## 🔍 Как работает GigaChat суммаризация

### Промпт-инжиниринг

Система использует специально разработанный промпт для образовательного контента:

```python
Системный промпт:
"Ты - профессиональный суммаризатор образовательного контента.
Твоя задача - создать краткое, но информативное резюме текста,
сохраняя все ключевые моменты."

Пользовательский промпт:
"Суммаризируй следующий фрагмент образовательной лекции.
Создай краткое резюме (2-4 предложения), которое передаёт суть и ключевые идеи.
Используй русский язык. Не добавляй вводные слова типа 'В этом фрагменте...'."
```

### Параметры

- **Temperature:** 0.3 (низкая для консистентности)
- **Max tokens:** 600 (~150 слов)
- **Кэширование:** Включено

---

## 📊 Сравнение: T5 vs GigaChat

### Пример суммаризации

**Исходный текст:**
```
В этом разделе мы рассматриваем основные принципы объектно-ориентированного
программирования. ООП базируется на четырех основных столпах: инкапсуляция,
наследование, полиморфизм и абстракция. Инкапсуляция позволяет скрыть внутреннюю
реализацию и предоставить только необходимый интерфейс. Наследование дает возможность
создавать новые классы на основе существующих, переиспользуя код...
```

**T5 суммаризация:**
```
Основные принципы объектно-ориентированного программирования: инкапсуляция,
наследование, полиморфизм, абстракция.
```

**GigaChat суммаризация:**
```
Рассматриваются четыре основных принципа ООП: инкапсуляция скрывает внутреннюю
реализацию и предоставляет интерфейс, наследование позволяет переиспользовать код
через создание новых классов на основе существующих, полиморфизм и абстракция
дополняют архитектуру.
```

✅ **GigaChat** сохраняет больше деталей и контекста!

---

## ⚙️ Настройка параметров

### Изменение модели GigaChat

В `src/summarize.py`:

```python
config = LLMConfig(
    provider="gigachat",
    model="GigaChat-Pro",  # ← Измените на GigaChat-Pro для лучшего качества
    temperature=0.3,
    max_tokens=600,
    use_cache=True
)
```

Доступные модели:
- `GigaChat` - базовая модель (по умолчанию)
- `GigaChat-Pro` - улучшенная модель (дороже, но качественнее)
- `GigaChat-Plus` - премиум модель

---

## 🐛 Troubleshooting

### ❌ Ошибка: "GIGACHAT_CREDENTIALS not found"

**Решение:**
```bash
# Проверьте .env файл
cat .env | grep GIGACHAT_CREDENTIALS

# Если пусто - добавьте credentials
echo "GIGACHAT_CREDENTIALS=ваш_ключ_здесь" >> .env
```

### ❌ Ошибка: "Failed to initialize GigaChat"

**Причины:**
1. Неверный API ключ
2. Нет интернета
3. Не установлена библиотека `gigachat`

**Решение:**
```bash
# Установите библиотеку
pip install gigachat

# Проверьте ключ
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('GIGACHAT_CREDENTIALS'))"
```

### ⚠️ Суммаризация медленная (5-10 секунд на сегмент)

**Это нормально!** GigaChat - это cloud API, требуется время на:
- Отправку запроса
- Обработку LLM
- Получение ответа

**Оптимизация:**
- ✅ Кэширование уже включено
- ✅ Используйте T5 для быстрого прототипирования
- ✅ Запускайте GigaChat на финальной версии

---

## 📈 Мониторинг использования токенов

Логи показывают детальную информацию:

```
[GIGACHAT] Sending request to GigaChat API
[GIGACHAT] Model: GigaChat
[GIGACHAT] Temperature: 0.3
[GIGACHAT] Prompt size: 1243 chars (~310 tokens)
[GIGACHAT] Total size: 1243 chars (~310 tokens)
[GIGACHAT] Waiting for response...
[GIGACHAT] Response received in 5.2s
[GIGACHAT] Response size: 178 chars (~44 tokens)
[GIGACHAT] Token usage:
[GIGACHAT]   - Prompt tokens: 312
[GIGACHAT]   - Completion tokens: 45
[GIGACHAT]   - Total tokens: 357
```

---

## 💡 Best Practices

### 1. **Hybrid подход**

Используйте **T5 для разработки**, **GigaChat для финала**:

```bash
# Разработка и тестирование
python -m src.cli process-all video.mp4

# Финальная версия для диплома
python -m src.cli process-all video.mp4 --use-llm
```

### 2. **Кэш не удаляйте**

Папка `.llm_cache/` экономит деньги:

```bash
# ❌ НЕ делайте
rm -rf .llm_cache/

# ✅ Добавьте в .gitignore
echo ".llm_cache/" >> .gitignore
```

### 3. **Мониторьте расход**

Проверяйте статистику кэша:

```python
from src.llm_provider import LLMProvider, LLMConfig

config = LLMConfig(use_cache=True)
llm = LLMProvider(config)

if llm.cache:
    stats = llm.cache.get_stats()
    print(f"Entries: {stats['total_entries']}")
    print(f"Tokens saved: {stats['estimated_tokens_saved']}")
```

---

## 📚 Дополнительная информация

- **GigaChat API настройка:** `GIGACHAT_SETUP.md`
- **Быстрый старт:** `QUICK_START.md`
- **Исправленные баги:** `BUGFIXES.md`
- **Основное README:** `README.md`

---

## 🎓 Для диплома

### Что указать в дипломе:

**Используемые технологии:**
- ✅ Local ML: T5 model (cointegrated/rut5-base-absum)
- ✅ Cloud LLM: GigaChat API (Сбербанк)
- ✅ Гибридный подход: локальная обработка + cloud enhancement
- ✅ Кэширование для оптимизации расходов

**Обоснование выбора:**
> "Система поддерживает два режима суммаризации: локальную T5 модель для быстрого прототипирования
> и cloud-based GigaChat LLM для получения качественных результатов. Кэширование API вызовов
> обеспечивает экономию токенов при повторных запусках."

---

**🚀 Готово! Теперь можно использовать GigaChat для качественной суммаризации!**
