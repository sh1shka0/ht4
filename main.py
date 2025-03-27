import threading
import time
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import telebot
from telebot import types
import json
from collections import defaultdict
import os
from dotenv import load_dotenv
import matplotlib
import speech_recognition as sr
import soundfile as sf
# ОБЯЗАТЕЛЬНО ДЛЯ НОРМАЛЬНОЙ РАБОТЫ ГС https://phoenixnap.com/kb/ffmpeg-windows и перезагрузить комп ещё

#подключение неинтерактивного бэкэнда для matplotlib
matplotlib.use('agg')

# подключение к боту с помощью спрятанного в .env токена
load_dotenv()
token=os.getenv('TOKEN') #'7044459383:AAGE-K-UOkT-gZocdJ6tXGb4rk7VNYpH4BM'
bot=telebot.TeleBot(token)

# в tasks хранятся все данные о задах всех пользователей, чтобы потом было легче их доставать
tasks = defaultdict(dict)
files = [int(f) for f in os.listdir('users/')]
for i in files:
    with open('users/'+str(i)) as f:
        tasks[i]=json.load(f)

# основная клавиатура для пользователя
def default_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_add = types.KeyboardButton('Добавить')
    btn_del = types.KeyboardButton('Удалить')
    btn_done = types.KeyboardButton('Отметить выполненным')
    btn_view = types.KeyboardButton('Посмотреть задачи')
    btn_graph = types.KeyboardButton('Посмотреть график продуктивности')
    markup.add(btn_add, btn_del,btn_done,btn_view, btn_graph)
    return markup

# шаблон для создания новой клавиатуры
def new_markup(texts):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for i in texts:
        markup.add(types.KeyboardButton(i))
    return markup

# основная команда /start и приветственное сообщение
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, f"Привет, {message.from_user.first_name}! Этот бот может помочь тебе в организации школьных дел. Напиши /help, чтобы узнать подробнее о командах.", reply_markup=default_markup())

# команда /help
@bot.message_handler(commands=['help'])
def start_message(message):
    bot.send_message(message.chat.id,"Добавить — добавить задачу в список невыполненнх дел;\nУдалить — удалить любое упоминание о задаче;\nОтметить выполненным — перенести задачу в список выполненных задач;\nПосмотреть задачи — посмотреть список активных задач;\nПосмотреть график продуктивности — посмотреть количество и даты уже выполненных в этом месяце задач.\n\nКроме того ты можешь записать голосовое сообщение для быстрой записи нового дела.", reply_markup=default_markup())

# команда добавления задачи
@bot.message_handler(func= lambda x:  x.text=='Добавить')
def add_task(message):
    msg=bot.send_message(message.chat.id,"Напиши название задачи", reply_markup=new_markup(['Отмена']))
    bot.register_next_step_handler(msg, task_name_add)

# добавление задачи: принимает название и запрашивает тип задачи
def task_name_add(message):
    name = message.text
    if name == 'Отмена':
        bot.send_message(message.chat.id, "Добавление задачи отменено", reply_markup=default_markup())
        return
    msg=bot.send_message(message.chat.id,"В какую категорию добавить?",
                         reply_markup=new_markup(['Домашка', 'Кружки', 'Личное', 'Отмена']))
    bot.register_next_step_handler(msg, task_type, name)

# добавление задачи: принимает тип и запрашивает важность задачи
def task_type(message, name):
    type_ = message.text
    if type_ == 'Отмена':
        bot.send_message(message.chat.id, "Добавление задачи отменено", reply_markup=default_markup())
        return
    msg=bot.send_message(message.chat.id,"Это важное?",
                         reply_markup=new_markup(['Да', 'Нет', 'Отмена']))
    bot.register_next_step_handler(msg, task_priority, name, type_)

# добавление задачи: принимает важность и запрашивает дедлайн задачи
def task_priority(message, name, type_):
    priority = message.text
    if priority == 'Отмена':
        bot.send_message(message.chat.id, "Добавление задачи отменено", reply_markup=default_markup())
        return
    msg=bot.send_message(message.chat.id,"Когда вам напомнить об этой задаче (дедлайн)? Вы можете написать срок в двух образцах: 'день.месяц.год часы:минуты' (01.01.2025 10:30) или 'день.месяц.год' (01.01.2025). Напишите 'нет', чтобы создать задачу без напоминания.",
                         reply_markup=new_markup(['Нет', 'Отмена']))
    bot.register_next_step_handler(msg, task_deadline, name, type_, priority)

