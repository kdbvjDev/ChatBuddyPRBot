import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, \
    CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler

from gpt import ChatGptService
from util import load_message, load_prompt, send_text_buttons, send_text, \
    send_image, show_main_menu

# Загрузка токенов из .env файла
load_dotenv()

# Токены для взаимодействия с Telegram и ChatGPT
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GPT_TOKEN = os.getenv("ChatGPT_TOKEN")
chat_gpt = ChatGptService(GPT_TOKEN)

# Константы для состояния разговоров
MENU, RANDOM, GPT, TALK, QUIZ, TRANSLATE = range(6)

# Настройка логирования для отслеживания работы бота
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения, повторяя их пользователю."""
    await update.message.reply_text(update.message.text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возвращает пользователя в главное меню."""
    await update.callback_query.answer()
    await start(update, context)
    return MENU

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Инициализирует главное меню и отображает пользователю доступные команды."""
    text = load_message('main')
    await send_text(update, context, text)
    await show_main_menu(update, context, {
        'start': 'Главное меню',
        'random': 'Узнать случайный интересный факт 🧠',
        'gpt': 'Задать вопрос чату GPT 🤖',
        'talk': 'Поговорить с известной личностью 👤',
        'quiz': 'Поучаствовать в квизе ❓',
        'translate': 'Перевод текстов'
    })
    return MENU

async def random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрашивает у ChatGPT случайный интересный факт и отображает его с возможностью запроса нового."""
    prompt = load_prompt('random')
    ans = await chat_gpt.send_question(prompt, '')
    await send_text_buttons(update, context, ans, {
        'random_more': 'еще один факт',
        'end': 'Достаточно'
    })
    return RANDOM

async def random_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает запрос на новый случайный факт и возвращает его пользователю."""
    await update.callback_query.answer()
    await random(update, context)
    return RANDOM

async def gpt_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Инициализирует режим общения с ChatGPT и задает начальную подсказку для диалога."""
    prompt = load_prompt('gpt')
    chat_gpt.set_prompt(prompt)
    msg = load_message('gpt')
    await send_text(update, context, msg)
    return GPT

async def gpt_dialog_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает сообщения в режиме диалога с ChatGPT."""
    qs = update.message.text
    ans = await chat_gpt.add_message(qs)
    await send_text_buttons(update, context, ans, {'end': 'Достаточно'})
    return GPT

async def talk_with_person(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает пользователю список знаменитых личностей для общения."""
    message = load_message('talk')
    await send_text_buttons(update, context, message, {
        'talk_cobain': 'Курт Кобейн',
        'talk_hawking': 'Стивен Хокинг',
        'talk_nietzsche': 'Фридрих Ницше',
        'talk_queen': 'Эли́забет Алекса́ндра Мэ́ри Ви́ндзор',
        'talk_tolkien': 'Джон Рональд Руэл Толкин',
    })
    return TALK

async def talk_with_person_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Инициирует диалог с выбранной знаменитой личностью, отображая ее изображение и текст."""
    await update.callback_query.answer()
    cb = update.callback_query.data
    prompt = load_prompt(cb)
    chat_gpt.set_prompt(prompt)
    await send_image(update, context, cb)
    await send_text(update, context, f'Можно начинать общение.')
    return TALK

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Инициализация викторины с выбором темы."""
    context.user_data.update({"quiz_count": 0, "quiz_score": 0})
    chat_gpt.set_prompt(load_prompt('quiz'))
    msg = load_message('quiz')
    await send_image(update, context, 'quiz')
    await send_text_buttons(update, context, msg, {
        'quiz_prog': 'Программирование на Python',
        'quiz_math': 'Теории алгоритмов, множеств и матанализа',
        'quiz_biology': 'Биология'
    })
    return QUIZ

