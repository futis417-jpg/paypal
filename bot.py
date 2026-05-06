import os
import asyncio
import random
import string
import json
import time
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from playwright.async_api import async_playwright
from flask import Flask
from threading import Thread

# --- CONFIGURACIÓN ---
# Asegúrate de que estos datos son correctos
API_ID = 32926930
API_HASH = "07216e34019bc7fbbaa05954131e8bdc"
BOT_TOKEN = "8588595625:AAF8YS-7MGjfX74jCMgsz9w_U1ZZ6SHKvnk"
ADMIN_ID = 8398522835 

app = Client("paypal_pro_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
web_app = Flask(__name__)

# --- PERSISTENCIA ---
DATA_FILE = "database.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"users": {}, "tokens": {}, "stats": {"total_gen": 0}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

db = load_data()
user_steps = {} # Estado temporal de generación

# --- LÓGICA DE TIEMPO ---
def get_expiry_date(days):
    if days == -1: return "Vitalicio ♾️"
    return (datetime.now() + timedelta(days=days)).strftime("%d/%m/%Y")

def is_premium(uid):
    uid = str(uid)
    if uid == str(ADMIN_ID): return True # Admin es premium siempre
    if uid not in db["users"]: return False
    expiry = db["users"][uid].get("expiry")
    if not expiry or expiry == "No activo": return False
    if expiry == "Vitalicio ♾️": return True
    try:
        return datetime.strptime(expiry, "%d/%m/%Y") > datetime.now()
    except:
        return False

# --- NAVEGADOR (Optimizado para Render) ---
async def capture_receipt(data):
    async with async_playwright() as p:
        try:
            # Lanzamos navegador con argumentos para ahorrar RAM
            browser = await p.chromium.launch(args=[
                "--no-sandbox", 
                "--disable-setuid-sandbox", 
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-zygote",
                "--single-process"
            ])
            context = await browser.new_context(viewport={'width': 700, 'height': 900})
            page = await context.new_page()
            
            tipo_msg = "Ha enviado" if data['tipo'] == "enviado" else "Ha recibido"
            
            # El ID de transacción se queda fijo en el objeto data para evitar cambios
            trans_id = data.get('trans_id', 'PAY-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=12)))
            
            content = HTML_TEMPLATE.format(
                emisor=data['emisor'], 
                receptor=data['receptor'],
                monto=data['monto'], 
                fecha=data['fecha'], 
                moneda=data['moneda'],
                tipo_msg=tipo_msg,
                id_trans=trans_id
            )
            
            await page.set_content(content)
            await asyncio.sleep(2) # Tiempo para renderizar estilos
            
            filename = f"recibo_{data['uid']}.png"
            await page.screenshot(path=filename, full_page=True)
            await browser.close()
            return filename
        except Exception as e:
            print(f"Error en Playwright: {e}")
            return None

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700;800&display=swap');
        body {{ font-family: 'Open Sans', sans-serif; background-color: #f7f9fc; padding: 0; margin: 0; }}
        .card {{ background: white; padding: 45px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); width: 580px; margin: 20px auto; }}
        .blue-text {{ color: #0070ba; }}
    </style>
</head>
<body>
    <div class="receipt-container p-10">
        <p style="text-align: center; color: #6c7378; font-size: 15px; margin-bottom: 25px;">Hola, {emisor}</p>
        <div class="card">
            <div style="text-align: center; margin-bottom: 35px;">
                <img src="https://www.paypalobjects.com/webstatic/mktg/logo/pp_cc_v3_2x.png" width="120" style="display: inline-block;">
            </div>
            
            <h1 style="font-size: 32px; font-weight: 700; text-align: center; color: #000; margin-bottom: 40px; letter-spacing: -0.5px;">
                {tipo_msg} {monto} {moneda} a {receptor}
            </h1>

            <div style="font-size: 19px; font-weight: 700; margin-bottom: 25px; border-bottom: 1px solid #eee; padding-bottom: 10px;">Detalles de la transacción</div>
            
            <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
                <div>
                    <div style="font-weight: 700; font-size: 14px; color: #2c2e2f;">Id. de transacción</div>
                    <div class="blue-text" style="font-size: 14px; text-decoration: underline;">{id_trans}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-weight: 700; font-size: 14px; color: #2c2e2f;">Fecha de la transacción</div>
                    <div style="font-size: 14px;">{fecha}</div>
                </div>
            </div>

            <div style="background: #fbfbfb; padding: 20px; border-radius: 8px; margin-top: 30px;">
                <div style="display: flex; justify-content: space-between; font-size: 16px; margin-bottom: 10px;">
                    <span style="font-weight: 600;">Importe</span>
                    <span>{monto} {moneda}</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 14px; color: #666;">
                    <span>Comisión de PayPal</span>
                    <span>0,00 {moneda}</span>
                </div>
                <hr style="border: 0; border-top: 1px solid #ddd; margin: 15px 0;">
                <div style="display: flex; justify-content: space-between; font-weight: 800; font-size: 20px; color: #000;">
                    <span>Total</span>
                    <span>{monto} {moneda}</span>
                </div>
            </div>

            <div style="margin-top: 30px; font-size: 13px; color: #888; text-align: center;">
                Este es un recibo oficial de su pago mediante el saldo de su cuenta PayPal.
            </div>
        </div>
    </div>
</body>
</html>
"""

# --- COMANDOS ---

@app.on_message(filters.command("start"))
async def start(c, m):
    uid = str(m.from_user.id)
    referido_por = m.command[1] if len(m.command) > 1 else None
    
    if uid not in db["users"]:
        db["users"][uid] = {
            "name": m.from_user.first_name,
            "expiry": "No activo",
            "referidos": 0,
            "invitado_por": referido_por
        }
        if referido_por and referido_por in db["users"]:
            db["users"][referido_por]["referidos"] += 1
            if db["users"][referido_por]["referidos"] % 3 == 0:
                # Damos 1 día si tiene 3 referidos
                db["users"][referido_por]["expiry"] = get_expiry_date(1)
        save_data(db)

    status = "💎 PREMIUM" if is_premium(uid) else "🆓 GRATIS"
    msg = (f"🚀 **Bienvenido al Generador Pro de PayPal**\n\n"
           f"👤 **Usuario:** {m.from_user.first_name}\n"
           f"⭐ **Rango:** {status}\n\n"
           "Genera comprobantes realistas para tus negocios.")
    
    kb = ReplyKeyboardMarkup([
        ["⚡ Generar Recibo", "👤 Mi Perfil"],
        ["🛒 Comprar Premium", "👥 Referidos"]
    ], resize_keyboard=True)
    await m.reply(msg, reply_markup=kb)

@app.on_message(filters.regex("👤 Mi Perfil"))
async def profile(c, m):
    uid = str(m.from_user.id)
    u = db["users"].get(uid, {})
    expiry = u.get("expiry") or "No activo"
    msg = (f"📋 **TU PERFIL**\n\n"
           f"ID: `{uid}`\n"
           f"Premium hasta: `{expiry}`\n"
           f"Referidos totales: `{u.get('referidos', 0)}`")
    await m.reply(msg)

@app.on_message(filters.regex("👥 Referidos"))
async def refer(c, m):
    me = await c.get_me()
    link = f"https://t.me/{me.username}?start={m.from_user.id}"
    await m.reply(f"🎁 **SISTEMA DE REFERIDOS**\n\n"
                  f"Por cada 3 amigos que invites, recibes **1 DÍA PREMIUM GRATIS**.\n\n"
                  f"🔗 **Tu enlace:** `{link}`")

@app.on_message(filters.command("redeem"))
async def redeem(c, m):
    if len(m.command) < 2: return await m.reply("❌ Uso: `/redeem TOKEN`")
    token = m.command[1]
    if token in db["tokens"]:
        days = db["tokens"].pop(token)
        uid = str(m.from_user.id)
        db["users"][uid]["expiry"] = get_expiry_date(days)
        save_data(db)
        await m.reply(f"✅ ¡Activado! Tienes {days} días de Premium.")
    else:
        await m.reply("❌ Token inválido.")

# --- FLUJO GENERACIÓN (Corregido y Unificado) ---

@app.on_message(filters.regex("⚡ Generar Recibo"))
async def init_gen(c, m):
    uid = m.from_user.id
    if not is_premium(uid):
        return await m.reply("⚠️ Esta función es **Premium**.\n\nUsa `/redeem` o invita 3 amigos para activarla.")
    
    user_steps[uid] = {"uid": uid, "step": "tipo", "trans_id": 'PAY-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))}
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Enviado", callback_data="t_enviado"), 
         InlineKeyboardButton("📥 Recibido", callback_data="t_recibido")]
    ])
    await m.reply("Selecciona el tipo de recibo:", reply_markup=kb)

@app.on_callback_query(filters.regex("^t_"))
async def set_type(c, q):
    uid = q.from_user.id
    if uid not in user_steps: return
    user_steps[uid]["tipo"] = q.data.split("_")[1]
    user_steps[uid]["step"] = "emisor"
    await q.message.edit_text("✍️ Escribe el nombre del **EMISOR**:", reply_markup=ForceReply(selective=True))

@app.on_callback_query(filters.regex("^c_"))
async def set_currency(c, q):
    uid = q.from_user.id
    if uid not in user_steps: return
    user_steps[uid]["moneda"] = q.data.split("_")[1]
    user_steps[uid]["step"] = "fecha"
    await q.message.edit_text("📅 **FECHA** (ej: 12 may 2024):", reply_markup=ForceReply(selective=True))

# HANDLER UNIFICADO PARA REPLIES
@app.on_message(filters.reply & filters.text)
async def handle_all_steps(c, m):
    uid = m.from_user.id
    if uid not in user_steps: return
    
    state = user_steps[uid]
    current_step = state.get("step")

    if current_step == "emisor":
        state["emisor"] = m.text
        state["step"] = "receptor"
        await m.reply("👤 Escribe el nombre del **RECEPTOR**:", reply_markup=ForceReply(selective=True))
    
    elif current_step == "receptor":
        state["receptor"] = m.text
        state["step"] = "monto"
        await m.reply("💰 **MONTO** (ej: 150.00):", reply_markup=ForceReply(selective=True))
    
    elif current_step == "monto":
        state["monto"] = m.text.replace(',', '.')
        state["step"] = "moneda"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("€ EUR", callback_data="c_EUR"), 
             InlineKeyboardButton("$ USD", callback_data="c_USD"),
             InlineKeyboardButton("£ GBP", callback_data="c_GBP")]
        ])
        await m.reply("💱 Selecciona la divisa:", reply_markup=kb)
        
    elif current_step == "fecha":
        state["fecha"] = m.text
        state["step"] = "generating"
        msg_wait = await m.reply("⏳ Generando imagen de alta calidad... Por favor espera.")
        
        path = await capture_receipt(state)
        if path:
            await m.reply_photo(path, caption="✅ **Comprobante Generado con Éxito**\nHecho con @PayProBot")
            if os.path.exists(path): os.remove(path)
            db["stats"]["total_gen"] += 1
            save_data(db)
        else:
            await m.reply("❌ Error al generar la imagen. Inténtalo de nuevo.")
        
        del user_steps[uid] # Limpiamos estado final

# --- ADMIN COMMANDS ---
@app.on_message(filters.command("gen_token") & filters.user(ADMIN_ID))
async def gen_token_cmd(c, m):
    try:
        days = int(m.command[1]) if len(m.command) > 1 else 30
        token = "PRO-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        db["tokens"][token] = days
        save_data(db)
        await m.reply(f"🎫 **Token de {days} días generado:** `{token}`")
    except:
        await m.reply("❌ Error. Uso: `/gen_token 30`")

# --- WEB SERVER PARA RENDER ---
@web_app.route('/')
def home(): return "Bot Online", 200

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    # Arrancamos Flask en un hilo separado
    Thread(target=run_web, daemon=True).start()
    print("Bot activo y servidor web iniciado...")
    app.run()
