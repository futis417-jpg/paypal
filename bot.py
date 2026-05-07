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

# --- DATOS DE ISHAK (Sant Hilari Power) ---
API_ID = 32926930
API_HASH = "07216e34019bc7fbbaa05954131e8bdc"
BOT_TOKEN = "8588595625:AAF8YS-7MGjfX74jCMgsz9w_U1ZZ6SHKvnk"
ADMIN_ID = 8398522835 

app = Client("paypal_pro_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
web_app = Flask(__name__)

# --- PERSISTENCIA DE DATOS ---
DATA_FILE = "database.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except: pass
    return {"users": {}, "tokens": {}, "stats": {"total_gen": 0, "total_users": 0}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

db = load_data()
user_steps = {}

# --- SISTEMA PREMIUM ---
def get_expiry_date(days):
    return (datetime.now() + timedelta(days=days)).strftime("%d/%m/%Y")

def is_premium(uid):
    uid = str(uid)
    if uid == str(ADMIN_ID): return True
    if uid not in db["users"]: return False
    expiry = db["users"][uid].get("expiry")
    if not expiry or expiry == "No activo": return False
    try:
        return datetime.strptime(expiry, "%d/%m/%Y") > datetime.now()
    except: return False

# --- GENERADOR DE IMÁGENES (FIXED) ---
async def capture_receipt(data):
    async with async_playwright() as p:
        try:
            # Argumentos críticos para que funcione en Render sin errores de memoria
            browser = await p.chromium.launch(args=[
                "--no-sandbox", 
                "--disable-setuid-sandbox", 
                "--disable-dev-shm-usage",
                "--single-process"
            ])
            context = await browser.new_context(viewport={'width': 500, 'height': 750}, device_scale_factor=2)
            page = await context.new_page()
            
            tipo_msg = "Ha enviado" if data['tipo'] == "enviado" else "Ha recibido"
            trans_id = 'PAY-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
            
            # Plantilla HTML inyectada directamente para evitar archivos externos
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
            await asyncio.sleep(2) # Tiempo para que carguen los estilos
            
            filename = f"recibo_{data['uid']}.png"
            await page.screenshot(path=filename)
            await browser.close()
            return filename
        except Exception as e:
            print(f"Error en el motor gráfico: {e}")
            return None

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: sans-serif; background-color: #fff; margin: 0; padding: 20px; }}
        .container {{ border: 1px solid #eee; border-radius: 12px; padding: 30px; max-width: 400px; margin: auto; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }}
        .logo {{ text-align: center; margin-bottom: 20px; }}
        .logo img {{ width: 100px; }}
        .greeting {{ text-align: center; color: #666; font-size: 14px; margin-bottom: 5px; }}
        .main-text {{ text-align: center; font-size: 24px; font-weight: bold; margin-bottom: 25px; color: #1a1a1a; }}
        .details {{ border-top: 1px solid #eee; padding-top: 15px; }}
        .row {{ margin-bottom: 15px; }}
        .label {{ font-size: 11px; color: #888; font-weight: bold; text-transform: uppercase; }}
        .val {{ font-size: 14px; color: #333; }}
        .blue {{ color: #0070ba; text-decoration: underline; }}
        .box {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 15px; }}
        .flex {{ display: flex; justify-content: space-between; font-size: 14px; margin-bottom: 5px; }}
        .total {{ border-top: 1px solid #ddd; padding-top: 8px; font-weight: bold; font-size: 16px; margin-top: 8px; }}
        .footer {{ text-align: center; font-size: 10px; color: #ccc; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="logo"><img src="https://www.paypalobjects.com/webstatic/mktg/logo/pp_cc_v3_2x.png"></div>
        <p class="greeting">Hola, {emisor}</p>
        <h1 class="main-text">{tipo_msg} {monto} {moneda} a {receptor}</h1>
        <div class="details">
            <div class="row">
                <div class="label">ID. DE TRANSACCIÓN</div>
                <div class="val blue">{id_trans}</div>
            </div>
            <div class="row">
                <div class="label">FECHA</div>
                <div class="val">{fecha}</div>
            </div>
        </div>
        <div class="box">
            <div class="flex"><span>Importe</span><span>{monto} {moneda}</span></div>
            <div class="flex"><span>Comisión</span><span>0,00 {moneda}</span></div>
            <div class="flex total"><span>Total</span><span>{monto} {moneda}</span></div>
        </div>
        <div class="footer">Recibo oficial generado por PayPal.</div>
    </div>
</body>
</html>
"""

# --- CONTROLADORES ---

@app.on_message(filters.command("start"))
async def start(c, m):
    uid = str(m.from_user.id)
    if uid not in db["users"]:
        db["users"][uid] = {"name": m.from_user.first_name, "expiry": "No activo", "referidos": 0}
        db["stats"]["total_users"] += 1
        save_data(db)

    status = "💎 PREMIUM" if is_premium(uid) else "🆓 GRATIS"
    msg = (f"👋 **¡Hola {m.from_user.first_name}!**\n\n"
           f"Bienvenido al Generador de Recibos Profesional.\n"
           f"Tu estado actual: **{status}**\n\n"
           "Usa el menú de abajo para empezar.")
    
    kb = ReplyKeyboardMarkup([
        ["⚡ Generar Recibo", "👤 Perfil"],
        ["👥 Referidos", "🛒 Comprar"]
    ], resize_keyboard=True)
    await m.reply(msg, reply_markup=kb)

@app.on_message(filters.regex("👤 Perfil"))
async def profile(c, m):
    uid = str(m.from_user.id)
    u = db["users"].get(uid, {})
    status = "Premium ✅" if is_premium(uid) else "Gratis ❌"
    await m.reply(f"📋 **TU CUENTA**\n\nID: `{uid}`\nEstado: {status}\nVence: `{u.get('expiry')}`\nInvitados: {u.get('referidos')}")

@app.on_message(filters.regex("👥 Referidos"))
async def refs(c, m):
    me = await c.get_me()
    link = f"https://t.me/{me.username}?start={m.from_user.id}"
    await m.reply(f"🎁 **¡PREMIUM GRATIS!**\n\nInvita a 3 amigos con tu link y obtén **2 días gratis**.\n\n`{link}`")

# --- FLUJO DE GENERACIÓN ---

@app.on_message(filters.regex("⚡ Generar Recibo"))
async def gen_init(c, m):
    if not is_premium(m.from_user.id):
        return await m.reply("⚠️ Debes ser **Premium** para usar esta función.")
    
    user_steps[m.from_user.id] = {"uid": m.from_user.id, "step": "tipo"}
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("📤 Enviado", callback_data="set_enviado"),
        InlineKeyboardButton("📥 Recibido", callback_data="set_recibido")
    ]])
    await m.reply("¿Qué tipo de pago quieres simular?", reply_markup=kb)

@app.on_callback_query(filters.regex("^set_"))
async def set_t(c, q):
    uid = q.from_user.id
    if uid not in user_steps: return
    user_steps[uid]["tipo"] = q.data.split("_")[1]
    user_steps[uid]["step"] = "emisor"
    await q.message.edit_text("👤 Escribe el nombre del **EMISOR**:")

@app.on_message(filters.text & ~filters.command(["start", "redeem"]))
async def catch_all(c, m):
    uid = m.from_user.id
    if uid not in user_steps: return
    
    state = user_steps[uid]
    step = state["step"]

    if step == "emisor":
        state["emisor"] = m.text
        state["step"] = "receptor"
        await m.reply("👤 Escribe el nombre del **RECEPTOR**:")
    elif step == "receptor":
        state["receptor"] = m.text
        state["step"] = "monto"
        await m.reply("💰 Escribe el **MONTO** (ej: 15.00):")
    elif step == "monto":
        state["monto"] = m.text.replace(",", ".")
        state["step"] = "moneda"
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("EUR €", callback_data="cur_EUR"),
            InlineKeyboardButton("USD $", callback_data="cur_USD")
        ]])
        await m.reply("💱 Elige la moneda:", reply_markup=kb)

@app.on_callback_query(filters.regex("^cur_"))
async def set_c(c, q):
    uid = q.from_user.id
    if uid not in user_steps: return
    user_steps[uid]["moneda"] = q.data.split("_")[1]
    user_steps[uid]["step"] = "fecha"
    await q.message.edit_text("📅 Escribe la **FECHA** (ej: 12 de mayo de 2024):")

@app.on_message(filters.text & ~filters.command(["start", "redeem"]))
async def final_step(c, m):
    uid = m.from_user.id
    if uid not in user_steps or user_steps[uid].get("step") != "fecha": return
    
    user_steps[uid]["fecha"] = m.text
    wait = await m.reply("🎨 **Generando imagen...**")
    
    path = await capture_receipt(user_steps[uid])
    if path:
        await m.reply_photo(path, caption="✅ **¡Aquí tienes tu recibo!**")
        if os.path.exists(path): os.remove(path)
    else:
        await m.reply("❌ Error al renderizar. Inténtalo de nuevo.")
    
    del user_steps[uid]

# --- ADMIN ---
@app.on_message(filters.command("gen") & filters.user(ADMIN_ID))
async def admin_gen(c, m):
    days = int(m.command[1]) if len(m.command) > 1 else 30
    token = "PRO-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    db["tokens"][token] = days
    save_data(db)
    await m.reply(f"🎫 Token de {days} días: `{token}`")

@app.on_message(filters.command("redeem"))
async def redeem(c, m):
    if len(m.command) < 2: return
    tk = m.command[1]
    if tk in db["tokens"]:
        days = db["tokens"].pop(tk)
        db["users"][str(m.from_user.id)]["expiry"] = get_expiry_date(days)
        save_data(db)
        await m.reply(f"✅ ¡Activado {days} días!")
    else:
        await m.reply("❌ Token no válido.")

# --- WEB ---
@web_app.route('/')
def home(): return "Bot Activo", 200

if __name__ == "__main__":
    Thread(target=lambda: web_app.run(host='0.0.0.0', port=10000), daemon=True).start()
    app.run()
