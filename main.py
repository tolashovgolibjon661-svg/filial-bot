import logging
import datetime
import os
import threading
from flask import Flask
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# --- RENDER UCHUN FLASK SERVER (Uyg'oq saqlash uchun) ---
app = Flask(__name__)

@app.route('/')
def function_index():
    return "Bot ishlayapti va uyg'oq!"

@app.route('/health')
def health():
    return "OK", 200

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
# --------------------------------------------------------

# 1. Bot tokeningiz
TOKEN = "9104508816:AAEDOdUYjtEFKNZeO6FbAFdWhJLQe9oxIK8"

# 2. Ma'lumotlar borib tushadigan Telegram guruhning ID raqami 
GROUP_ID = -4290725255

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# 6 ta filial ro'yxati
FILIALS = [
    "Mingbuloq", "Chust", "Buramatut", 
    "Uychi", "Chorsu", "Uchqoʻrgʻon"
]

# Mahsulotlar ro'yxati (37 xil)
PRODUCTS = [
    "Pitsa karobka katta", "Pitsa karobka kichik", "Toʻrt karobka",
    "Perojni katta karobka", "Perojni kichik karobka", "Tandir lavash",
    "Tvister", "Klab sendvich", "K F S karobka", "Kofe sumka",
    "Kfs paqir", "Saboy stakan 200ml", "Kombo uchun stakan 330",
    "Kofe stakan 300 ml", "Kola stakan 400 ml", "Kola stakan 500",
    "Mini lavash", "Lavash oddiy", "Lavash achchiq", "Lavash pishloqli",
    "Donar paket", "Pitsa fergament", "Xot dog fergament", "Gam fergament",
    "Nabor salfetka", "Saboy paket katta", "Saboy kichik", "Fri karobka katta",
    "Saboy salafan paket 3kg", "Pitsa paket salafan", "patnistga fergament",
    "Fri mini karobka", "Kids boxs karobka", "stiker", "zubachistka", "salat idish"
]

# Xotirada qoldiqlarni saqlash uchun baza (Boshlang'ich qiymat: 0 dona)
# Har bir filial va mahsulot uchun 0 dan boshlanadi
DATABASE = {filial: {product: 0 for product in PRODUCTS} for filial in FILIALS}

class SkladState(StatesGroup):
    choosing_action = State()
    choosing_product = State()
    entering_amount = State()

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for f in FILIALS:
        keyboard.add(types.KeyboardButton(f))
    
    await message.answer(
        "Assalomu alaykum! Sklad upakovka qog'ozlarini nazorat qilish botiga xush kelibsiz.\n"
        "Kerakli filialni tanlang:", reply_markup=keyboard
    )

@dp.message_handler(text=FILIALS)
async def select_filial(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['filial'] = message.text
    
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(types.KeyboardButton("➕ Kirim qilish (Qo'shish)"), types.KeyboardButton("➖ Chiqim qilish (Berish)"))
    keyboard.add(types.KeyboardButton("📦 Qoldiq"))
    keyboard.add(types.KeyboardButton("🔙 Orqaga / Bosh menu"))
    
    await state.set_state(SkladState.choosing_action.state)
    await message.answer(f"Siz **{message.text}**ni tanladingiz. Amalni tanlang:", reply_markup=keyboard, parse_mode="Markdown")

@dp.message_handler(state=SkladState.choosing_action)
async def select_action(message: types.Message, state: FSMContext):
    if message.text == "🔙 Orqaga / Bosh menu":
        await state.finish()
        return await send_welcome(message)
    
    if message.text == "📦 Qoldiq":
        async with state.proxy() as data:
            filial = data.get('filial', 'Filial')
        
        filial_stocks = DATABASE.get(filial, {})
        text = f"📦 **{filial} filiali bo'yicha joriy qoldiqlar:**\n\n"
        
        for product, qty in filial_stocks.items():
            text += f"▪️ {product}: **{qty} dona**\n"
            
        await message.answer(text, parse_mode="Markdown")
        return
    
    if message.text not in ["➕ Kirim qilish (Qo'shish)", "➖ Chiqim qilish (Berish)"]:
        await message.answer("Iltimos, tugmalardan birini tanlang!")
        return

    async with state.proxy() as data:
        data['action'] = message.text

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for p in PRODUCTS:
        keyboard.add(types.KeyboardButton(p))
    keyboard.add(types.KeyboardButton("🔙 Orqaga"))

    await state.set_state(SkladState.choosing_product.state)
    await message.answer("Kerakli mahsulotni tanlang:", reply_markup=keyboard)

@dp.message_handler(state=SkladState.choosing_product)
async def select_product(message: types.Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await state.set_state(SkladState.choosing_action.state)
        async with state.proxy() as data:
            filial_name = data.get('filial', FILIALS[0])
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        keyboard.add(types.KeyboardButton("➕ Kirim qilish (Qo'shish)"), types.KeyboardButton("➖ Chiqim qilish (Berish)"))
        keyboard.add(types.KeyboardButton("📦 Qoldiq"))
        keyboard.add(types.KeyboardButton("🔙 Orqaga / Bosh menu"))
        await message.answer(f"Siz **{filial_name}**dasiz. Amalni tanlang:", reply_markup=keyboard, parse_mode="Markdown")
        return
    
    if message.text not in PRODUCTS:
        await message.answer("Ro'yxatdan to'g'ri mahsulotni tanlang!")
        return

    async with state.proxy() as data:
        data['product'] = message.text

    await state.set_state(SkladState.entering_amount.state)
    await message.answer(f"Tanlandi: **{message.text}**\nMiqdorini kiriting (faqat raqam, masalan: *150*):", parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(state=SkladState.entering_amount)
async def save_to_group(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, miqdorni faqat raqamlarda kiriting (masalan: 50):")
        return

    amount = int(message.text)
    async with state.proxy() as data:
        filial = data['filial']
        action = data['action']
        product = data['product']

    # Qoldiqlarni avtomatik yangilash
    if action == "➕ Kirim qilish (Qo'shish)":
        DATABASE[filial][product] += amount
    elif action == "➖ Chiqim qilish (Berish)":
        DATABASE[filial][product] = max(0, DATABASE[filial][product] - amount)

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_name = message.from_user.full_name

    report_text = (
        f"📦 **Yangi amal qayd etildi!**\n\n"
        f"📅 Sana: {now}\n"
        f"🏢 Filial: {filial}\n"
        f"📋 Mahsulot: {product}\n"
        f"🔄 Amal: {action}\n"
        f"📊 Miqdor: {amount} dona\n"
        f"👤 Mas'ul: {user_name}"
    )

    try:
        await bot.send_message(chat_id=GROUP_ID, text=report_text, parse_mode="Markdown")
    except Exception as e:
        print(f"Guruhga yuborishda xatolik: {e}")

    await state.finish()
    
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for f in FILIALS:
        keyboard.add(types.KeyboardButton(f))

    await message.answer(
        f"✅ Muvaffaqiyatli saqlandi va guruhga yuborildi!\n\n"
        f"🏢 Filial: {filial}\n"
        f"📦 Mahsulot: {product}\n"
        f"🔄 Amal: {action}\n"
        f"📊 Miqdor: {amount} dona",
        reply_markup=keyboard
    )

if __name__ == '__main__':
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()
    
    executor.start_polling(dp, skip_updates=True)
    
