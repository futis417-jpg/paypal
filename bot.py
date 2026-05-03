import os
import asyncio
import random
import string
from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from playwright.async_api import async_playwright
from flask import Flask
from threading import Thread

# --- CONFIGURACIÓN DE TELEGRAM ---
API_ID = 32926930
API_HASH = "07216e34019bc7fbbaa05954131e8bdc"
BOT_TOKEN = "8058527405:AAEr7xSTTdBxxxAwfiyyUoM-qVaoYu_O9nE"

app = Client("paypal_pro_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- MINI WEB PARA RENDER (GRATIS) ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot de Ishak está Online!", 200

def run_web():
    # Render asigna un puerto automáticamente
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host='0.0.0.0', port=port)

# --- LÓGICA DEL BOT ---
user_data = {}

def gen_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=17)) + 'F'

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;700;800&display=swap');
        body {{ font-family: 'Open Sans', sans-serif; background-color: #f7f9fc; margin: 0; }}
        .receipt-card {{ max-width: 540px; background: white; margin: 0 auto; padding: 60px 50px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
    </style>
</head>
<body>
    <div style="padding: 40px 0; background: #f7f9fc; width: 600px;">
        <div style="font-size: 14px; color: #6c7378; text-align: center; margin-bottom: 35px;">Hola, {emisor}</div>
        <div class="receipt-card">
            <center><img src="https://www.paypalobjects.com/paypal-ui/logos/svg/paypal-mark-color.svg" width="45"></center>
            <h1 style="font-size: 42px; font-weight: 800; text-align: center; margin: 40px 0; letter-spacing: -1.5px; line-height: 1.1; color: #000;">
                Ha enviado {monto} € EUR a {receptor}
            </h1>
            <div style="font-size: 19px; margin-bottom: 35px; color: #000;">Detalles de la transacción</div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 25px;">
                <div>
                    <div style="font-weight: 700; font-size: 15px; color: #000;">Id. de transacción</div>
                    <div style="color: #0070ba; text-decoration: underline; font-size: 15px;">{id_trans}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-weight: 700; font-size: 15px; color: #000;">Fecha de la transacción</div>
                    <div style="font-size: 15px; color: #000;">{fecha}</div>
                </div>
            </div>
            <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
            <div style="display: flex; justify-content: space-between; font-size: 15px; margin-bottom: 10px;">
                <span style="font-weight: 700; color: #000;">Dinero enviado</span>
                <span style="color: #000;">{monto} € EUR</span>
            </div>
            <div style="margin: 15px 0 10px 0; font-size: 15px; font-weight: 400; color: #000;">Pagado con:</div>
            <div style="display: flex; justify-content: space-between; font-size: 15px;">
                <span style="color: #000;">Saldo de PayPal (EUR)</span>
                <span style="color: #000;">{monto} € EUR</span>
            </div>
            <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
            <div style="display: flex; justify-content: space-between; font-weight: 700; font-size: 16px; color: #000;">
                <span>Ha pagado</span>
                <span>{monto} € EUR</span>
            </div>
        </div>
        <center style="margin-top: 40px;">
            <img src="https://www.paypalobjects.com/paypal-ui/logos/svg/paypal-mark-color.svg" width="30">
        </center>
    </div>
</body>
</html>
"""

async def capture_receipt(data):
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox"])
        page = await browser.new_page()
        content = HTML_TEMPLATE.format(
            emisor=data['emisor'], receptor=data['receptor'],
            monto=data['monto'], fecha=data['fecha'], id_trans=gen_id()
        )
        await page.set_content(content)
        await asyncio.sleep(1.5)
        path = f"recibo_{gen_id()}.png"
        await page.screenshot(path=path, full_page=True)
        await browser.close()
        return path

@app.on_message(filters.command("start"))
async def start(c, m):
    kb = ReplyKeyboardMarkup([["🚀 Generar Comprobante"]], resize_keyboard=True)
    await m.reply(f"🔥 ¡Qué pasa {m.from_user.first_name}! Sistema listo.", reply_markup=kb)

@app.on_message(filters.regex("🚀 Generar Comprobante"))
async def init(c, m):
    user_data[m.from_user.id] = {}
    await m.reply("📝 Nombre del EMISOR:", reply_markup=ForceReply(selective=True))

@app.on_message(filters.reply & filters.text)
async def steps(c, m):
    uid = m.from_user.id
    if uid not in user_data: return
    d = user_data[uid]
    if 'emisor' not in d:
        d['emisor'] = m.text
        await m.reply("👤 Nombre del RECEPTOR:", reply_markup=ForceReply(selective=True))
    elif 'receptor' not in d:
        d['receptor'] = m.text
        await m.reply("💰 MONTO (ej: 10.00):", reply_markup=ForceReply(selective=True))
    elif 'monto' not in d:
        d['monto'] = m.text
        await m.reply("📅 FECHA:", reply_markup=ForceReply(selective=True))
    elif 'fecha' not in d:
        d['fecha'] = m.text
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("💎 GENERAR", callback_data="gen")]])
        await m.reply("✅ Listo para generar.", reply_markup=btn)

@app.on_callback_query(filters.regex("gen"))
async def fin(c, q):
    uid = q.from_user.id
    await q.message.edit_text("⏳ Generando...")
    path = await capture_receipt(user_data[uid])
    await q.message.reply_photo(path)
    if os.path.exists(path): os.remove(path)
    del user_data[uid]

if __name__ == "__main__":
    # Arrancar la web en un hilo aparte
    Thread(target=run_web).start()
    # Arrancar el bot
    print("Bot encendido...")
    app.run()
