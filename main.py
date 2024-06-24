import random
import time
import psycopg2

from user_personal_data.connections import database, password, user, token_bot
from user_personal_data.words_for_db import words
from db_script import create_tables
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage

from telebot.handler_backends import State, StatesGroup
from telebot.types import ReplyKeyboardRemove

print('Start telegram bot...')
state_storage = StateMemoryStorage()
bot = TeleBot(token_bot, state_storage=state_storage)


known_users = []
userStep = {}


def new_user_insert(message):
    with conn.cursor() as cur:
        for pair in words:
            cur.execute("""
                INSERT INTO words (question_word, answer_word, user_id) 
                VALUES (%s, %s, %s)
                """, (pair[0], pair[1], message.chat.id, ))
    conn.commit()


def show_hint(*lines) -> str:
    return '\n'.join(lines)


def show_target(data):
    return f"{data['target_word']} -> {data['translate_word']}"


class Command:
    ADD_WORD = 'Wort hinzufügen ➕'
    DELETE_WORD = 'Wort löschen🔙'
    NEXT = 'Nächste ⏭'


class MyStates(StatesGroup):
    target_word = State()


def get_words(message) -> list:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT question_word, answer_word
            FROM words
            WHERE user_id = %s
        """, (message.chat.id,))
        result = cur.fetchall()
        return result


def get_word(message):
    word_pair1 = []
    word_pair = []
    word_pair1.append(random.choice(get_words(message)))
    for pairs in word_pair1:
        for pair in pairs:
            word_pair.append(pair)
    return word_pair


def get_randword():
    random_words = []
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT word 
            FROM random_words
        """)
        select = cur.fetchall()
        words_3 = random.sample(select, 3)
        for word in words_3:
            random_words.append(word[0])
    return random_words


@bot.message_handler(commands=['cards', 'start'])
def create_cards(message):
    cid = message.chat.id
    if cid not in known_users:
        known_users.append(cid)
        new_user_insert(message)
        userStep[cid] = 0
        bot.send_message(cid, "Hallo ✌ Möchtest du etwas Englisch lernen?")
        time.sleep(1)
    markup = types.ReplyKeyboardMarkup(row_width=2)

    buttons = []

    card_pair = get_word(message)
    target_word = card_pair[1]
    translate = card_pair[0]
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
    try:
        create_cards(message)
    except IndexError:
        bot.send_message(message.chat.id, 'Deine Worte gingen zu Ende :(')


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        with conn. cursor() as cur:
            cur.execute(f'''
                DELETE FROM words
                WHERE answer_word = %s AND user_id = %s;
            ''', (data['target_word'], message.chat.id, ))
        conn.commit()
        bot.send_message(message.chat.id, 'Worte übrig: ' +
                         str(len(get_words(message))))


@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def get_question_word(message):
    cid = message.chat.id
    userStep[cid] = 1
    remove_keyboard: True
    sent = bot.send_message(
      message.chat.id,
      "Was wird das Fragewort sein?",
      reply_markup=ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(sent, get_answer_word)


must_add = ['', '']


def get_answer_word(message):
    must_add[0] = message.text
    bot.send_message(message.chat.id, 'Und was ist die Antwort?')
    bot.register_next_step_handler(message, add_words_to_db)


def add_words_to_db(message):
    bot.send_message(message.chat.id, 'Danke schön!')
    must_add[1] = message.text
    with conn.cursor() as cur:
        cur.execute(f"""
            INSERT INTO  words(question_word, answer_word, user_id)
            VALUES (%s, %s, %s);
        """, (must_add[0], must_add[1], message.chat.id))
    conn.commit()
    time.sleep(1)
    bot.send_message(message.chat.id, 'Worte übrig: ' +
                     str(len(get_words(message))))
    time.sleep(1)
    bot.send_message(message.chat.id, 'Weitermachen?')
    next_cards(message)


@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    buttons = []
    text = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data['target_word']
        if text == target_word:
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


if __name__ == '__main__':
    with psycopg2.connect(database=database, user=user, password=password) as conn:
        create_tables()
        bot.add_custom_filter(custom_filters.StateFilter(bot))
        bot.infinity_polling(skip_pending=True)
