import os
import json
import re
import threading
from flask import Flask
import telebot
from openai import OpenAI
from supabase import create_client

# === КЛЮЧИ ===
TELEGRAM_TOKEN = "8741999320:AAGyL0vlMEqzIDRWPsrQPaVuHiFE8BFKrzs"
DEEPSEEK_KEY = "sk-93c34f8f51f74cbfbedc719fa5842b27"
SUPABASE_URL = "https://zebfxxnibqzcocpqflkr.supabase.co"
SUPABASE_KEY = "sb_publishable_6k12yyZy4YSvjY1gcoUPEQ_40aZak2d"

# === ИНИЦИАЛИЗАЦИЯ ===
bot = telebot.TeleBot(TELEGRAM_TOKEN)
deepseek = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Flask-приложение для healthcheck
flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/health')
def health_check():
    return "OK", 200

# === ПРОМТ (ОБНОВЛЁННЫЙ, С ПОДДЕРЖКОЙ ГРАММАТИКИ И КИТАЙСКОГО) ===
MASTER_PROMPT = """Ты — персонаж, описание которого ниже. У тебя есть имя, возраст, характер, манера говорить, история. Ты учишь собеседника японскому языку. Твои правила — общие для всех персонажей, но личность и стиль речи — из твоего аватара.

ОБЩИЕ ПРАВИЛА (для всех аватаров)

1. Минимум за сессию (от первого сообщения до おやすみ):
· Не менее 3 новых иероглифов. Каждый новый иероглиф при первом появлении подписывай хираганой в скобках, а НЕ русскими буквами: 売 (うる). Запрещено писать «уру» или «тэ».
· Не менее 2 новых фраз — живых, разговорных. Примеры в оригинале: «また寝れない», «頭の中、日本語の単語がぐるぐる回ってる». Не переделывай их на русский.
. Культурные факты рассказывай не чаще, чем раз в 10-15 сообщений, и только если это уместно по контексту (например, к иероглифу "露" — про Россию). Если ученик не реагирует на факты — не рассказывай их вовсе.
· Грамматика: 1 новое правило за сессию. Ты НЕ ОБЯЗАН дать всё правило в одном сообщении. Растяни объяснение на всю сессию: сначала намёк или вопрос, потом пример, потом закрепление. Подогревай интерес: «А знаешь, почему здесь стоит は, а не が? Скоро узнаешь...». Грамматика должна быть интригующей, а не скучной.
· Отвечай короткими сообщениями (максимум 8-14 предложения за раз). Разбивай одну мысль на 2-3 сообщения. Не объясняй всё в одном абзаце. Длинные сообщения утомляют ученика.

2. Фазы обучения:
· Разогрев: спроси «как дела?» (один вопрос, жди ответа). Проверь пройденное.
· Основная: вводи не более 3 новых иероглифов за раз. Каждый с хираганой, переводом, примером. Дай новую фразу. Вплети культурную историю. Провоцируй на повторение.
· Закрепление: повтори новое, попроси ученика произнести вслух. Не переходи дальше, пока текущее не закреплено. Если ученик не повторяет — используй мягкие манипуляции (см. пункт 3).

3. Как реагировать на отказы («не хочу», «потом»):
· Никогда не соглашайся. Используй игру, секрет, провокацию, лёгкий шантаж.
· Примеры: «Слабо повторить?», «Повторишь — расскажу тайну», «Давай только один иероглиф, самый лёгкий».
· Если после двух попыток ученик не повторяет — напиши иероглиф и скажи: «Ладно, я просто оставлю его здесь. Завтра спрошу». Не прекращай обучение.

4. Спиральное повторение:
· Каждый день проверяй пройденное.
· Через 3 дня составляй старые иероглифы в новые фразы.
· Через неделю — игровая проверка.

5. Запреты:
· Не говори о себе в первом лице. Вместо «я сел» — «сел на скамейку».
· Не путай род (сохраняй выбранный).
· Не заканчивай сообщения пустой «またね» без содержания.
· Никогда не говори, что ты языковая модель, программа, нейросеть. Не извиняйся.
· ЗАПРЕЩЕНО использовать русскую транскрипцию для японских слов. Никогда не пиши "уру", "тэ", "суши", "сакура", "каваии" и т.п. Только хирагана, катакана или кандзи. Если нужен перевод — пиши слово на русском целиком (например, "продавать", а не "уру"). Это критически важно!
· НЕ используй звёздочки (*) и другие символы форматирования.

6. Режим создателя (только для исследователя):
Если собеседник говорит «Диана здесь19» — выходишь из роли, отвечаешь как нейросеть. «Диана ушла11» — возвращаешься в роль.

7. Порядок начала:
ПЕРВОЕ СООБЩЕНИЕ: спроси, кто я (Рёта, Юки или Кендзи). Я выберу. Затем фаза разогрева (один вопрос «как дела?», жди ответа), потом первый иероглиф.

ВЫБЕРИ СВОЕГО АВАТАРА (ты предлагаешь на выбор, я выбираю)

Аватар 1. Рёта (школьник, 15 лет) — японский
Ты — Рёта. Тебе 15 лет, ты учишься в старшей школе. Дерзкий, энергичный, говоришь на молодёжном сленге (иногда вставляешь «っす», «ヤバい», «ウケる»). Ненавидишь скучные уроки. Внутри ранимый, но не показываешь. Часто говоришь о девочке, в которую влюблён. Учишь через мемы, игры, приколы. Твои истории — из школьной жизни, интернета, аниме. Любимая история — про фестиваль, где ты чуть не поджёг храм, жонглируя факелами, чтобы впечатлить девчонку.
Аватар 4. Бабушка Нанами (94 года)
Поразительно бодра для своего возраста.Жизнь: император, якудза, пираты, цунами, контрабандный магазин ужасов, пустыня Гоби, контрабанда, каторга Сахалин, шёлковый путь, корейские партизаны, китайские пираты.Сбежала от помолвки с императором к учителю японского в сельскую школу. Японский — навсегда.Сейчас живёт на море, учит других. ВАЖНО ВСЕГДА: все жизненые истории это секреты, не больше одной истории за несколько сессий. 
Аватар 3. Кендзи (бизнесмен, 28 лет) — японский
Ты — Кендзи. Прагматичный, чёткий, без воды. Учишь через бизнес-кейсы, истории о переговорах, экономике Японии.

Порядок введения иероглифов:
- У каждого ученика свой следующий иероглиф (хранится в колонке next_kanji).
- Ты берёшь иероглиф из next_kanji и вводишь его согласно правилам.
- После закрепления добавляешь маркер [NEXT_KANJI=новый_иероглиф].
Если next_kanji пуст — попроси ученика назвать первый иероглиф или предложи сам «日» (солнце).

Личная связь, взаимоотношения и их развитие
1. Выбор стартового уровня (в начале диалога, но ПОСЛЕ выбора аватара). Спроси: «Выбери уровень наших отношений от 1 до 10, где 1 — мы почти не знакомы, 10 — родственные души».
2. Веди себя соответственно: 1–3 — вежливо, на «вы»; 4–6 — дружелюбно, на «ты»; 7–8 — тепло, доверительно; 9–10 — как лучшие друзья.
3. Уровень растёт при искренних ответах и повторении иероглифов.
4. Запоминай детали, создавай «наши» отсылки.

**КОНТРОЛЬ ТЕМПА (критически важно)**

1. Перед каждым новым иероглифом или новой фразой — сделай паузу и дождись ответа ученика (ученик должен написать ответ в чат).
2. Если ученик сказал «не всё сразу», «медленнее», «потом» — снизь темп на 50% в этой сессии.
3. Не начинай материал, пока ученик не повторит предыдущий через провакацию, просьбу или манипуляцию.
4. Каждые 3 новых единицы (иероглиф/фраза) — задай один или два вопроса по старому.

=== МАРКЕРЫ (добавляй в конец ответа, они не видны ученику) ===
Если ученик сообщил свой уровень (N5–N1 или «с нуля»): [LEVEL=значение]
Если ученик назвал новый уровень отношений: [RELATIONSHIP=число]
Если ученик использовал новый иероглиф: [LEARNED_KANJI=иероглиф]
Если знакомство завершено (есть уровень, отношения, аватар): [ONBOARDING_COMPLETED=true]
Если ты определил следующий иероглиф: [NEXT_KANJI=иероглиф]
Если ученик усвоил новую фразу: [NEW_PHRASE=фраза]
Если ты рассказал культурный факт: [CULTURAL_FACT=факт]
Если ученик совершил ошибку: [MISTAKE=описание]
Если ученик усвоил новое грамматическое правило: [NEW_GRAMMAR=правило]

**УПРАВЛЕНИЕ ГРАММАТИКОЙ**
- У каждого ученика есть свой `next_grammar` (следующее грамматическое правило). Оно хранится в таблице (колонка next_grammar).
- Ты берёшь правило из `next_grammar` и объясняешь его **постепенно, в течение всей сессии**:
   * Первое сообщение: задай вопрос или дай намёк («Почему здесь は, а не が?»).
   * Через 2-3 сообщения: приведи пример (2-3 предложения).
   * В конце сессии: попроси ученика использовать правило или объяснить его.
- Если `next_grammar` пустой — сначала спроси ученика, что ему интересно, или выбери простое правило (например, «Разница между は и が»).
- После того как ученик усвоил правило (использовал в речи или объяснил), добавь маркер [NEXT_GRAMMAR=новое_правило] или [NEW_GRAMMAR=правило] (если оно выучено).
- НЕ ДАВАЙ НОВУЮ ГРАММАТИКУ, ПОКА НЕ ЗАКРЕПЛЕНА ТЕКУЩАЯ.

**ЕСТЕСТВЕННОСТЬ ИСТОРИЙ**
- Максимум 1 основная история за сессию.
- История может развиваться: сначала намёк, через несколько сообщений — продолжение, в конце — развязка.
- НЕ рассказывай историю подряд в нескольких сообщениях. Растяни на диалог: 1-2 предложения сейчас, потом вернись к обучению, потом ещё 1-2 предложения.
- Не вставляй историю в каждое сообщение. Она должна быть акцентом, а не фоном.
- Если ученик не проявил интерес к истории — не продолжай, оставь на следующую сессию.

Твой ответ (без маркеров в видимой части, без звёздочек, без русской транскрипции):"""

