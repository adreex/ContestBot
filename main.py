from telebot.types import ReplyKeyboardMarkup, Update
from telebot import TeleBot, apihelper

from aiohttp import web
import ssl

import requests
import time

from database import DBHelper
import config


bot = TeleBot(config.bot_token)


def check_mass(msg):
    if msg.chat.id in config.admins:
        text = msg.text
        caption = msg.caption
        if (text and '/mass' in text and not text.strip() == '/mass') or (caption and '/mass' in caption):
            return True


@bot.message_handler(content_types=['photo', 'text'], func=check_mass)
def handle_mass_mailing(message):
    successful, failed = mass_mailing(message)
    text = '💬 Сообщение отправлено <b>{}</b> пользователям.\n\n<b>{}</b> пользователей были удалены.'
    bot.send_message(message.chat.id, text.format(successful, failed), parse_mode='html')


def mass_mailing(message):
    successful, failed = 0, 0
    with DBHelper() as db:
        users = db.get_users()

    for user in users:
        try:
            if message.photo:
                file_id = message.photo[0].file_id
                path = bot.get_file(file_id).file_path
                photo = requests.get(f'https://api.telegram.org/file/bot{config.bot_token}/{path}')

                caption = message.caption.replace('/mass', '').strip()
                caption = None if caption == '' else caption
                bot.send_photo(user, photo.content, caption=caption)

            elif message.text:
                text = message.text.replace('/mass', '').strip()
                if not text:
                    return 0, 0
                bot.send_message(user, text)

            successful += 1
            time.sleep(1 / 30)

        except apihelper.ApiException:
            with DBHelper() as db:
                db.del_user(user)
            failed += 1

    return successful, failed


@bot.message_handler(commands=['users'], func=lambda msg: msg.chat.id in config.admins)
def handle_participants_amount(message):
    with DBHelper() as db:
        amount = db.get_amount_of_users()
        bot.send_message(message.chat.id, f'Пользователей в боте: {amount}')


@bot.message_handler(commands=['participants'], func=lambda msg: msg.chat.id in config.admins)
def handle_participants_amount(message):
    with DBHelper() as db:
        amount = db.get_participants_amount()
        bot.send_message(message.chat.id, f'Участников конкурса: {amount}')


@bot.message_handler(content_types=['text'], func=lambda msg: '/get' in msg.text and len(msg.text.split()) == 2)
def handle_start(message):
    if message.chat.id in config.admins:
        limit = message.text.replace('/get', '').strip()

        if limit.isdigit():
            with DBHelper() as db:
                winners = []

                while not len(winners) == int(limit):
                    if db.get_participants_amount() >= int(limit):
                        user_id = db.get_winner()
                        member = bot.get_chat_member(config.channel_id, user_id)

                        if member is not None and member.status in ('creator', 'administrator', 'member'):
                            link = f'[user](tg://user?id={member.user.id}'
                            winners.append(link)

                        else:
                            db.set(user_id, 'subscribed', 0)
                    else:
                        bot.send_message(message.chat.id, '❗Еще не набралось такое количество участников')
                        break
                else:
                    bot.send_message(message.chat.id, ', '.join(winners), parse_mode='markdown')
        else:
            bot.send_message(message.chat.id, '❗️Некорректный аргумент')


@bot.message_handler(commands=['start'])
def handle_start(message):
    with DBHelper() as db:
        db.add_user(message.from_user.id)

    text = f'💬 Привет! Для участия в конкурсе подпишитесь на {config.channel_name}, а затем нажмите на кнопку ниже ' \
        'или просто напишите боту "Участвовать"'
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.row('Участвовать')

    bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.message_handler(func=lambda msg: msg.text == 'Участвовать')
def handle_join(message):
    member = bot.get_chat_member(config.channel_id, message.from_user.id)

    if member is not None and member.status in ('creator', 'administrator', 'member'):
        with DBHelper() as db:
            db.set(message.from_user.id, 'subscribed', 1)
            text = '💬 Отлично, теперь просто дожидайтесь итогов конкурса'
            bot.send_message(message.chat.id, text, reply_markup=ReplyKeyboardMarkup())
    else:
        text = f'❗️Для участия конкурсе требуется подписаться на {config.channel_name}'
        bot.send_message(message.chat.id, text)


async def webhook_handle(request):
    if request.path.replace('/', '') == bot.token:
        request_body_dict = await request.json()
        update = Update.de_json(request_body_dict)
        bot.process_new_updates([update])
        return web.Response()
    else:
        return web.Response(status=403)


def webhook_setup():
    webhook_host = config.host
    webhook_port = config.port
    webhook_listen = '0.0.0.0'  # or probably ip address

    webhook_ssl_cert = 'webhook_cert.pem'
    webhook_ssl_priv = 'webhook_pkey.pem'

    webhook_url_base = f'https://{webhook_host}:{webhook_port}'
    webhook_url_path = f'/{config.bot_token}/'

    app = web.Application()
    app.router.add_post(f'/{config.bot_token}/', webhook_handle)

    bot.remove_webhook()
    bot.set_webhook(url=webhook_url_base + webhook_url_path, certificate=open(webhook_ssl_cert, 'r'))

    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.load_cert_chain(webhook_ssl_cert, webhook_ssl_priv)

    web.run_app(
        app,
        host=webhook_listen,
        port=webhook_port,
        ssl_context=context,
    )


def main():
    info = bot.get_me()

    print(f'\nName: {info.first_name}.\n'
          f'Username: @{info.username}.\n'
          f'User_id: {info.id}.\n')

    webhook_setup()


if __name__ == '__main__':
    main()
