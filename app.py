"""
Telegram-бот "Сыр к вину"
Стек: Python + pyTelegramBotAPI (telebot) + Flask (для Render.com)

Установка зависимостей:
    pip install pyTelegramBotAPI python-dotenv flask

Запуск на Render:
    Start Command: gunicorn wine_cheese_bot:flask_app

Запуск локально:
    python wine_cheese_bot.py
"""

import logging
import os
import re
import threading
import telebot
from flask import Flask
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Логирование
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # вывод в консоль
        logging.FileHandler("wine_cheese_bot.log", encoding="utf-8"),  # вывод в файл
    ],
)
logger = logging.getLogger("wine_cheese_bot")

# ---------------------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------------------

load_dotenv()  # загружает переменные окружения из файла .env

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.critical(
        "Не найден BOT_TOKEN. Убедитесь, что файл .env существует и содержит "
        "строку BOT_TOKEN=ваш_токен_бота"
    )
    raise ValueError(
        "Не найден BOT_TOKEN. Убедитесь, что файл .env существует и содержит "
        "строку BOT_TOKEN=ваш_токен_бота"
    )

CHANNEL_USERNAME = "@wine_and_cheese_guide"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# ---------------------------------------------------------------------------
# Flask-приложение для Render.com (чтобы сервис не засыпал и не падал)
# ---------------------------------------------------------------------------

flask_app = Flask('')


@flask_app.route('/')
def home():
    """Минимальный эндпоинт, чтобы Render видел активность на порту."""
    return "🍷🧀 Wine & Cheese Bot is running!"


@flask_app.route('/health')
def health():
    """Эндпоинт для проверки здоровья (можно использовать для Uptime Robot)."""
    return {"status": "ok", "message": "Bot is alive"}


def run_web_server():
    """Запускает Flask-сервер (используется при локальном запуске)."""
    port = int(os.environ.get('PORT', 8000))
    logger.info(f"Запуск веб-сервера на порту {port}...")
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


# ---------------------------------------------------------------------------
# Функции для работы с Markdown
# ---------------------------------------------------------------------------

def escape_md(text: str) -> str:
    """
    Экранирует спецсимволы legacy Markdown Telegram (_ * ` [ ]),
    чтобы текст вроде '@wine_and_cheese_guide' не ломал парсинг entities.
    """
    try:
        return re.sub(r"([_*`\[\]])", r"\\\1", text)
    except (TypeError, re.error) as exc:
        logger.error("Ошибка экранирования текста '%s': %s", text, exc)
        return str(text)


# Заранее экранированная версия названия канала для использования в тексте
CHANNEL_USERNAME_MD = escape_md(CHANNEL_USERNAME)

# ---------------------------------------------------------------------------
# База данных сочетаний вино/сыр
# ---------------------------------------------------------------------------

