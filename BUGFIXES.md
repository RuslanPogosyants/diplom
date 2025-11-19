# 🐛 Исправленные баги

## Коммиты с исправлениями

### 1. Fix critical issues: UTF-8 encoding and logging (286184c)

**Проблема:**
```
'charmap' codec can't decode byte 0x98 in position 1342: character maps to <undefined>
```

**Причина:**
- Windows использует кодировку cp1252 по умолчанию
- subprocess.Popen не указывал явную кодировку
- Эмодзи и кириллица в stdout/stderr вызывали краш

**Решение:**
```python
# web_app.py
process = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    encoding='utf-8',      # ✅ Явная UTF-8 кодировка
    errors='replace',      # ✅ Замена проблемных символов
    bufsize=1
)
```

**Проверка:**
```bash
# Запустить веб-интерфейс
python web_app.py

# Загрузить видео
# Ошибка кодировки больше не должна появляться
```

---

### 2. Add centralized logging system (286184c)

**Проблема:**
- print() везде в коде
- Нет сохранения логов в файлы
- Эмодзи в print() ломают кодировку на Windows
- Невозможно отследить ошибки после краша

**Решение:**
Создан модуль `src/logger.py`:

```python
from src.logger import get_logger, TaskLogger

# Глобальный логгер
logger = get_logger("my_module")
logger.info("Информация")
logger.error("Ошибка", exc_info=True)

# Для задач
task_logger = TaskLogger("task_123")
task_logger.stage(1, 8, "Транскрибация")
task_logger.success("Готово!")
```

**Фичи:**
- ✅ Автоматическое сохранение в `logs/app_YYYYMMDD.log`
- ✅ Отдельный файл для ошибок `logs/errors_YYYYMMDD.log`
- ✅ UTF-8 поддержка
- ✅ Форматированный вывод с timestamp
- ✅ TaskLogger для отслеживания задач

**Проверка:**
```bash
# Запустить сервер
python web_app.py

# Проверить что логи создались
ls -lh logs/

# Читать логи в реальном времени
tail -f logs/app_*.log
```

---

### 3. Fix device='auto' parameter handling (fd128ed)

**Проблема:**
```
RuntimeError: Expected one of cpu, cuda... device type at start of device string: auto
```

**Причина:**
- PyTorch не понимает 'auto' как устройство
- Параметр `--device auto` передавался напрямую в модели
- Краш в segment.py, summarize.py, generate_questions.py

**Решение:**
Создан модуль `src/utils.py` с функцией `resolve_device()`:

```python
from src.utils import resolve_device

# Конвертирует 'auto' в 'cuda' или 'cpu'
device = resolve_device('auto')  # -> 'cuda' если GPU доступен
device = resolve_device('cpu')   # -> 'cpu' (как есть)
device = resolve_device('cuda')  # -> 'cuda' (как есть)
```

**Обновлены модули:**
- ✅ `src/segment.py` - TranscriptSegmenter
- ✅ `src/summarize.py` - SegmentSummarizer
- ✅ `src/generate_questions.py` - QuestionGenerator

**Проверка:**
```bash
# CLI с auto device
python -m src.cli process-all video.mp4 --device auto

# Должно работать без ошибок
# Будет автоматически выбрана cuda или cpu
```

**Дополнительно:**
```python
from src.utils import print_device_info

# Вывести информацию о GPU/CPU
print_device_info()
```

---

### 4. Add detailed per-segment summarization progress logging (f53780c, 4351350)

**Проблема:**
```
Суммаризация занимает 10+ минут без видимого прогресса
Пользователь не понимает что происходит - система зависла или работает
```

**Причина:**
- В `summarize.py` только tqdm progress bar показывал прогресс
- Нет детального логирования после завершения каждого сегмента
- Невозможно отследить какой сегмент обрабатывается и сколько времени занимает

**Решение:**
Добавлено детальное логирование в `src/summarize.py` и `src/llm_provider.py`:

