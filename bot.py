import telebot
from openai import OpenAI
from supabase import create_client
import os
import json
import threading
import re

# ===== ВАШИ КЛЮЧИ (замените на реальные) =====
TELEGRAM_TOKEN = "8741999320:AAGyL0vlMEqzIDRWPsrQPaVuHiFE8BFKrzs"
DEEPSEEK_KEY = "sk-93c34f8f51f74cbfbedc719fa5842b27"
SUPABASE_URL = "https://zebfxxnibqzcocpqflkr.supabase.co"
SUPABASE_KEY = "sb_publishable_6k12yyZy4YSvjY1gcoUPEQ_40aZak2d"
# ============================================

bot = telebot.TeleBot(TELEGRAM_TOKEN)
deepseek = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ========== ЗАГРУЗКА ПРОМТА ИЗ SUPABASE ==========
def load_prompt_template():
    try:
        result = supabase.table('prompt_templates').select('template').eq('id', 'master_prompt').eq('is_active', True).execute()
        if result.data:
            return result.data[0]['template']
    except Exception as e:
        print(f"⚠️ Ошибка загрузки промта из БД: {e}")
    return "Ты — учитель японского. Отвечай кратко."

MASTER_PROMPT = load_prompt_template()
print("✅ Промт загружен из Supabase")

# ========== РАБОТА С ПРОФИЛЕМ ==========
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
            'next_kanji': None,
            'relationship_level': None,
            'dialogue_count': 0,
            'mistakes': [],
            'personal_info': {},
            'message_history': [],
            'onboarding_completed': False,
            'character_avatar': 'Рёта'
        }
        supabase.table('users').insert(new_user).execute()
        return new_user

def update_user(user_id, updates):
    supabase.table('users').update(updates).eq('user_id', user_id).execute()

# ========== ФОНОВЫЙ АНАЛИЗАТОР ФАКТОВ ==========
def extract_personal_info(user_id, recent_messages):
    prompt = f"""
Ты — анализатор профиля. Из диалога извлеки факты об ученике:
- likes: что нравится (например, дождь, кофе, тишина)
- dislikes: что не нравится (гроза, шум, лук)
- visited: где был (страны, города, музеи)
- important: что для него важно (семья, учёба, здоровье, сон)

Верни ТОЛЬКО JSON. Если факта нет — пустой список.
Пример: {{"likes": ["дождь", "тишина"], "dislikes": [], "visited": ["Москва"], "important": ["семья"]}}

Диалог (последние сообщения):
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
                    if item not in current_info[key]:
                        current_info[key].append(item)
        update_user(user_id, {'personal_info': current_info})
        print(f"🧠 Профиль обновлён: {new_info}")
    except Exception as e:
        print(f"⚠️ Ошибка анализатора: {e}")

# ========== ОСНОВНОЙ ОБРАБОТЧИК ==========
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    print(f"Получено: {message.text}")
    user_id = str(message.from_user.id)
    username = message.from_user.username
    profile = get_or_create_user(user_id, username)

    # --- ИСТОРИЯ ДИАЛОГА ---
    history_text = ""
    if 'message_history' in profile and profile['message_history']:
        last_messages = profile['message_history'][-16:]
        history_text = "История диалога (последние сообщения):\n" + "\n".join(last_messages) + "\n\n"

    # --- ЛИЧНАЯ ИНФОРМАЦИЯ ---
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

    # --- СБОРКА ПРОМТА ---
    prompt = f"""
{MASTER_PROMPT}

{history_text}

{personal_text}

Текущие данные ученика:
- Уровень: {profile.get('level', 'не указан')}
- Выученные иероглифы: {', '.join(profile['learned_kanji']) if profile['learned_kanji'] else 'пока нет'}
- Уровень отношений: {profile.get('relationship_level', 'не выбран')}/10

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

    # --- ОБРАБОТКА МАРКЕРОВ ---
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

    answer = re.sub(r'\n\s*\n', '\n\n', answer).strip()

    # --- СОХРАНЕНИЕ ИСТОРИИ ---
    history = profile.get('message_history', [])
    history.append(f"Ученик: {message.text}")
    history.append(f"Ты: {answer}")
    if len(history) > 16:
        history = history[-16:]
    update_user(user_id, {
        'message_history': history,
        'dialogue_count': profile.get('dialogue_count', 0) + 1
    })

    # --- ФОНОВЫЙ АНАЛИЗ ---
    last_messages_for_analysis = "\n".join(history[-6:])
    threading.Thread(target=extract_personal_info, args=(user_id, last_messages_for_analysis)).start()

    # --- ОТПРАВКА ОТВЕТА ---
    bot.reply_to(message, answer)

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("✅ Бот запущен!")
    bot.infinity_polling()
