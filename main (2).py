import os
import asyncio
import time
import json
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from threading import Thread

# ================== CONFIG ==================
API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")  # Admin Telegram ID
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ================== KANAL FSM ==================
def save_kanallar():
    try:
        with open('kanallar.json', 'w') as f:
            json.dump(kanallar, f)
    except Exception as e:
        print(f"Деректерді сақтау қатесі: {e}")

def load_kanallar():
    try:
        with open('kanallar.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

kanallar = load_kanallar()

class KanalFSM(StatesGroup):
    url = State()
    kanal_id = State()
    vaqt = State()
    limit = State()

def kanal_menu():
    menu = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="kanal_add")],
        [InlineKeyboardButton(text="📋 Kanal ro'yxati", callback_data="kanal_list")],
        [InlineKeyboardButton(text="❌ Kanal o'chirish", callback_data="kanal_delete")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="kanal_back")],
    ])
    return menu

# ================== COMMANDS ==================
@dp.message(Command("start"))
async def start_cmd(msg: types.Message):
    start_text = (
        "👋 Assalomu alaykum! Bu bot orqali quyidagi kanallarga obuna bo'lishingiz mumkin:\n\n"
        "📌 <b>Majburiy obuna kanallari:</b>\n"
    )
    
    if kanallar:
        for i, (k_id, data) in enumerate(kanallar.items(), 1):
            start_text += f"{i}. {data['url']} - {data['vaqt']} minut, {len(data.get('members', []))}/{data['limit']} odam\n"
        
        register_btn = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Ro'yxatdan o'tish", callback_data="user_register")]
        ])
        start_text += "\nRo'yxatdan o'tish uchun quyidagi tugmani bosing yoki /register buyrug'ini yuboring"
        await msg.answer(start_text, reply_markup=register_btn, parse_mode="HTML")
    else:
        await msg.answer("ℹ️ Hozircha majburiy obuna kanallari mavjud emas")

@dp.message(Command("kanal"))
async def kanal_cmd(msg: types.Message):
    if str(msg.from_user.id) == ADMIN_ID:
        await msg.answer("📌 Kanal menyusi:", reply_markup=kanal_menu())
    else:
        await msg.answer("⚠️ Sizga ruxsat yo'q!")

# ================== KANAL HANDLERS ==================
@dp.callback_query(lambda c: c.data == "kanal_add")
async def kanal_add(call: types.CallbackQuery, state: FSMContext):
    if str(call.from_user.id) == ADMIN_ID:
        await call.message.answer("📎 Kanal havolasini yuboring:")
        await state.set_state(KanalFSM.url)
    else:
        await call.answer("⚠️ Sizga ruxsat yo'q!", show_alert=True)

@dp.message(KanalFSM.url)
async def kanal_url(msg: types.Message, state: FSMContext):
    await state.update_data(url=msg.text)
    await msg.answer("🆔 Kanal ID yuboring:")
    await state.set_state(KanalFSM.kanal_id)

@dp.message(KanalFSM.kanal_id)
async def kanal_id(msg: types.Message, state: FSMContext):
    await state.update_data(kanal_id=msg.text)
    await msg.answer("⏳ Qancha vaqt majburiy obunada turadi? (masalan: 5 minut)")
    await state.set_state(KanalFSM.vaqt)

@dp.message(KanalFSM.vaqt)
async def kanal_vaqt(msg: types.Message, state: FSMContext):
    try:
        parts = msg.text.split()
        vaqt = int(parts[0]) if parts else 0
        if vaqt <= 0:
            raise ValueError
        await state.update_data(vaqt=vaqt)
        await msg.answer("👥 Nechta odam obuna bo'lishi kerak? (masalan: 2)")
        await state.set_state(KanalFSM.limit)
    except:
        await msg.answer("⚠️ Iltimos, musbat son kiriting! Masalan: '5 minut'")