wine_cheese_pairings = [
    {
        "wine": "Каберне Совиньон",
        "cheeses": ["Выдержанная Гауда", "Чеддер", "Пекорино"],
        "cheese_makers": ["Сыроварня Соболева", "Grand Milk"],
        "websites": ["sobolevcheese-opt.ru", "grandmilk.co"],
        "pairing_description": "Полнотелое, танинное вино требует насыщенных, солоноватых и твердых сыров, которые не потеряются на его фоне.",
        "cheese_descriptions": {
            "Выдержанная Гауда": "Насыщенный твердый сыр, не теряется на фоне танинного вина.",
            "Чеддер": "Насыщенный, солоноватый твердый сыр, выдерживает мощь Каберне.",
            "Пекорино": "Солоноватый твердый сыр из овечьего молока, отлично балансирует танины."
        },
        "note": "В ассортименте есть выдержанный Чеддер, Гауда и Пекорино из овечьего молока."
    },
    {
        "wine": "Пино Нуар",
        "cheeses": ["Камамбер", "Бри", "Грюйер"],
        "cheese_makers": ["Сыроварня (Москва)", "Сыроварня Соболева"],
        "websites": ["syrovarnya.com", "sobolevcheese-opt.ru"],
        "pairing_description": "Элегантное и легкое красное вино с ягодными нотами идеально подчеркивает сливочность и грибные оттенки мягких сыров, а также ореховость полутвердых.",
        "cheese_descriptions": {
            "Камамбер": "Мягкий сыр со сливочной текстурой и грибными оттенками.",
            "Бри": "Мягкий сыр со сливочной текстурой и грибными оттенками.",
            "Грюйер": "Полутвердый сыр с выраженным ореховым вкусом."
        },
        "note": "Классические Камамбер и Бри, а также твердые сыры в стиле Грюйер."
    },
    {
        "wine": "Шардоне",
        "cheeses": ["Камамбер", "Бри"],
        "cheese_makers": ["Сыроварня (Москва)"],
        "websites": ["syrovarnya.com"],
        "pairing_description": "Маслянистость и баланс кислотности вина хорошо сочетаются со сливочной текстурой мягких сыров с белой плесенью, особенно если Шардоне не слишком дубовое.",
        "cheese_descriptions": {
            "Камамбер": "Мягкий сыр с белой плесенью и сливочной текстурой.",
            "Бри": "Мягкий сыр с белой плесенью и сливочной текстурой."
        },
        "note": "Мягкие сыры с белой плесенью, идеально подходящие к маслянистому Шардоне."
    },
    {
        "wine": "Рислинг",
        "cheeses": ["Фета", "Козий сыр", "Бри"],
        "cheese_makers": ["De Gali"],
        "websites": ["degali.ru"],
        "pairing_description": "Свежая кислотность и цитрусовые ноты Рислинга отлично контрастируют с соленостью Феты или сливочностью Бри, создавая сбалансированную пару.",
        "cheese_descriptions": {
            "Фета": "Соленый рассольный сыр, контрастирует со свежей кислотностью вина.",
            "Козий сыр": "Свежий сыр с легкой кислинкой, гармонирует с цитрусовыми нотами.",
            "Бри": "Сливочный мягкий сыр, создает баланс с цитрусовой кислотностью."
        },
        "note": "Специализация на козьих сырах и рассольных сырах (Фета)."
    },
    {
        "wine": "Мерло",
        "cheeses": ["Козий сыр", "Грюйер"],
        "cheese_makers": ["Сыроварня Соболева"],
        "websites": ["sobolevcheese-opt.ru"],
        "pairing_description": "Мягкое и округлое Мерло хорошо сочетается с козьими сырами, подчеркивая их свежесть, а также с твердыми сырами орехового вкуса.",
        "cheese_descriptions": {
            "Козий сыр": "Мягкое Мерло подчеркивает свежесть козьего сыра.",
            "Грюйер": "Твердый сыр орехового вкуса, гармонирует с округлостью Мерло."
        },
        "note": "Козья Гауда и выдержанные твердые сыры орехового профиля."
    },
    {
        "wine": "Зинфандель",
        "cheeses": ["Острый Чеддер", "Копченая Гауда", "Халлуми"],
        "cheese_makers": ["Сыроварня (Москва)", "Логовская сыроварня", "Сыроварня Соболева"],
        "websites": ["syrovarnya.com", "metro-cc.ru", "sobolevcheese-opt.ru"],
        "pairing_description": "Насыщенный, пряный и плотный вкус этого вина требует таких же ярких и смелых сыров с выраженным характером.",
        "cheese_descriptions": {
            "Острый Чеддер": "Яркий сыр с выраженным характером, выдерживает плотность Зинфанделя.",
            "Копченая Гауда": "Смелый сыр с дымными нотами, перекликается с пряностью вина.",
            "Халлуми": "Плотный сыр с выраженным характером, подходит к насыщенному вину."
        },
        "note": "Яркие сыры, включая Халлуми для жарки, и выдержанный Чеддер."
    },
    {
        "wine": "Сира (Шираз)",
        "cheeses": ["Выдержанные твердые сыры", "Пряные сыры"],
        "cheese_makers": ["Сыроварня Соболева"],
        "websites": ["sobolevcheese-opt.ru"],
        "pairing_description": "Мощное, пряное вино с нотами перца и ежевики идеально дополняют выдержанные сыры с пикантным вкусом и плотной текстурой.",
        "cheese_descriptions": {
            "Выдержанные твердые сыры": "Пикантный вкус и плотная текстура дополняют мощь Сиры.",
            "Пряные сыры": "Пикантные сыры перекликаются с перчеными нотами вина."
        },
        "note": "Специализация на выдержанных твердых сырах (Чеддер винтажный 24+ мес.)."
    },
    {
        "wine": "Совиньон Блан",
        "cheeses": ["Козий сыр", "Бри", "Камамбер"],
        "cheese_makers": ["De Gali", "Сыроварня (Москва)"],
        "websites": ["degali.ru", "syrovarnya.com"],
        "pairing_description": "Легкое и освежающее вино с травянистыми нотами — классическая пара к козьему сыру, а также к сливочным мягким сырам.",
        "cheese_descriptions": {
            "Козий сыр": "Классическая пара к травянистому Совиньон Блан.",
            "Бри": "Сливочный мягкий сыр, гармонирует с освежающей кислотностью вина.",
            "Камамбер": "Сливочный мягкий сыр, гармонирует с освежающей кислотностью вина."
        },
        "note": "Классическая пара: свежий козий сыр и сливочные мягкие сыры."
    },
    {
        "wine": "Пино Гриджо",
        "cheeses": ["Моцарелла", "Проволоне"],
        "cheese_makers": ["BuonLatte", "Маркур"],
        "websites": ["buonlatte.ru", "cheese-marcur.com"],
        "pairing_description": "Легкое, хрустящее и нейтральное вино отлично подходит к молодым, свежим сырам с мягкой или слегка тягучей текстурой.",
        "cheese_descriptions": {
            "Моцарелла": "Молодой свежий сыр с мягкой, слегка тягучей текстурой.",
            "Проволоне": "Молодой свежий сыр с мягкой, слегка тягучей текстурой."
        },
        "note": "Итальянские технологии: свежая Моцарелла и Проволоне."
    },
    {
        "wine": "Кьянти",
        "cheeses": ["Пекорино", "Пармезан"],
        "cheese_makers": ["Grand Milk", "Провинция Че"],
        "websites": ["grandmilk.co", "provinciache.orgs.biz"],
        "pairing_description": "Итальянская классика: терпкое Кьянти из Санджовезе превосходно сочетается с твердыми, солоноватыми сырами, особенно из овечьего молока.",
        "cheese_descriptions": {
            "Пекорино": "Твердый солоноватый сыр из овечьего молока — итальянская классика.",
            "Пармезан": "Твердый солоноватый сыр с ярким вкусом, выдерживает терпкость Кьянти."
        },
        "note": "Пекорино из овечьего молока и зрелые твердые сыры в стиле Пармезана."
    },
    {
        "wine": "Розе",
        "cheeses": ["Козий сыр", "Фета", "Бри"],
        "cheese_makers": ["De Gali", "Сыроварня (Москва)"],
        "websites": ["degali.ru", "syrovarnya.com"],
        "pairing_description": "Универсальное розовое вино подходит к широкому спектру сыров: от свежих и соленых до сливочных, не перебивая их вкус.",
        "cheese_descriptions": {
            "Козий сыр": "Свежий сыр, вкус которого не перебивается легким Розе.",
            "Фета": "Соленый рассольный сыр, универсальная пара к Розе.",
            "Бри": "Сливочный мягкий сыр, не перебивается вкусом вина."
        },
        "note": "Универсальная подборка: от соленых рассольных до сливочных сыров."
    },
    {
        "wine": "Портвейн",
        "cheeses": ["Стилтон", "Горгонзола", "Рокфор"],
        "cheese_makers": ["Сыроварня Соболева", "Сыроварня (Орёл)"],
        "websites": ["sobolevcheese-opt.ru", "cheeseunion.orgs.biz"],
        "pairing_description": "Сладкое и крепкое десертное вино — идеальный партнер для насыщенных, соленых и пикантных голубых сыров с плесенью.",
        "cheese_descriptions": {
            "Стилтон": "Насыщенный, соленый и пикантный голубой сыр с плесенью.",
            "Горгонзола": "Насыщенный, соленый и пикантный голубой сыр с плесенью.",
            "Рокфор": "Насыщенный, соленый и пикантный голубой сыр с плесенью."
        },
        "note": "Российские аналоги сыров с голубой плесенью по традиционным рецептурам."
    },
]