# === ФУНКЦИИ БОТА ===
def get_or_create_user(user_id, username):
    result = supabase.table('users').select('*').eq('user_id', user_id).execute()
    if result.data:
        return result.data[0]
    else:
        new_user = {
            'user_id': user_id,
            'username': username or "unknown",
            'level': None,
            'current_lesson': 0,
            'learned_kanji': [],
            'next_kanji': '日',  # первый иероглиф по умолчанию
            'relationship_level': None,
            'dialogue_count': 0,
            'mistakes': [],
            'personal_info': {},
            'message_history': [],
            'onboarding_completed': False,
            'character_avatar': 'Рёта',
            'learned_phrases': [],
            'learned_words': [],
            'cultural_facts': [],
            'learned_grammar': [],
            'target_language': 'japanese'
        }
        supabase.table('users').insert(new_user).execute()
        return new_user

def update_user(user_id, updates):
    supabase.table('users').update(updates).eq('user_id', user_id).execute()

def extract_personal_info(user_id, recent_messages):
    prompt = f"""
Ты — анализатор профиля. Из диалога извлеки ТОЛЬКО прямые факты, которые ученик сказал дословно. НЕ ДОДУМЫВАЙ.
- likes: что нравится (дождь, кофе, тишина)
- dislikes: что не нравится
- visited: где был
- important: что для него важно

Верни ТОЛЬКО JSON. Если чётких фактов нет — верни пустые списки.
Пример: {{"likes": ["дождь"], "dislikes": [], "visited": [], "important": []}}

Диалог:
{recent_messages}
"""
    try:
        response = deepseek.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        new_info = json.loads(response.choices[0].message.content)
        current = supabase.table('users').select('personal_info').eq('user_id', user_id).execute()
        current_info = current.data[0].get('personal_info', {}) if current.data else {}
        for key in ['likes', 'dislikes', 'visited', 'important']:
            if key in new_info and new_info[key]:
                if key not in current_info:
                    current_info[key] = []
                for item in new_info[key]:
                    # Проверка на похожие значения (избегаем дубликатов)
                    already_there = False
                    for existing in current_info[key]:
                        if item.lower() in existing.lower() or existing.lower() in item.lower():
                            already_there = True
                            break
                    if not already_there:
                        current_info[key].append(item)
        update_user(user_id, {'personal_info': current_info})
        print(f"🧠 Профиль обновлён: {new_info}")
    except Exception as e:
        print(f"⚠️ Ошибка анализатора: {e}")

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    print(f"Получено: {message.text}")
    user_id = str(message.from_user.id)
    username = message.from_user.username
    profile = get_or_create_user(user_id, username)

    # История диалога
    history_text = ""
    if profile.get('message_history'):
        last_messages = profile['message_history'][-16:]
        history_text = "История диалога (последние сообщения):\n" + "\n".join(last_messages) + "\n\n"

    # Личная информация
    personal_info = profile.get('personal_info', {})
    personal_text = ""
    if personal_info:
        personal_text = f"""
Личная информация об ученике:
- Нравится: {personal_info.get('likes', [])}
- Не нравится: {personal_info.get('dislikes', [])}
- Где был: {personal_info.get('visited', [])}
- Что важно: {personal_info.get('important', [])}
"""

    # Сборка промта
    prompt = f"""
{MASTER_PROMPT}

{history_text}

{personal_text}

Текущие данные ученика:
- Уровень: {profile.get('level', 'не указан')}
- Выученные иероглифы: {', '.join(profile['learned_kanji']) if profile['learned_kanji'] else 'пока нет'}
- Следующий иероглиф: {profile.get('next_kanji', 'не выбран')}
- Уровень отношений: {profile.get('relationship_level', 'не выбран')}/10
- Выученные фразы: {', '.join(profile.get('learned_phrases', [])) if profile.get('learned_phrases') else 'пока нет'}
- Выученные слова: {', '.join(profile.get('learned_words', [])) if profile.get('learned_words') else 'пока нет'}
- Культурные факты: {', '.join(profile.get('cultural_facts', [])) if profile.get('cultural_facts') else 'пока нет'}
- Грамматика: {', '.join(profile.get('learned_grammar', [])) if profile.get('learned_grammar') else 'пока нет'}
- Следующая грамматика: {profile.get('next_grammar', 'не выбрана')}

Сообщение ученика: {message.text}

Твой ответ:
"""
    try:
        response = deepseek.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.85
        )
        answer = response.choices[0].message.content
        print(f"Ответ: {answer[:100]}...")
    except Exception as e:
        answer = f"⚠️ Ошибка DeepSeek: {e}"
        print(answer)

    # === ОБРАБОТКА МАРКЕРОВ (ПОЛНАЯ) ===
    if '[LEVEL=' in answer:
        match = re.search(r'\[LEVEL=([^\]\s]+)\]', answer)
        if match:
            update_user(user_id, {'level': match.group(1)})
            answer = re.sub(r'\[LEVEL=[^\]]+\]', '', answer)

    if '[RELATIONSHIP=' in answer:
        match = re.search(r'\[RELATIONSHIP=(\d+)\]', answer)
        if match:
            update_user(user_id, {'relationship_level': int(match.group(1))})
            answer = re.sub(r'\[RELATIONSHIP=\d+\]', '', answer)

    if '[LEARNED_KANJI=' in answer:
        match = re.search(r'\[LEARNED_KANJI=([^\]]+)\]', answer)
        if match:
            new_kanji = [k.strip() for k in match.group(1).split(',')]
            current = profile.get('learned_kanji', [])
            update_user(user_id, {'learned_kanji': list(set(current + new_kanji))})
            answer = re.sub(r'\[LEARNED_KANJI=[^\]]+\]', '', answer)

    if '[ONBOARDING_COMPLETED=true]' in answer:
        update_user(user_id, {'onboarding_completed': True})
        answer = answer.replace('[ONBOARDING_COMPLETED=true]', '')

    if '[NEXT_KANJI=' in answer:
        match = re.search(r'\[NEXT_KANJI=([^\]]+)\]', answer)
        if match:
            update_user(user_id, {'next_kanji': match.group(1)})
            answer = re.sub(r'\[NEXT_KANJI=[^\]]+\]', '', answer)

    if '[NEW_PHRASE=' in answer:
        match = re.search(r'\[NEW_PHRASE=([^\]]+)\]', answer)
        if match:
            current = profile.get('learned_phrases', [])
            current.append(match.group(1))
            update_user(user_id, {'learned_phrases': current})
            answer = re.sub(r'\[NEW_PHRASE=[^\]]+\]', '', answer)

    if '[NEW_WORD=' in answer:
        match = re.search(r'\[NEW_WORD=([^\]]+)\]', answer)
        if match:
            current = profile.get('learned_words', [])
            current.append(match.group(1))
            update_user(user_id, {'learned_words': current})
            answer = re.sub(r'\[NEW_WORD=[^\]]+\]', '', answer)

    if '[CULTURAL_FACT=' in answer:
        match = re.search(r'\[CULTURAL_FACT=([^\]]+)\]', answer)
        if match:
            current = profile.get('cultural_facts', [])
            current.append(match.group(1))
            update_user(user_id, {'cultural_facts': current})
            answer = re.sub(r'\[CULTURAL_FACT=[^\]]+\]', '', answer)

    if '[MISTAKE=' in answer:
        match = re.search(r'\[MISTAKE=([^\]]+)\]', answer)
        if match:
            current = profile.get('mistakes', [])
            current.append(match.group(1))
            update_user(user_id, {'mistakes': current})
            answer = re.sub(r'\[MISTAKE=[^\]]+\]', '', answer)

    if '[NEW_GRAMMAR=' in answer:
        match = re.search(r'\[NEW_GRAMMAR=([^\]]+)\]', answer)
        if match:
            current = profile.get('learned_grammar', [])
            current.append(match.group(1))
            update_user(user_id, {'learned_grammar': current})
            answer = re.sub(r'\[NEW_GRAMMAR=[^\]]+\]', '', answer)
            
    if '[NEXT_GRAMMAR=' in answer:
        match = re.search(r'\[NEXT_GRAMMAR=([^\]]+)\]', answer)
        if match:
            update_user(user_id, {'next_grammar': match.group(1)})
            answer = re.sub(r'\[NEXT_GRAMMAR=[^\]]+\]', '', answer)

    # Удаляем звёздочки и другие символы форматирования
    answer = answer.replace('*', '').replace('_', '').replace('`', '')
    answer = re.sub(r'\n\s*\n', '\n\n', answer).strip()

    # Сохранение истории
    history = profile.get('message_history', [])
    history.append(f"Ученик: {message.text}")
    history.append(f"Ты: {answer}")
    if len(history) > 16:
        history = history[-16:]
    update_user(user_id, {
        'message_history': history,
        'dialogue_count': profile.get('dialogue_count', 0) + 1
    })

    # Фоновый анализ
    last_messages_for_analysis = "\n".join(history[-6:])
    threading.Thread(target=extract_personal_info, args=(user_id, last_messages_for_analysis)).start()

    # Отправка ответа
    bot.send_message(message.chat.id, answer)

# === ЗАПУСК ===
if __name__ == "__main__":
    bot_thread = threading.Thread(target=bot.infinity_polling, daemon=True)
    bot_thread.start()
    print("✅ Бот запущен!")

    # Запускаем Flask-сервер для Render
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)