@dp.message(KanalFSM.limit)
async def kanal_limit(msg: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        data.update({
            "limit": int(msg.text),
            "created_at": time.time(),
            "end_time": (datetime.now() + timedelta(minutes=data['vaqt'])).timestamp(),
            "members": []
        })
        kanal_id = data["kanal_id"]
        kanallar[kanal_id] = data
        save_kanallar()
        
        await msg.answer(
            f"✅ Kanal qo'shildi!\n"
            f"URL: {data['url']}\n"
            f"ID: {data['kanal_id']}\n"
            f"Vaqt: {data['vaqt']} minut\n"
            f"Limit: {data['limit']} odam"
        )
    except ValueError:
        await msg.answer("⚠️ Iltimos, raqam kiriting!")
    finally:
        await state.clear()

@dp.callback_query(lambda c: c.data == "kanal_list")
async def kanal_list(call: types.CallbackQuery):
    if not kanallar:
        await call.message.answer("📭 Hech qanday kanal yo'q.")
    else:
        text = "📋 Majburiy obunadagi kanallar:\n"
        for i, (k_id, data) in enumerate(kanallar.items(), 1):
            text += f"{i}. {data['url']} (ID: {k_id}) - {data['limit']} odam, {data['vaqt']} minut\n"
        await call.message.answer(text)

@dp.callback_query(lambda c: c.data == "kanal_delete")
async def kanal_delete(call: types.CallbackQuery):
    if not kanallar:
        await call.message.answer("📭 Hech qanday kanal yo'q.")
        return
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"O'chirish: {data['url']}", callback_data=f"del_{k_id}")]
        for k_id, data in kanallar.items()
    ])
    markup.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="kanal_back")])
    await call.message.answer("❌ Qaysi kanalni o'chirmoqchisiz?", reply_markup=markup)

@dp.callback_query(lambda c: c.data.startswith("del_"))
async def confirm_delete(call: types.CallbackQuery):
    k_id = call.data.split("_")[1]
    if k_id in kanallar:
        del kanallar[k_id]
        save_kanallar()
        await call.message.answer("✅ Kanal o'chirildi.")
    else:
        await call.message.answer("⚠️ Bu kanal topilmadi.")

@dp.callback_query(lambda c: c.data == "kanal_back")
async def kanal_back(call: types.CallbackQuery):
    await call.message.answer("🔙 Orqaga qaytdingiz.", reply_markup=kanal_menu())

# ================== REGISTER HANDLERS ==================
@dp.callback_query(lambda c: c.data == "user_register")
async def register_callback(call: types.CallbackQuery):
    await call.answer()
    await register_member_func(call.message)

@dp.message(Command("register"))
async def register_command(msg: types.Message):
    await register_member_func(msg)

async def register_member_func(message: types.Message):
    user_id = message.from_user.id
    registered = False
    
    for kanal_id, data in list(kanallar.items()):
        if user_id not in data.get("members", []):
            data.setdefault("members", []).append(user_id)
            save_kanallar()
            registered = True
            await message.answer(
                f"✅ <b>{data['url']}</b> kanaliga muvaffaqiyatli ro'yxatdan o'tdingiz!\n"
                f"🔹 Majburiy obuna muddati: {data['vaqt']} minut\n"
                f"👥 Joriy obunachilar: {len(data['members'])}/{data['limit']}",
                parse_mode="HTML"
            )
    
    if not registered:
        await message.answer("ℹ️ Siz allaqachon barcha kanallarga ro'yxatdan o'tgansiz yoki hozircha kanallar mavjud emas")

# ================== AUTOMATIC CHECK ==================
async def check_kanallar():
    while True:
        await asyncio.sleep(60)  # Har 1 minutda tekshiramiz
        now = time.time()
        for kanal_id, data in list(kanallar.items()):
            # Vaqt tugaganligini tekshirish
            if now >= data['end_time']:
                del kanallar[kanal_id]
                save_kanallar()
                await bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"⏳ Vaqt tugadi: {data['url']} kanali o'chirildi"
                )
            
            # Limit yetganligini tekshirish
            if len(data.get('members', [])) >= data['limit']:
                del kanallar[kanal_id]
                save_kanallar()
                await bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"👥 Limit yetdi ({data['limit']} odam): {data['url']} kanali o'chirildi"
                )

# ================== FLASK (Render uchun) ==================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running ✅"

# ================== RUN ==================
async def start_bot():
    asyncio.create_task(check_kanallar())  # Avtomatik tekshiruvni ishga tushiramiz
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Flask серверни алохида threadда ишга туширамиз
    port = int(os.getenv("PORT", 5000))
    Thread(target=lambda: app.run(host="0.0.0.0", port=port, debug=False)).start()

    # Telegram ботни ишга туширамиз
    asyncio.run(start_bot())