# Список названий вин для приветственного и fallback-сообщений (в исходном порядке + "Другое")
WINE_LIST_TEXT = ("Каберне Совиньон, Пино Нуар, Шардоне, Рислинг, Мерло, Зинфандель, "
                  "Сира, Совиньон Блан, Пино Гриджо, Кьянти, Розе, Портвейн, Другое")

# ---------------------------------------------------------------------------
# Индекс для поиска без учета регистра
# ---------------------------------------------------------------------------

# Ключ - название вина в нижнем регистре, значение - словарь с данными
try:
    PAIRINGS_INDEX = {item["wine"].lower(): item for item in wine_cheese_pairings}
except (KeyError, AttributeError) as exc:
    logger.critical("Ошибка построения индекса вин из wine_cheese_pairings: %s", exc)
    raise

# Дополнительные варианты написания (синонимы), чтобы пользователь мог
# писать вино чуть иначе и все равно получить совпадение
WINE_ALIASES = {
    "сира": "сира (шираз)",
    "шираз": "сира (шираз)",
    "сира (шираз)": "сира (шираз)",
    "совиньон блан": "совиньон блан",
    "каберне совиньон": "каберне совиньон",
}

FALLBACK_TEXT = (
    "Я умею только подбирать сыр к вину. Напиши, пожалуйста, название вина из списка: "
    f"{WINE_LIST_TEXT}."
)