```python
# src/summarize.py
import time
from .logger import get_logger

logger = get_logger(__name__)

for idx, segment in enumerate(iterator, 1):
    segment_start_time = time.time()

    logger.info(f"Processing segment {idx}/{len(segments)} (ID: {segment_id})")

    # ... обработка сегмента ...

    elapsed = time.time() - segment_start_time
    logger.info(
        f"✓ Segment {idx}/{len(segments)} completed in {elapsed:.1f}s - "
        f"{original_length} → {summary_length} chars "
        f"({compression_ratio:.1f}x compression)"
    )
```

**Результат:**
```
2025-11-19 15:30:12 [INFO] Processing segment 1/25 (ID: 0)
2025-11-19 15:30:24 [INFO] ✓ Segment 1/25 completed in 12.3s - 1243 → 156 chars (8.0x compression)
2025-11-19 15:30:25 [INFO] Processing segment 2/25 (ID: 1)
2025-11-19 15:30:36 [INFO] ✓ Segment 2/25 completed in 11.8s - 987 → 134 chars (7.4x compression)
...
```

**Проверка:**
```bash
# Запустить суммаризацию
python -m src.cli summarize artifacts/video_id/segments_semantic.json

# В другом терминале смотреть логи в реальном времени
tail -f logs/app_*.log

# Увидите детальный прогресс по каждому сегменту
```

**Дополнительно обновлено:**
- ✅ Все print() в `summarize.py` заменены на logger
- ✅ Все print() в `llm_provider.py` заменены на logger
- ✅ Добавлен таймер для каждого сегмента
- ✅ Логирование показывает compression ratio и время обработки

---

## ✅ Текущий статус

| Баг | Статус | Коммит |
|-----|--------|--------|
| UTF-8 кодировка | ✅ Исправлен | 286184c |
| Отсутствие логирования | ✅ Исправлен | 286184c |
| device='auto' краш | ✅ Исправлен | fd128ed |
| Нет прогресса при суммаризации | ✅ Исправлен | f53780c, 4351350 |

---

## 🚀 Что работает сейчас

1. **Веб-интерфейс запускается без ошибок**
   ```bash
   python web_app.py
   # Открыть http://localhost:5000
   ```

2. **Логи сохраняются в файлы**
   ```bash
   ls logs/
   # app_20251119.log
   # errors_20251119.log
   ```

3. **device='auto' работает корректно**
   ```bash
   python -m src.cli transcribe video.mp4 --device auto
   # Автоматически выберет cuda или cpu
   ```

---

## 🐛 Известные проблемы (TODO)

### Не критично, но желательно исправить:

1. **Race conditions в web_app.py**
   - `processing_tasks` словарь не thread-safe
   - Может привести к багам при параллельных запросах

2. **Отсутствие валидации входных файлов**
   - Нет проверки формата (может загрузить .exe вместо .mp4)
   - Нет проверки размера (может загрузить 50GB файл)

3. **Хрупкий парсинг LLM ответов**
   - Используются регулярки вместо JSON mode
   - LLM может нарушить формат → пустой результат

4. **Отсутствие тестов**
   - Нет unit/integration тестов
   - Рефакторинг опасен

5. **Неоптимальное использование памяти**
   - Segment.py создает огромные массивы для маппинга
   - Может быть OOM на больших видео

---

## 📖 Дополнительная информация

- **GigaChat настройка:** см. `GIGACHAT_SETUP.md`
- **Быстрый старт:** см. `QUICK_START.md`
- **Общее README:** см. `README.md`

---

## 💬 Отладка

### Если что-то не работает:

1. **Проверить логи:**
   ```bash
   tail -f logs/app_*.log
   tail -f logs/errors_*.log
   ```

2. **Проверить устройство:**
   ```bash
   python -c "from src.utils import print_device_info; print_device_info()"
   ```

3. **Проверить зависимости:**
   ```bash
   python -c "import torch; print(f'PyTorch: {torch.__version__}')"
   python -c "import transformers; print(f'Transformers: {transformers.__version__}')"
   ```

4. **Запустить в режиме DEBUG:**
   ```python
   from src.logger import set_log_level
   set_log_level('DEBUG')
   ```
