import random
import time
import psycopg2

from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
from telebot.types import ReplyKeyboardRemove

print('Start telegram bot...')

global conn
conn = psycopg2.connect(database='Deu-Eng', password='', user='')  # Здесь хранится инфорбация о базе данных
state_storage = StateMemoryStorage()
token_bot = ''  # Здесь хранится Токен бота
bot = TeleBot(token_bot, state_storage=state_storage)


known_users = []
userStep = {}
buttons = []


def create_tables():
    with conn.cursor() as cur:
        cur.execute('''
            DROP TABLE words;
            DROP TABLE random_words;
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS words (
                id SERIAL PRIMARY KEY,
                question_word VARCHAR (15),
                answer_word VARCHAR (10)
            );
            CREATE TABLE IF NOT EXISTS random_words(
                id SERIAL PRIMARY KEY,
                word VARCHAR(10)
             );
        ''')
        cur.execute("""
            INSERT INTO words (question_word, answer_word) 
            VALUES ('die Zeit', 'time'),
            ('das Beispiel', 'example'),
            ('das Jahr', 'year'),
            ('ganz', 'entire'),
            ('hilfsbereit', 'helpful'),
            ('böse', 'evil'),
            ('gebraten', 'fried'),
            ('scharf', 'spicy'),
            ('faul', 'lasy'),
            ('gefährlich', 'dangerous'),
            ('genervt', 'annoyed'),
            ('wieder', 'again');
            
            INSERT INTO random_words (word) 
            VALUES ('cave'),
            ('worm'),
            ('advance'),
            ('wage'),
            ('note'),
            ('please'),
            ('month'),
            ('mouth'),
            ('lower'),
            ('lawyer'),
            ('layer'),
            ('wider'),
            ('game'),
            ('eye'),
            ('now');
        """)


create_tables()


def show_hint(*lines):
    return '\n'.join(lines)


def show_target(data):
    return f"{data['target_word']} -> {data['translate_word']}"


class Command:
    ADD_WORD = 'Wort hinzufügen ➕'
    DELETE_WORD = 'Wort löschen🔙'
    NEXT = 'Nächste ⏭'


class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    another_words = State()


def find_id(table_name):
    ids = []
    for table in table_name:
        with conn.cursor() as cur:
            cur.execute(f'''
                SELECT id 
                FROM {table};
            ''')

            for i in cur.fetchall():
                ids.append(i[0])
    return ids


def get_word(message):
    word_pair1 = []
    word_pair = []
    word_id = random.choice(find_id(['words', f'custom_words_{message.chat.id}']))
    for table in [f'custom_words_{message.chat.id}', 'words']:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT question_word, answer_word
                FROM {table}
                WHERE id = {word_id}
            """)
            word_pair1.append(cur.fetchall())
    for pairs in word_pair1:
        for pair in pairs:
            word_pair.append(pair)
    return word_pair


def get_randword():
    random_words = []
    options = [random.sample(range(1, len(find_id(['random_words']))), 3)]
    with conn.cursor() as cur:
        for option in options:
            for ide in option:
                cur.execute(f"""
                    SELECT word 
                    FROM random_words
                    WHERE id = {ide}
                """)
                random_words.append(cur.fetchone()[0])
    return random_words


def get_user_step(uid):
    if uid in userStep:
        return userStep[uid]
    else:
        known_users.append(uid)
        userStep[uid] = 0
        print("Nun wurde ein neuer Benutzer erkannt \"/start\" noch")
        return 0


@bot.message_handler(commands=['cards', 'start'])
def create_cards(message):
    cid = message.chat.id
    if cid not in known_users:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE custom_words_%s(
                id SERIAL PRIMARY KEY,
                question_word VARCHAR (20),
                answer_word VARCHAR (20)
                );
            ''', (message.chat.id, ))
            cur.execute('''
                INSERT INTO custom_words_%s
                VALUES (13, 'Hallo', 'Hello');
            ''', (message.chat.id, ))
        known_users.append(cid)
        userStep[cid] = 0
        bot.send_message(cid, "Hallo ✌ Möchtest du etwas Englisch lernen?")
    markup = types.ReplyKeyboardMarkup(row_width=2)

    global buttons
    buttons = []

    card_pair = get_word(message)
    target_word = card_pair[0][1]
    translate = card_pair[0][0]
    target_word_btn = types.KeyboardButton(target_word)

    buttons.append(target_word_btn)
    others = get_randword()
    other_words_btns = [types.KeyboardButton(word) for word in others]
    buttons.extend(other_words_btns)
    random.shuffle(buttons)
    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_word_btn, delete_word_btn])

    markup.add(*buttons)

    greeting = f"Übersetzen Sie dieses Wort, bitte:\n🇩🇪 {translate}"
    bot.send_message(message.chat.id, greeting, reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word
        data['translate_word'] = translate
        data['other_words'] = others


@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        with conn. cursor() as cur:
            cur.execute(f'''
                DELETE FROM words
                WHERE answer_word = %s;
                
                DELETE FROM custom_words_%s
                WHERE answer_word = %s
            ''', (data['target_word'], message.chat.id, data['target_word']))
        bot.send_message(message.chat.id, 'Worte übrig: ' +
                         str(len(find_id(['words', f'custom_words_{message.chat.id}']))))


@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    cid = message.chat.id
    userStep[cid] = 1
    remove_keyboard: True
    sent = bot.send_message(
      message.chat.id,
      "Was wird das Fragewort sein?",
      reply_markup = ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(sent, hello)


global must_add
must_add = []


def hello(message):
    must_add.append(message.text)
    bot.send_message(message.chat.id, 'Und was ist die Antwort?')
    bot.register_next_step_handler(message, bye)


def bye(message):
    buttons.clear()
    bot.send_message(message.chat.id, 'Danke schön!')
    must_add.append(message.text)
    table_name = 'custom_words_' + str(message.chat.id)
    with conn.cursor() as cur:
        cur.execute(f"""
            INSERT INTO  {table_name}(question_word, answer_word)
            VALUES (%s, %s);
        """, (must_add[0], must_add[1]))
    time.sleep(1)
    bot.send_message(message.chat.id, 'Worte übrig: ' +
                     str(len(find_id(['words', f'custom_words_{message.chat.id}']))))
    time.sleep(1)
    bot.send_message(message.chat.id, 'Weitermachen?')
    next_cards(message)


@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    text = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data['target_word']
        if text == target_word:
            buttons.clear()
            hint = show_target(data)
            hint_text = ["Wunderbar!❤", hint]
            next_btn = types.KeyboardButton(Command.NEXT)
            add_word_btn = types.KeyboardButton(Command.ADD_WORD)
            delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
            buttons.extend([next_btn, add_word_btn, delete_word_btn])
            hint = show_hint(*hint_text)
        else:
            for btn in buttons:
                if btn.text == text:
                    btn.text = text + '❌'
                    break
            hint = show_hint("Hier ist ein Fehler!",
                             f"Versuchen Sie, sich "
                             f"🇩🇪{data['translate_word']} noch einmal zu merken")
    markup.add(*buttons)
    bot.send_message(message.chat.id, hint, reply_markup=markup)


bot.add_custom_filter(custom_filters.StateFilter(bot))

bot.infinity_polling(skip_pending=True)