# Ссылки на сыроварни для сыров, упомянутых в универсальном совете ("Другое").
# Данные взяты из wine_cheese_pairings: "Копченая Гауда" и "Острый Чеддер" (Зинфандель).
OTHER_WINE_CHEESE_LINKS = {
    "Гауда": ("Логовская сыроварня", "metro-cc.ru"),
    "Чеддер": ("Сыроварня (Москва)", "syrovarnya.com"),
}


def _cheese_md_link(cheese_label: str) -> str:
    """Строит Markdown-ссылку '[cheese_label](url)' по данным из OTHER_WINE_CHEESE_LINKS."""
    maker, site = OTHER_WINE_CHEESE_LINKS[cheese_label]
    url = site if site.startswith("http") else f"https://{site}"
    return f"[{escape_md(cheese_label)}]({url})"


OTHER_WINE_TEXT = (
    "Пока у меня нет отдельной рекомендации именно для этого вина 🍷\n\n"
    "Но вот универсальный совет: к большинству вин хорошо подходят сыры средней "
    f"твердости с нейтральным вкусом — например, {_cheese_md_link('Гауда')} или молодой "
    f"{_cheese_md_link('Чеддер')}, они редко перебивают вкус вина и подходят почти к "
    "любому бокалу.\n\n"
    "Если хочешь точный подбор — напиши одно из вин: "
    f"{WINE_LIST_TEXT}.\n\n"
    f"Подписывайся на {CHANNEL_USERNAME_MD} — там каждый день новые гастро-идеи! 🧀🍷"
)

START_TEXT = (
    "Привет! 🍷 Я помогу тебе подобрать идеальный сыр к твоему вину.\n\n"
    "Просто напиши название вина из списка: "
    f"{WINE_LIST_TEXT}.\n\n"
    "Напишу совет и порекомендую сыр с ссылкой для заказа.\n\n"
    f"Подписывайся на {CHANNEL_USERNAME_MD} — там каждый день новые гастро-идеи!"
)


# ---------------------------------------------------------------------------
# Формирование ответа
# ---------------------------------------------------------------------------

def build_pairing_response(item: dict) -> str:
    """Собирает текст ответа для найденного вина."""
    try:
        wine = escape_md(item["wine"])
        cheeses_str = escape_md(", ".join(item["cheeses"]))
        pairing_description = escape_md(item["pairing_description"])

        # Ссылки на сыроварни: [Название сыроварни](сайт)
        # (текст ссылки экранируем, URL — нет, так как он не сканируется на entities)
        links = []
        for maker, site in zip(item["cheese_makers"], item["websites"]):
            url = site if site.startswith("http") else f"https://{site}"
            links.append(f"[{escape_md(maker)}]({url})")
        links_str = ", ".join(links)

        # Описания сыров из cheese_descriptions, сгруппированные по совпадающему тексту
        cheese_descriptions = item.get("cheese_descriptions", {})
        grouped = []  # список [description, [cheese1, cheese2, ...]]
        for cheese in item["cheeses"]:
            description = cheese_descriptions.get(cheese)
            if not description:
                continue
            for group in grouped:
                if group[0] == description:
                    group[1].append(cheese)
                    break
            else:
                grouped.append([description, [cheese]])

        descriptions_lines = [
            f"— *{escape_md(', '.join(cheeses))}*: {escape_md(description)}"
            for description, cheeses in grouped
        ]
        descriptions_str = "\n".join(descriptions_lines)

        response = (
            f"🍷 Вино: {wine}\n"
            f"🧀 Сыр: {cheeses_str} ({links_str}) — {pairing_description}\n\n"
            f"{descriptions_str}\n\n"
            f"Хочешь больше таких сочетаний? Подписывайся на {CHANNEL_USERNAME_MD} 🧀🍷"
        )
        return response
    except (KeyError, TypeError, AttributeError) as exc:
        logger.error("Ошибка формирования ответа для вина '%s': %s",
                     item.get("wine", "неизвестно"), exc)
        return (
            "Упс, не получилось сформировать подробную рекомендацию 😔\n"
            "Попробуй, пожалуйста, ещё раз или выбери другое вино из списка."
        )


