import os
import asyncio
import random
import string
import re
from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from playwright.async_api import async_playwright
from flask import Flask
from threading import Thread

# --- CONFIGURACIÓN ---
# Usa variables de entorno en Render para que no te roben el token si el repo es público
API_ID = 32926930
API_HASH = "07216e34019bc7fbbaa05954131e8bdc"
BOT_TOKEN = "8588595625:AAF8YS-7MGjfX74jCMgsz9w_U1ZZ6SHKvnk"
ADMIN_ID = 8398522835 # ¡CAMBIA ESTO por tu ID de Telegram para generar códigos!

app = Client("paypal_pro_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
web_app = Flask(__name__)

# --- MEMORIA VOLÁTIL (Se borra si el bot se reinicia) ---
user_data = {}
premium_users = set()
valid_tokens = set() # Aquí guardaremos los códigos que puedes vender

# --- BROWSER GLOBAL (Para ahorrar RAM en Render) ---
browser_instance = None
playwright_instance = None

async def get_browser():
    global browser_instance, playwright_instance
    if not playwright_instance:
        playwright_instance = await async_playwright().start()
    if not browser_instance:
        browser_instance = await playwright_instance.chromium.launch(
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--single-process"]
        )
    return browser_instance

# --- LOGICA DE GENERACIÓN ---
def gen_id():
    return 'PAY-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700;800&display=swap');
        body {{ font-family: 'Open Sans', sans-serif; background-color: #f7f9fc; margin: 0; padding: 0; }}
        .receipt-container {{ width: 100%; max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
        .card {{ background: white; padding: 50px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
        .blue-text {{ color: #0070ba; }}
    </style>
</head>
<body>
    <div class="receipt-container">
        <p style="text-align: center; color: #6c7378; font-size: 14px; margin-bottom: 30px;">Hola, {emisor}</p>
        <div class="card">
            <div style="text-align: center; margin-bottom: 30px;">
                <img src="https://www.paypalobjects.com/paypal-ui/logos/svg/paypal-mark-color.svg" width="45" style="display: inline-block;">
            </div>
            
            <h1 style="font-size: 36px; font-weight: 800; text-align: center; color: #000; line-height: 1.1; margin-bottom: 40px;">
                Ha enviado {monto} € EUR a {receptor}
            </h1>

            <div style="font-size: 18px; font-weight: 700; margin-bottom: 20px;">Detalles de la transacción</div>
            
            <div style="display: flex; justify-content: space-between; margin-bottom: 25px;">
                <div>
                    <div style="font-weight: 700; font-size: 14px;">Id. de transacción</div>
                    <div class="blue-text" style="font-size: 14px; text-decoration: underline;">{id_trans}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-weight: 700; font-size: 14px;">Fecha de la transacción</div>
                    <div style="font-size: 14px;">{fecha}</div>
                </div>
            </div>

            <hr style="border: 0; border-top: 1px solid #eee; margin: 25px 0;">

            <div style="display: flex; justify-content: space-between; font-size: 15px; margin-bottom: 12px;">
                <span style="font-weight: 700;">Importe enviado</span>
                <span>{monto} € EUR</span>
            </div>

            <div style="margin: 20px 0 10px 0; font-size: 14px; color: #666;">Pagado con:</div>
            <div style="display: flex; justify-content: space-between; font-size: 15px;">
                <span>Saldo de PayPal</span>
                <span>{monto} € EUR</span>
            </div>

            <hr style="border: 0; border-top: 2px solid #000; margin: 25px 0;">

            <div style="display: flex; justify-content: space-between; font-weight: 800; font-size: 18px; color: #000;">
                <span>Total</span>
                <span>{monto} € EUR</span>
            </div>
        </div>
        <div style="text-align: center; margin-top: 40px;">
             <img src="https://www.paypalobjects.com/paypal-ui/logos/svg/paypal-mark-color.svg" width="30" style="opacity: 0.5;">
        </div>
    </div>
</body>
</html>
"""

async def capture_receipt(data):
    try:
        browser = await get_browser()
        context = await browser.new_context(viewport={'width': 650, 'height': 850})
        page = await context.new_page()
        
        content = HTML_TEMPLATE.format(
            emisor=data['emisor'], 
            receptor=data['receptor'],
            monto=data['monto'], 
            fecha=data['fecha'], 
            id_trans=gen_id()
        )
        
        await page.set_content(content)
        await asyncio.sleep(1) # Tiempo para renderizar fuentes
        
        filename = f"recibo_{random.randint(1000,9999)}.png"
        await page.screenshot(path=filename, full_page=True)
        await context.close()
        return filename
    except Exception as e:
        print(f"Error en captura: {e}")
        return None

# --- COMANDOS DEL BOT ---

@app.on_message(filters.command("start"))
async def start(c, m):
    msg = (f"👋 ¡Hola {m.from_user.first_name}!\n\n"
           "Este bot genera comprobantes de PayPal realistas.\n\n"
           "💎 **Estado:** " + ("Premium ✅" if m.from_user.id in premium_users else "Gratis ❌") + "\n"
           "Usa /redeem [código] para activar el modo VIP.")
    
    kb = ReplyKeyboardMarkup([["🚀 Generar Comprobante"]], resize_keyboard=True)
    await m.reply(msg, reply_markup=kb)

# --- SISTEMA DE MONETIZACIÓN (VENTA DE CÓDIGOS) ---

@app.on_message(filters.command("gen_token") & filters.user(ADMIN_ID))
async def gen_token(c, m):
    new_token = "ISHAK-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    valid_tokens.add(new_token)
    await m.reply(f"🎫 **Nuevo Token Generado:** `{new_token}`\n\nVéndelo y dile al usuario que use `/redeem {new_token}`")

@app.on_message(filters.command("redeem"))
async def redeem(c, m):
    if len(m.command) < 2:
        return await m.reply("❌ Uso: `/redeem CODI-GO`")
    
    token = m.command[1]
    if token in valid_tokens:
        valid_tokens.remove(token)
        premium_users.add(m.from_user.id)
        await m.reply("💎 ¡Felicidades! Ahora eres **USUARIO PREMIUM**. Ya puedes generar recibos ilimitados.")
    else:
        await m.reply("❌ Código inválido o ya usado.")

# --- FLUJO DE GENERACIÓN ---

@app.on_message(filters.regex("🚀 Generar Comprobante"))
async def init(c, m):
    # Lógica de limitación gratuita (opcional)
    if m.from_user.id not in premium_users:
        return await m.reply("⚠️ Debes ser **Premium** para usar esta función.\nContacta al admin para comprar un código.")
        
    user_data[m.from_user.id] = {}
    await m.reply("📝 Nombre del **EMISOR** (quien envía):", reply_markup=ForceReply(selective=True))

@app.on_message(filters.reply & filters.text)
async def steps(c, m):
    uid = m.from_user.id
    if uid not in user_data: return
    
    d = user_data[uid]
    
    if 'emisor' not in d:
        d['emisor'] = m.text
        await m.reply("👤 Nombre del **RECEPTOR** (quien recibe):", reply_markup=ForceReply(selective=True))
    elif 'receptor' not in d:
        d['receptor'] = m.text
        await m.reply("💰 **MONTO** (ej: 50,00):", reply_markup=ForceReply(selective=True))
    elif 'monto' not in d:
        # Validar un poco el monto
        monto = m.text.replace('.', ',')
        d['monto'] = monto
        await m.reply("📅 **FECHA** (ej: 24 abr 2024):", reply_markup=ForceReply(selective=True))
    elif 'fecha' not in d:
        d['fecha'] = m.text
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("💎 GENERAR AHORA", callback_data="gen")]])
        await m.reply("✅ Datos listos. Pulsa el botón para crear la imagen.", reply_markup=btn)

@app.on_callback_query(filters.regex("gen"))
async def fin(c, q):
    uid = q.from_user.id
    if uid not in user_data: return
    
    await q.message.edit_text("⏳ Generando recibo en alta calidad... espera un momento.")
    
    path = await capture_receipt(user_data[uid])
    
    if path:
        await q.message.reply_photo(path, caption="✅ **Aquí tienes tu recibo profesional.**\nGenerado por el Bot de Ishak.")
        if os.path.exists(path): os.remove(path)
    else:
        await q.message.edit_text("❌ Error al generar. Inténtalo de nuevo.")
    
    del user_data[uid]

# --- WEB SERVER PARA RENDER ---
@web_app.route('/')
def home(): return "Ishak's Bot is Running!", 200

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    print("Bot encendido y listo...")
    app.run()