# добавление задачи: принимает дедлайн задачи и записывает всё её данные в личный json файл пользователя
def task_deadline(message, name, type_, priority):
    deadline = message.text.lower()
    if deadline == 'Отмена':
        bot.send_message(message.chat.id, "Добавление задачи отменено", reply_markup=default_markup())
        return
    if deadline != 'нет':
        time_temp=deadline.split()
        try:
            if len(time_temp) == 2:
                time = [int(x) for x in time_temp[0].split('.') + time_temp[1].split(':')]
                deadline = datetime(time[2], time[1], time[0], time[3], time[4]).timestamp()
            elif len(time_temp) == 1:
                time = [int(x) for x in time_temp[0].split('.')]
                deadline = datetime(time[2], time[1], time[0], 12, 0).timestamp()
        except:
            bot.send_message(message.chat.id, "Неправильный формат даты", reply_markup=default_markup())
            return
    tasks[message.chat.id][name] = {'type': type_, 'priority': priority,
                                    'deadline': deadline, 'deadline_done': False,
                                    'done': False}
    with open('users/'+str(message.chat.id), 'w+') as f:
        json.dump(tasks[message.chat.id], f, ensure_ascii=False)
    bot.send_message(message.chat.id, "Готово!", reply_markup=default_markup())

# команда удаления задачи
@bot.message_handler(func= lambda x:  x.text=='Удалить')
def del_task(message):
    msg=bot.send_message(message.chat.id,"Напиши название задачи", reply_markup=new_markup(['Отмена']))
    bot.register_next_step_handler(msg, task_name_del)

# удаление задачи: принимает название задачи и удаляет её из json файла пользователя
def task_name_del(message):
    name = message.text
    if name == 'Отмена':
        bot.send_message(message.chat.id, "Удаление задачи отменено", reply_markup=default_markup())
        return
    try:
        tasks[message.chat.id].pop(name)
        with open('users/' + str(message.chat.id), 'w+') as f:
            json.dump(tasks[message.chat.id], f, ensure_ascii=False)
        bot.send_message(message.chat.id, "Удалено", reply_markup=default_markup())
    except:
        bot.send_message(message.chat.id, "Такой задачи нет", reply_markup=default_markup())

# команда изменения статуса задачи на выполненную
@bot.message_handler(func= lambda x:  x.text=='Отметить выполненным')
def mark_task(message):
    msg=bot.send_message(message.chat.id,"Напиши название задачи", reply_markup=new_markup(['Отмена']))
    bot.register_next_step_handler(msg, task_name_mark)

# изменение статуса задачи: принимает название задачи и меняет значиние done на её время выполнени в json файле пользователя
def task_name_mark(message):
    name = message.text
    if name == 'Отмена':
        bot.send_message(message.chat.id, "Выполнение фунции отменено", reply_markup=default_markup())
        return
    try:
        tasks[message.chat.id][name]['done']=datetime.now().timestamp()
        with open('users/' + str(message.chat.id), 'w+') as f:
            json.dump(tasks[message.chat.id], f, ensure_ascii=False)
        bot.send_message(message.chat.id, "Задача отмечена как выполненная", reply_markup=default_markup())
    except:
        bot.send_message(message.chat.id, "Такой задачи нет", reply_markup=default_markup())

# команда просмотра невыполненных задач пользователя
@bot.message_handler(func= lambda x:  x.text=='Посмотреть задачи')
def mark_task(message):
    text='Ваши невыполненные задачи:\n'
    c=1
    for i in tasks[message.chat.id]:
        if not tasks[message.chat.id][i]['done']:
            text+=['', '<b>ВАЖНО! </b>'][tasks[message.chat.id][i]['priority']=='Да']+i+f' ({tasks[message.chat.id][i]['type']})'+'\n'
            c=0
    if c:
        text='Нет невыполненных задач'
    bot.send_message(message.chat.id, text, reply_markup=default_markup(), parse_mode='HTML')