# ---------------------------------------------------------------------------
# Хендлеры
# ---------------------------------------------------------------------------

def safe_send(chat_id, text, **kwargs):
    """
    Отправляет сообщение с parse_mode="Markdown", а при ошибке парсинга entities
    (например, из-за неэкранированного спецсимвола) отправляет тот же текст
    как обычный текст, чтобы пользователь в любом случае получил ответ.
    Любые другие ошибки отправки логируются и не приводят к падению бота.
    """
    try:
        bot.send_message(chat_id, text, **kwargs)
    except telebot.apihelper.ApiTelegramException as exc:
        if "can't parse entities" in str(exc):
            logger.warning(
                "Ошибка парсинга Markdown-entities для chat_id=%s, отправляю "
                "текст без разметки. Детали: %s", chat_id, exc
            )
            try:
                bot.send_message(chat_id, text, parse_mode=None, **kwargs)
            except telebot.apihelper.ApiTelegramException as exc2:
                logger.error(
                    "Не удалось отправить сообщение chat_id=%s даже без "
                    "разметки: %s", chat_id, exc2
                )
        else:
            logger.error(
                "Ошибка Telegram API при отправке сообщения chat_id=%s: %s",
                chat_id, exc
            )
    except Exception as exc:  # noqa: BLE001 - страхуемся от любых неожиданных ошибок
        logger.exception(
            "Неожиданная ошибка при отправке сообщения chat_id=%s: %s", chat_id, exc
        )


@bot.message_handler(commands=["start"])
def handle_start(message):
    try:
        logger.info("Команда /start от chat_id=%s (user=%s)",
                    message.chat.id, message.from_user.username)
        safe_send(message.chat.id, START_TEXT, disable_web_page_preview=True)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ошибка в обработчике /start: %s", exc)


@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_message(message):
    try:
        user_text = message.text.strip().lower()
        logger.info("Сообщение от chat_id=%s (user=%s): %r",
                    message.chat.id, message.from_user.username, message.text)

        if user_text == "другое":
            safe_send(message.chat.id, OTHER_WINE_TEXT, disable_web_page_preview=True)
            return

        # Прямое совпадение по названию
        item = PAIRINGS_INDEX.get(user_text)

        # Проверка синонимов, если прямого совпадения нет
        if item is None and user_text in WINE_ALIASES:
            item = PAIRINGS_INDEX.get(WINE_ALIASES[user_text])

        if item is not None:
            safe_send(message.chat.id, build_pairing_response(item),
                      disable_web_page_preview=True)
        else:
            safe_send(message.chat.id, FALLBACK_TEXT)
    except Exception as exc:  # noqa: BLE001 - обработчик не должен падать целиком
        logger.exception(
            "Неожиданная ошибка при обработке сообщения chat_id=%s: %s",
            getattr(message.chat, "id", "unknown"), exc
        )
        try:
            bot.send_message(
                message.chat.id,
                "Что-то пошло не так при обработке твоего сообщения. Попробуй ещё раз.",
            )
        except Exception:  # noqa: BLE001
            logger.error("Не удалось отправить сообщение об ошибке пользователю.")


# ---------------------------------------------------------------------------
# Запуск бота в отдельном потоке (для Gunicorn)
# ---------------------------------------------------------------------------

def run_bot():
    """Запускает Telegram-бота в отдельном потоке."""
    logger.info("Запуск Telegram-бота...")
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as exc:
        logger.critical(f"Бот аварийно завершил работу: {exc}")
        raise


# Запускаем бота в фоновом потоке при импорте модуля (для Gunicorn)
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()
logger.info("Telegram-бот запущен в фоновом потоке")

# ---------------------------------------------------------------------------
# Запуск при локальном выполнении
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Запуск через python wine_cheese_bot.py")
    # Запускаем Flask (для локальной разработки)
    port = int(os.environ.get('PORT', 8000))
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)