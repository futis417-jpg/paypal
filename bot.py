import os
import asyncio
import random
import string
from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from playwright.async_api import async_playwright

# --- CONFIGURACIÓN TOTAL DIRECTA ---
API_ID = 32926930
API_HASH = "07216e34019bc7fbbaa05954131e8bdc"
BOT_TOKEN = "8588595625:AAF8YS-7MGjfX74jCMgsz9w_U1ZZ6SHKvnk"

app = Client("paypal_pro_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Diccionario para gestionar los pasos de cada usuario
user_data = {}

def gen_id():
    """Genera un ID de transacción realista estilo PayPal."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=17)) + 'F'

# Plantilla HTML Pro con Tailwind CSS
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@300;400;600;700;800&display=swap');
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
                <span>Saldo de PayPal (EUR)</span>
                <span>{monto} € EUR</span>
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
    """Renderiza el HTML y toma una captura de pantalla."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox", "--disable-setuid-sandbox"])
        page = await browser.new_page()
        content = HTML_TEMPLATE.format(
            emisor=data['emisor'],
            receptor=data['receptor'],
            monto=data['monto'],
            fecha=data['fecha'],
            id_trans=gen_id()
        )
        await page.set_content(content)
        await asyncio.sleep(1.5) # Espera para cargar fuentes/estilos
        path = f"recibo_{gen_id()}.png"
        await page.screenshot(path=path, full_page=True, scale="device")
        await browser.close()
        return path

# --- LÓGICA DEL BOT ---

@app.on_message(filters.command("start"))
async def start(client, message):
    keyboard = ReplyKeyboardMarkup([
        ["🚀 Generar Comprobante"],
        ["ℹ️ Info", "⚙️ Soporte"]
    ], resize_keyboard=True)
    await message.reply(
        f"👋 ¡Qué pasa **{message.from_user.first_name}**!\n\nListo para crear comprobantes realistas. Dale al botón de abajo.",
        reply_markup=keyboard
    )

@app.on_message(filters.regex("🚀 Generar Comprobante"))
async def init_gen(client, message):
    user_data[message.from_user.id] = {}
    await message.reply(
        "📝 **PASO 1:**\nEscribe el **Nombre o Correo del EMISOR**:",
        reply_markup=ForceReply(selective=True)
    )

@app.on_message(filters.reply & filters.text)
async def process_steps(client, message):
    uid = message.from_user.id
    if uid not in user_data: return
    
    step_data = user_data[uid]
    text = message.text

    if 'emisor' not in step_data:
        step_data['emisor'] = text
        await message.reply("👤 **PASO 2:**\nEscribe el **Nombre o Correo del RECEPTOR**:", reply_markup=ForceReply(selective=True))
    elif 'receptor' not in step_data:
        step_data['receptor'] = text
        await message.reply("💰 **PASO 3:**\nIntroduce el **MONTO** (ej: `10.00`):", reply_markup=ForceReply(selective=True))
    elif 'monto' not in step_data:
        step_data['monto'] = text
        await message.reply("📅 **PASO 4:**\nIntroduce la **FECHA** (ej: `2 de mayo de 2026`):", reply_markup=ForceReply(selective=True))
    elif 'fecha' not in step_data:
        step_data['fecha'] = text
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("💎 GENERAR IMAGEN", callback_data="final_gen")]])
        await message.reply("🔥 Todo listo. Dale a generar para crear la imagen realista.", reply_markup=btn)

@app.on_callback_query(filters.regex("final_gen"))
async def finalize(client, callback_query):
    uid = callback_query.from_user.id
    if uid in user_data:
        await callback_query.message.edit_text("⌛ Renderizando captura realista...")
        try:
            path = await capture_receipt(user_data[uid])
            await callback_query.message.reply_photo(path, caption="✅ Comprobante generado con éxito.")
            if os.path.exists(path): os.remove(path)
            del user_data[uid]
            await callback_query.message.delete()
        except Exception as e:
            await callback_query.message.edit_text(f"❌ Error: {e}")

print("Bot encendido...")
app.run()
