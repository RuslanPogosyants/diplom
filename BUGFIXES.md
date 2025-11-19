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

## ✅ Текущий статус

| Баг | Статус | Коммит |
|-----|--------|--------|
| UTF-8 кодировка | ✅ Исправлен | 286184c |
| Отсутствие логирования | ✅ Исправлен | 286184c |
| device='auto' краш | ✅ Исправлен | fd128ed |

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
