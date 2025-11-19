#!/bin/bash
# install.sh

echo "=== Video Intelligence System Setup ==="

# Проверка Python версии
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
echo "Python version: $python_version"

if [ "$(printf '%s\n' "3.10" "$python_version" | sort -V | head -n1)" != "3.10" ]; then
    echo "Error: Python 3.10+ required"
    exit 1
fi

# Создание виртуального окружения
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Обновление pip
pip install --upgrade pip setuptools wheel

# Установка PyTorch с CUDA 11.8
echo "Installing PyTorch with CUDA 11.8..."
pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118

# Установка остальных зависимостей
echo "Installing dependencies..."
pip install -r requirements.txt

# Загрузка SpaCy модели для русского
echo "Downloading SpaCy Russian model..."
python3 -m spacy download ru_core_news_lg

# Загрузка NLTK данных
echo "Downloading NLTK data..."
python3 -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

echo "=== Setup complete! ==="
echo "Activate environment: source venv/bin/activate"