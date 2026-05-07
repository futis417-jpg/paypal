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

# --- DATOS DE ISHAK ---
API_ID = 32926930
API_HASH = "07216e34019bc7fbbaa05954131e8bdc"
# IMPORTANTE: Si te sigue saliendo lo del canal A_ToolsX, cambia este token en @BotFather
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

# --- MOTOR DE GENERACIÓN ---
async def capture_receipt(data):
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(args=[
                "--no-sandbox", 
                "--disable-setuid-sandbox", 
                "--disable-dev-shm-usage",
                "--single-process"
            ])
            # Ajustamos escala para mejor calidad en Telegram
            context = await browser.new_context(viewport={'width': 450, 'height': 700}, device_scale_factor=2)
            page = await context.new_page()
            
            tipo_msg = "Ha enviado" if data['tipo'] == "enviado" else "Ha recibido"
            trans_id = 'PAY-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
            
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
            await asyncio.sleep(2) 
            
            filename = f"recibo_{data['uid']}_{int(time.time())}.png"
            await page.screenshot(path=filename)
            await browser.close()
            return filename
        except Exception as e:
            print(f"Error en Playwright: {e}")
            return None

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Helvetica', sans-serif; background-color: #fff; margin: 0; padding: 15px; }}
        .card {{ border: 1px solid #e0e0e0; border-radius: 14px; padding: 30px; max-width: 380px; margin: auto; }}
        .header {{ text-align: center; margin-bottom: 25px; }}
        .header img {{ width: 110px; }}
        .user-greet {{ text-align: center; color: #666; font-size: 14px; margin-bottom: 4px; }}
        .amount {{ text-align: center; font-size: 28px; font-weight: 700; color: #000; margin-bottom: 30px; }}
        .detail-label {{ font-size: 11px; color: #888; font-weight: bold; text-transform: uppercase; margin-bottom: 4px; }}
        .detail-val {{ font-size: 15px; color: #333; margin-bottom: 20px; }}
        .blue-link {{ color: #0070ba; text-decoration: none; border-bottom: 1px solid #0070ba; }}
        .summary-box {{ background: #f5f7fa; padding: 20px; border-radius: 10px; }}
        .flex {{ display: flex; justify-content: space-between; font-size: 14px; margin-bottom: 8px; }}
        .total-line {{ border-top: 1px solid #ccc; padding-top: 10px; font-weight: bold; font-size: 18px; color: #000; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header"><img src="https://www.paypalobjects.com/webstatic/mktg/logo/pp_cc_v3_2x.png"></div>
        <p class="user-greet">Hola, {emisor}</p>
        <h1 class="amount">{tipo_msg} {monto} {moneda} a {receptor}</h1>
        
        <div class="detail-label">Id. de transacción</div>
        <div class="detail-val blue-link">{id_trans}</div>
        
        <div class="detail-label">Fecha de la transacción</div>
        <div class="detail-val">{fecha}</div>

        <div class="summary-box">
            <div class="flex"><span>Importe</span><span>{monto} {moneda}</span></div>
            <div class="flex"><span>Comisión de PayPal</span><span>0,00 {moneda}</span></div>
            <div class="flex total-line"><span>Total</span><span>{monto} {moneda}</span></div>
        </div>
    </div>
</body>
</html>
"""

# --- CONTROLADORES DE MENSAJES ---

@app.on_message(filters.command("start"))
async def start(c, m):
    uid = str(m.from_user.id)
    if uid not in db["users"]:
        db["users"][uid] = {"name": m.from_user.first_name, "expiry": "No activo", "referidos": 0}
        db["stats"]["total_users"] += 1
        save_data(db)

    status = "💎 PREMIUM" if is_premium(uid) else "🆓 GRATIS"
    msg = (f"👋 **¡Hola {m.from_user.first_name}!**\n\n"
           f"Rango: **{status}**\n\n"
           "Genera tus comprobantes oficiales con los botones de abajo.")
    
    kb = ReplyKeyboardMarkup([
        ["⚡ Generar Recibo", "👤 Mi Perfil"],
        ["👥 Referidos", "🛒 Comprar Acceso"]
    ], resize_keyboard=True)
    await m.reply(msg, reply_markup=kb)

@app.on_message(filters.regex("👤 Mi Perfil"))
async def profile(c, m):
    uid = str(m.from_user.id)
    u = db["users"].get(uid, {})
    status = "Premium ✅" if is_premium(uid) else "Gratis ❌"
    await m.reply(f"📋 **TU CUENTA**\n\nID: `{uid}`\nEstado: {status}\nVence: `{u.get('expiry')}`")

@app.on_message(filters.regex("⚡ Generar Recibo"))
async def gen_init(c, m):
    if not is_premium(m.from_user.id):
        return await m.reply("⚠️ Esta función es solo para usuarios **Premium**.")
    
    user_steps[m.from_user.id] = {"uid": m.from_user.id, "step": "tipo"}
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("📤 Enviado", callback_data="set_enviado"),
        InlineKeyboardButton("📥 Recibido", callback_data="set_recibido")
    ]])
    await m.reply("¿Qué tipo de recibo quieres?", reply_markup=kb)

@app.on_callback_query(filters.regex("^set_"))
async def set_t(c, q):
    uid = q.from_user.id
    if uid not in user_steps: return
    user_steps[uid]["tipo"] = q.data.split("_")[1]
    user_steps[uid]["step"] = "emisor"
    await q.message.edit_text("👤 Escribe el nombre del **EMISOR**:")

@app.on_callback_query(filters.regex("^cur_"))
async def set_c(c, q):
    uid = q.from_user.id
    if uid not in user_steps: return
    user_steps[uid]["moneda"] = q.data.split("_")[1]
    user_steps[uid]["step"] = "fecha"
    await q.message.edit_text("📅 Escribe la **FECHA** (ej: 15 de mayo de 2024):")

# --- FUNCIÓN TODO-EN-UNO (ARREGLADA) ---
@app.on_message(filters.text & ~filters.command(["start", "redeem", "admin", "gen"]))
async def handle_workflow(c, m):
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
        await m.reply("💰 Escribe el **MONTO** (ej: 45.00):")
    
    elif step == "monto":
        state["monto"] = m.text.replace(",", ".")
        state["step"] = "moneda"
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("EUR €", callback_data="cur_EUR"),
            InlineKeyboardButton("USD $", callback_data="cur_USD")
        ]])
        await m.reply("💱 Elige la divisa:", reply_markup=kb)
        
    elif step == "fecha":
        state["fecha"] = m.text
        state["step"] = "generating" # Bloqueamos para que no envíe más texto
        
        progreso = await m.reply("⌛ **Procesando datos y generando imagen...**\nEsto tarda unos 10 segundos.")
        
        path = await capture_receipt(state)
        
        if path:
            await progreso.delete()
            await m.reply_photo(path, caption=f"✅ **Recibo generado con éxito.**\nCortesía de @{ (await c.get_me()).username }")
            if os.path.exists(path): os.remove(path)
            db["stats"]["total_gen"] += 1
            save_data(db)
        else:
            await progreso.edit_text("❌ **Error en el servidor.**\nNo se pudo renderizar la imagen. Inténtalo de nuevo más tarde.")
        
        del user_steps[uid] # Limpiamos el estado al terminar

# --- ADMIN ---
@app.on_message(filters.command("gen") & filters.user(ADMIN_ID))
async def admin_gen(c, m):
    try:
        days = int(m.command[1]) if len(m.command) > 1 else 30
        token = "PRO-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        db["tokens"][token] = days
        save_data(db)
        await m.reply(f"🎫 Token generado: `{token}` ({days} días)")
    except: pass

@app.on_message(filters.command("redeem"))
async def redeem(c, m):
    if len(m.command) < 2: return
    tk = m.command[1]
    if tk in db["tokens"]:
        days = db["tokens"].pop(tk)
        uid = str(m.from_user.id)
        db["users"][uid]["expiry"] = get_expiry_date(days)
        save_data(db)
        await m.reply(f"✅ ¡Premium activado por {days} días!")
    else:
        await m.reply("❌ Código inválido.")

# --- WEB SERVER ---
@web_app.route('/')
def home(): return "Bot Online", 200

if __name__ == "__main__":
    Thread(target=lambda: web_app.run(host='0.0.0.0', port=10000), daemon=True).start()
    app.run()