# команда, выводящая график по количеству выполненных задач и их дате в этом месяце
@bot.message_handler(func= lambda x:  x.text=='Посмотреть график продуктивности')
def graph_task(message):
    fig = plt.figure()
    month_ = datetime.now().month
    year = datetime.now().year
    data = {i: 0 for i in range(31)}
    c=1
    for i in tasks[message.chat.id]:
        if tasks[message.chat.id][i]['done']:
            if datetime.fromtimestamp(tasks[message.chat.id][i]['done']).month == month_ and \
                datetime.fromtimestamp(tasks[message.chat.id][i]['done']).year == year:
                day = datetime.fromtimestamp(tasks[message.chat.id][i]['done']).day
                data[day] +=1
                c=0
    if c:
        bot.send_message(message.chat.id, "Выполненных задач в этом месяце нет")
        return
    plt.bar(data.keys(),data.values(), figure=fig)
    plt.yticks(np.arange(0, max(data.values()) + 1, 1.0))
    plt.xticks(np.arange(0, 31, 2.0))
    plt.xlabel('Дни')
    plt.ylabel('Выполненные задачи')
    plt.title('Выполненные задачи за этот месяц')
    fig.savefig(f'tmp/{message.chat.id}.png')
    with open(f'tmp/{message.chat.id}.png', 'rb') as f:
        bot.send_photo(message.chat.id, f)
    os.remove(f'tmp/{message.chat.id}.png')

# команда, принимающая и распознающая в текст голосовое сообщение пользователя
rec = sr.Recognizer()
@bot.message_handler(content_types=['voice'])
def voice_add(message):
    file_info = bot.get_file(message.voice.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    with open(f'tmp/{message.chat.id}.ogg', 'wb+')as f:
        f.write(downloaded_file)
    os.system(f'ffmpeg -i tmp/{message.chat.id}.ogg tmp/{message.chat.id}.wav')
    with sr.AudioFile(f'tmp/{message.chat.id}.wav') as f:
        audio = rec.listen(f)
        try:
            text = rec.recognize_google(audio, language = 'ru_RU')
            msg = bot.send_message(message.chat.id,'Задача будет создана как : '+text, reply_markup=new_markup(['Да', 'Нет']))
            bot.register_next_step_handler(msg, audio_add_confirm, text)
        except:
            bot.send_message(message.chat.id, f"Ошибка распознавания", reply_markup=default_markup())
    os.remove(f'tmp/{message.chat.id}.wav')
    os.remove(f'tmp/{message.chat.id}.ogg')

# распознование текста из голосового сообщения: записывает данные задачи в json файл пользователя
def audio_add_confirm(message, text):
    answer = message.text
    if answer=='Да':
        tasks[message.chat.id][text] = {'type': 'Личное', 'priority': 'Нет',
                                        'deadline': 'нет', 'deadline_done': False,
                                        'done': False}
        with open('users/' + str(message.chat.id), 'w+') as f:
            json.dump(tasks[message.chat.id], f, ensure_ascii=False)
        bot.send_message(message.chat.id, f"Создана задача из голосового сообщения: {text}",
                         reply_markup=default_markup())
    else:
        bot.send_message(message.chat.id, f'Отменено',
                         reply_markup=default_markup())

# функция, которая каждые 60 секунд проверяет дедлайны задач и отправляет напоминания пользователю
def deadline_thread():
    while 1:
        time.sleep(60)
        for i in tasks:
            for j in tasks[i]:
                try:
                    if tasks[i][j]['deadline']<=datetime.now().timestamp() and not tasks[i][j]['deadline_done']:
                        bot.send_message(i, f'Напоминание о задаче {j}')
                        tasks[i][j]['deadline_done']=True
                        with open('users/' + str(i), 'w+') as f:
                            json.dump(tasks[i], f, ensure_ascii=False)
                except:
                    pass

# создаёт и запускает поток для deadline_thread в фоновом режиме
threading.Thread(target=deadline_thread, daemon=True).start()

# бесконечный цикл обработки входящих от пользователей сообщений
bot.infinity_polling() #можно попробовать bot.polling() если не работает