async def quiz_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор темы викторины или запрос на следующий вопрос."""
    await update.callback_query.answer()
    topic = update.callback_query.data

    if topic == 'quiz_more':
        context.user_data["quiz_count"] += 1
        next_qs = "quiz_more"
    else:
        context.user_data.update({"quiz_count": 1, "quiz_score": 0})
        await send_text(update, context, "Начинаем игру!")
        next_qs = topic

    question = await chat_gpt.add_message(next_qs)
    await send_text(update, context, question)
    return QUIZ

async def quiz_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ответы пользователя и показывает текущий результат викторины."""
    ans = update.message.text
    response = await chat_gpt.add_message(ans)

    # Проверка на правильность ответа и обновление счёта
    if "правильно!" == response.lower():
        context.user_data["quiz_score"] += 1

    await send_text(update, context, response)
    await send_text_buttons(
        update, context,
        f'Правильных ответов: {context.user_data["quiz_score"]} из {context.user_data["quiz_count"]}.',
        {'quiz_more': 'Следующий вопрос', 'end': 'Достаточно'}
    )
    return QUIZ

async def translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Режим переводчика: инициализация с выбором языка и дальнейшая обработка перевода."""
    # Установка основной подсказки для ChatGPT
    chat_gpt.set_prompt(
        'ты переводчик, сам определяешь на каком языке написан текст и переводишь на выбранный пользователем'
    )
    
    # Отображение кнопок выбора языка для перевода, добавлена кнопка "Достаточно" для выхода
    await send_text_buttons(
        update, context, 
        'Вы выбрали режим переводчика. Выберите язык на который перевести:', 
        {'ru': 'Русский', 'en': 'English', 'end': 'Достаточно'}
    )
    return TRANSLATE

async def handle_translation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка запроса на перевод текста или выбора языка."""

    if update.callback_query:
        if update.callback_query.data == 'end':  # Если нажата кнопка "Достаточно"
            await update.callback_query.answer()
            await start(update, context)
            return MENU
        
        # Если пришел выбор языка
        await update.callback_query.answer()
        selected_lang = update.callback_query.data
        context.user_data['translation_language'] = selected_lang
        await send_text(update, context, 'Пришлите текст для перевода.')

    elif update.message:  # Если пришел текст для перевода
        selected_lang = context.user_data.get('translation_language', 'en')  # По умолчанию English
        text = update.message.text
        await send_text(update, context, 'В процессе перевода...')

        # Передаем текст для перевода на выбранный язык
        ans = await chat_gpt.add_message(f"{selected_lang}: {text}")
        await send_text_buttons(update, context, ans, {'end': 'Достаточно'})  # Отправляем переведенный текст
    
    return TRANSLATE


def main() -> None:
    """Главная функция, которая инициализирует бота и запускает его работу."""
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Настройка обработчика разговоров и состояний
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MENU: [
                CommandHandler('random', random),
                CommandHandler('gpt', gpt_mode),
                CommandHandler('talk', talk_with_person),
                CommandHandler('quiz', quiz),  # Добавляем квиз в меню
                CommandHandler('translate', translate)
            ],
            RANDOM: [
                CallbackQueryHandler(random_button, pattern='random_'),
                CallbackQueryHandler(cancel, pattern='end')
            ],
            GPT: [
                CallbackQueryHandler(cancel, pattern='end'),
                MessageHandler(filters=filters.TEXT & ~filters.COMMAND, callback=gpt_dialog_mode)

            ],
            TALK: [
                CallbackQueryHandler(cancel, pattern='end'),
                CallbackQueryHandler(talk_with_person_dialog),
                MessageHandler(filters=filters.TEXT & ~filters.COMMAND, callback=gpt_dialog_mode),
            ],
            QUIZ: [
                CallbackQueryHandler(quiz_button, pattern='^quiz_'),  # Для выбора темы
                CallbackQueryHandler(cancel, pattern='end'),  # Для завершения квиза
                MessageHandler(filters.TEXT & ~filters.COMMAND, quiz_dialog),  # Для обработки ответов
            ],
            TRANSLATE: [
                CallbackQueryHandler(handle_translation),  # Для выбора языка и завершения перевода
                CallbackQueryHandler(cancel, pattern='end'),  # Для выхода в главное меню
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_translation)  # Для перевода текста
            ],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    # Добавление обработчика разговоров к приложению и запуск бота
    app.add_handler(conv_handler)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
