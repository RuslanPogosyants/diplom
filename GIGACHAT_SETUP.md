# Настройка GigaChat API

## 📝 Пошаговая инструкция

### 1. Регистрация в GigaChat Studio

1. Откройте: https://developers.sber.ru/studio/workspaces
2. Нажмите "Войти" → войдите через **Сбер ID**
   - Если нет аккаунта Сбербанк Онлайн, зарегистрируйтесь
3. После входа вы попадете в личный кабинет

### 2. Создание проекта

1. Нажмите **"Создать проект"**
2. Выберите **"GigaChat API"**
3. Заполните данные:
   - Название проекта: `Video Intelligence System`
   - Описание: `Дипломная работа - анализ образовательных видео`
4. Примите **Пользовательское соглашение**
5. Нажмите **"Создать"**

### 3. Получение авторизационных данных

1. В созданном проекте откройте раздел **"Авторизационные данные"**
2. Вы увидите:
   - **Client ID** (UUID формат)
   - **Client Secret** ← **ВОТ ЭТО НУЖНО СКОПИРОВАТЬ!**
3. Нажмите на иконку "Скопировать" рядом с Client Secret

### 4. Настройка проекта

Создайте файл `.env` в корне проекта:

```bash
# Скопируйте содержимое .env.example
cp .env.example .env

# Откройте .env в редакторе
nano .env  # или любой другой редактор
```

Вставьте ваш Client Secret:

```bash
GIGACHAT_CREDENTIALS=ваш_очень_длинный_секретный_ключ_здесь
GIGACHAT_SCOPE=GIGACHAT_API_PERS
```

**ВАЖНО:** Client Secret выглядит примерно так:
```
NTZjNmQ0ZmEtMjdkYy00ZmE4LWI4YmUtYzQ5ZGI1NmE3MDk0OjdhNzU0NjY5LWY4ZjItNGRkMy1iZjk5LWUyNzVhMjY5NTY4MA==
```

### 5. Проверка настройки

Запустите тест:

```bash
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

credentials = os.getenv('GIGACHAT_CREDENTIALS')
scope = os.getenv('GIGACHAT_SCOPE')

print(f'Credentials: {credentials[:20]}...{credentials[-20:]}')
print(f'Scope: {scope}')
print('✓ Настройка выглядит корректно!')
"
```

### 6. Тест подключения к API

```bash
python -c "
from src.llm_provider import LLMProvider, LLMConfig

config = LLMConfig()
llm = LLMProvider(config)

# Простой тест
response = llm.provider.chat('Привет! Как дела?')
print(f'Ответ GigaChat: {response}')
"
```

---

## 🔧 Возможные проблемы

### ❌ Ошибка: "GIGACHAT_CREDENTIALS not found"

**Причина:** Переменная окружения не загружена

**Решение:**
1. Убедитесь что файл `.env` создан в корне проекта
2. Установите `python-dotenv`:
   ```bash
   pip install python-dotenv
   ```
3. В коде используйте:
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```

### ❌ Ошибка: "Invalid credentials"

**Причина:** Неверный Client Secret

**Решение:**
1. Проверьте что скопировали **Client Secret**, а не Client ID
2. Убедитесь что в credentials нет лишних пробелов
3. Перегенерируйте ключ в GigaChat Studio

### ❌ Ошибка: "SSL certificate verify failed"

**Причина:** Проблемы с сертификатами

**Решение:**
Уже исправлено в коде:
```python
config = LLMConfig(verify_ssl=False)
```

### ❌ Ошибка: "Rate limit exceeded"

**Причина:** Превышен лимит запросов

**Решение:**
1. Используйте кэширование (уже включено):
   ```python
   config = LLMConfig(use_cache=True)
   ```
2. Подождите 1-2 минуты между запросами

---

## 💡 Альтернатива: Работа БЕЗ GigaChat

Если у вас нет доступа к GigaChat API, **система все равно будет работать!**

### Что будет использоваться вместо LLM:

1. **Суммаризация:** T5 модель (cointegrated/rut5-base-absum)
2. **Ключевые тезисы:** Частотный анализ (TF-IDF)
3. **Вопросы:** Rule-based генерация

### Просто НЕ используйте флаги:
```bash
# БЕЗ LLM (работает без credentials)
python -m src.cli process-all video.mp4 \
  --model base \
  --language ru

# С LLM (требует credentials)
python -m src.cli process-all video.mp4 \
  --model base \
  --language ru \
  --use-llm \        # ← НЕ добавляйте без credentials
  --with-answers
```

---

## 📊 Сравнение: С LLM vs БЕЗ LLM

| Компонент | БЕЗ LLM | С LLM (GigaChat) |
|-----------|---------|------------------|
| **Транскрибация** | ✅ Whisper | ✅ Whisper (то же) |
| **Сегментация** | ✅ SentenceTransformer | ✅ SentenceTransformer (то же) |
| **Суммаризация** | ✅ T5 (хорошо) | ✅ LLM (отлично) |
| **Ключевые тезисы** | ⚠️ TF-IDF (нормально) | ✅ LLM (отлично) |
| **Генерация вопросов** | ⚠️ Шаблоны (базово) | ✅ LLM (качественно) |
| **Ответы к вопросам** | ❌ Нет | ✅ Есть |
| **Скорость** | 🚀 Быстро | 🐌 Медленнее |
| **Стоимость** | 💰 Бесплатно | 💰 Зависит от тарифа |

**Рекомендация:** Для диплома достаточно работы БЕЗ LLM. GigaChat - это nice-to-have фича для улучшения качества.

---

## 🔗 Полезные ссылки

- **GigaChat Studio:** https://developers.sber.ru/studio/workspaces
- **Документация API:** https://developers.sber.ru/docs/ru/gigachat/api/overview
- **Тарифы:** https://developers.sber.ru/pricing
- **Поддержка:** https://developers.sber.ru/help

---

## 💬 FAQ

**Q: Это платно?**
A: Есть бесплатный тариф с лимитами (достаточно для диплома).

**Q: Нужна ли карта Сбербанка?**
A: Нет, достаточно учетной записи Сбер ID (можно создать онлайн).

**Q: Можно ли использовать другие LLM (ChatGPT, Claude)?**
A: Код написан под GigaChat, но можно адаптировать. Для диплома достаточно работы без LLM.

**Q: Что делать если получу 403 ошибку?**
A: Проверьте что credentials корректный и scope = GIGACHAT_API_PERS.
