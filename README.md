# Бот для учёта парковочных мест

## Для работы программы требуется:
- Машина под управлением Linux
- Python 3
- pip
Если ранее не установлен:
```bash
sudo apt install python3-pip
```
- Библиотека venv:
```bash
sudo apt install python3.11-venv
```


## Порядок установки:
0. На данном этапе подразумевается, что у Вас выполнены все требования и Вы находитесь в домашней директории пользователя (не root)
1. Создать виртуальную среду:
```bash
python3 -m venv env
```
2. Склонировать репозиторий
```bash
git clone https://github.com/KrivoSoft/parking_telegram_bot.git
```
3. Установить необходимые библиотеки: 
```bash
cd parking_telegram_bot
pip install -r requirements.txt 
```
4. Создайте конфигурационный файл settings.yml:
```bash
cp example_settings.yml settings.yml
``` 
5. Запишите в конфигурационный файл актуальный токен бота 
6. Запустите бота в фоновом режиме:
```bash
nohup python3 run.py
```
