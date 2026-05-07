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

# --- CONFIGURACIÓN (Tus datos proporcionados) ---
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
        except: pass
    return {"users": {}, "tokens": {}, "stats": {"total_gen": 0, "total_users": 0}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

db = load_data()
user_steps = {} 

# --- LÓGICA DE TIEMPO ---
def get_expiry_date(days):
    return (datetime.now() + timedelta(days=days)).strftime("%d/%m/%Y")

def is_premium(uid):
    uid = str(uid)
    if uid == str(ADMIN_ID): return True
    if uid not in db["users"]: return False
    expiry = db["users"][uid].get("expiry")
    if not expiry or expiry == "No activo": return False
    if expiry == "Vitalicio ♾️": return True
    try:
        return datetime.strptime(expiry, "%d/%m/%Y") > datetime.now()
    except: return False

# --- MOTOR DE GENERACIÓN (Optimizado) ---
async def capture_receipt(data):
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(args=[
                "--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage",
                "--disable-gpu", "--no-zygote", "--single-process"
            ])
            context = await browser.new_context(viewport={'width': 600, 'height': 850}, device_scale_factor=2)
            page = await context.new_page()
            
            tipo_msg = "Ha enviado" if data['tipo'] == "enviado" else "Ha recibido"
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
            await asyncio.sleep(1.5) # Espera renderizado
            
            filename = f"recibo_{data['uid']}_{int(time.time())}.png"
            await page.screenshot(path=filename, full_page=False)
            await browser.close()
            return filename
        except Exception as e:
            print(f"Error Crítico Playwright: {e}")
            return None

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700&display=swap');
        body {{ font-family: 'Open Sans', sans-serif; background-color: #ffffff; margin: 0; padding: 20px; }}
        .paypal-blue {{ color: #003087; }}
        .amount-text {{ font-size: 34px; font-weight: 700; color: #1a1a1a; }}
    </style>
</head>
<body>
    <div class="max-w-md mx-auto border border-gray-100 rounded-xl shadow-lg p-8">
        <div class="flex justify-center mb-8">
            <img src="https://www.paypalobjects.com/webstatic/mktg/logo/pp_cc_v3_2x.png" width="120">
        </div>
        
        <div class="text-center mb-10">
            <p class="text-gray-500 text-sm mb-1">Hola, {emisor}</p>
            <h1 class="amount-text">{tipo_msg} {monto} {moneda}</h1>
            <p class="text-gray-800 font-semibold mt-1">a {receptor}</p>
        </div>

        <div class="space-y-6">
            <div class="border-b pb-2">
                <p class="text-xs font-bold text-gray-500 uppercase">Detalles de la transacción</p>
            </div>
            
            <div class="flex justify-between items-start">
                <div>
                    <p class="text-sm font-bold text-gray-800">Id. de transacción</p>
                    <p class="text-sm paypal-blue underline">{id_trans}</p>
                </div>
                <div class="text-right">
                    <p class="text-sm font-bold text-gray-800">Fecha</p>
                    <p class="text-sm text-gray-600">{fecha}</p>
                </div>
            </div>

            <div class="bg-gray-50 p-4 rounded-lg space-y-3">
                <div class="flex justify-between text-sm">
                    <span class="text-gray-600 font-semibold">Importe</span>
                    <span class="font-bold">{monto} {moneda}</span>
                </div>
                <div class="flex justify-between text-sm">
                    <span class="text-gray-600">Comisión de PayPal</span>
                    <span>0,00 {moneda}</span>
                </div>
                <div class="border-t pt-2 flex justify-between items-center">
                    <span class="text-lg font-extrabold">Total</span>
                    <span class="text-lg font-extrabold">{monto} {moneda}</span>
                </div>
            </div>
        </div>

        <div class="mt-8 text-center">
            <p class="text-[10px] text-gray-400 leading-tight">
                Conserve este recibo como comprobante de su transacción. PayPal no solicita claves ni información sensible por este medio.
            </p>
        </div>
    </div>
</body>
</html>
"""

# --- COMANDOS ---

@app.on_message(filters.command("start"))
async def start(c, m):
    uid = str(m.from_user.id)
    ref_id = m.command[1] if len(m.command) > 1 else None
    
    if uid not in db["users"]:
        db["users"][uid] = {
            "name": m.from_user.first_name,
            "expiry": "No activo",
            "referidos": 0,
            "ref_by": ref_id
        }
        db["stats"]["total_users"] += 1
        if ref_id and ref_id in db["users"]:
            db["users"][ref_id]["referidos"] += 1
            if db["users"][ref_id]["referidos"] % 3 == 0:
                db["users"][ref_id]["expiry"] = get_expiry_date(2) # 2 días de regalo
        save_data(db)

    status = "💎 PREMIUM" if is_premium(uid) else "🆓 GRATIS"
    msg = (f"🔥 **PAYPAL PRO GEN v4.0** 🔥\n\n"
           f"👤 **Usuario:** {m.from_user.first_name}\n"
           f"🆔 **ID:** `{uid}`\n"
           f"⭐ **Rango:** {status}\n\n"
           "Utiliza los botones de abajo para navegar.")
    
    kb = ReplyKeyboardMarkup([
        ["⚡ Generar Recibo", "👤 Mi Perfil"],
        ["🛒 Comprar Acceso", "👥 Referidos"],
        ["📊 Estadísticas"]
    ], resize_keyboard=True)
    await m.reply(msg, reply_markup=kb)

@app.on_message(filters.regex("👤 Mi Perfil"))
async def profile(c, m):
    uid = str(m.from_user.id)
    u = db["users"].get(uid, {})
    status = "Premium 💎" if is_premium(uid) else "Gratis 🆓"
    msg = (f"📋 **TU CUENTA**\n\n"
           f"Nombre: {u.get('name')}\n"
           f"Rango: **{status}**\n"
           f"Vence: `{u.get('expiry', 'No activo')}`\n"
           f"Amigos invitados: `{u.get('referidos', 0)}`")
    await m.reply(msg)

@app.on_message(filters.regex("📊 Estadísticas"))
async def stats(c, m):
    await m.reply(f"📈 **ESTADO DEL SISTEMA**\n\n"
                  f"Usuarios totales: {db['stats']['total_users']}\n"
                  f"Recibos generados: {db['stats']['total_gen']}\n"
                  f"Servidor: **Online ✅**")

@app.on_message(filters.regex("👥 Referidos"))
async def refer(c, m):
    me = await c.get_me()
    link = f"https://t.me/{me.username}?start={m.from_user.id}"
    await m.reply(f"🎁 **GANA PREMIUM GRATIS**\n\n"
                  f"Por cada 3 amigos que se unan con tu link, recibes **2 DÍAS PREMIUM**.\n\n"
                  f"🔗 **Tu enlace único:**\n`{link}`")

@app.on_message(filters.command("redeem"))
async def redeem(c, m):
    if len(m.command) < 2: return await m.reply("❌ Uso: `/redeem PRO-XXXX`")
    tk = m.command[1]
    if tk in db["tokens"]:
        days = db["tokens"].pop(tk)
        uid = str(m.from_user.id)
        db["users"][uid]["expiry"] = get_expiry_date(days)
        save_data(db)
        await m.reply(f"✅ **¡ÉXITO!**\nHas activado {days} días de Premium.")
    else:
        await m.reply("❌ Código inválido o ya usado.")

# --- FLUJO DE GENERACIÓN MEJORADO ---

@app.on_message(filters.regex("⚡ Generar Recibo"))
async def init_gen(c, m):
    if not is_premium(m.from_user.id):
        return await m.reply("⚠️ **FUNCIÓN BLOQUEADA**\n\nDebes ser Premium para generar recibos. Compra un código o invita a 3 amigos.")
    
    user_steps[m.from_user.id] = {"uid": m.from_user.id, "step": "tipo"}
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Pago Enviado", callback_data="t_enviado")],
        [InlineKeyboardButton("📥 Pago Recibido", callback_data="t_recibido")]
    ])
    await m.reply("🚀 **INICIANDO GENERADOR**\n\n¿Qué tipo de recibo necesitas?", reply_markup=kb)

@app.on_callback_query(filters.regex("^t_"))
async def cb_type(c, q):
    uid = q.from_user.id
    if uid not in user_steps: return
    user_steps[uid]["tipo"] = q.data.split("_")[1]
    user_steps[uid]["step"] = "emisor"
    await q.message.edit_text("👤 Escribe el nombre de la persona que **ENVÍA** el dinero:")

@app.on_message(filters.text & ~filters.command(["start", "redeem"]))
async def workflow(c, m):
    uid = m.from_user.id
    if uid not in user_steps: return
    
    step = user_steps[uid]["step"]
    
    if step == "emisor":
        user_steps[uid]["emisor"] = m.text
        user_steps[uid]["step"] = "receptor"
        await m.reply(f"👤 Ahora el nombre de quien **RECIBE** (puedes ser tú o un negocio):")
    
    elif step == "receptor":
        user_steps[uid]["receptor"] = m.text
        user_steps[uid]["step"] = "monto"
        await m.reply(f"💰 Escribe el **MONTO** (ej: 125.50):")
        
    elif step == "monto":
        user_steps[uid]["monto"] = m.text.replace(",", ".")
        user_steps[uid]["step"] = "divisa"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("EUR €", callback_data="cur_EUR"), InlineKeyboardButton("USD $", callback_data="cur_USD")],
            [InlineKeyboardButton("GBP £", callback_data="cur_GBP"), InlineKeyboardButton("MXN $", callback_data="cur_MXN")]
        ])
        await m.reply("💱 Selecciona la moneda:", reply_markup=kb)

@app.on_callback_query(filters.regex("^cur_"))
async def cb_cur(c, q):
    uid = q.from_user.id
    if uid not in user_steps: return
    user_steps[uid]["moneda"] = q.data.split("_")[1]
    user_steps[uid]["step"] = "fecha"
    await q.message.edit_text("📅 Escribe la **FECHA** (ej: 24 de may. de 2024):")

@app.on_message(filters.text & ~filters.command(["start", "redeem"]))
async def final_step(c, m):
    uid = m.from_user.id
    if uid not in user_steps or user_steps[uid].get("step") != "fecha": return
    
    user_steps[uid]["fecha"] = m.text
    wait = await m.reply("⌛ **Generando recibo en alta definición...**\nEsto puede tardar 10-15 segundos.")
    
    path = await capture_receipt(user_steps[uid])
    if path:
        await wait.delete()
        await m.reply_photo(path, caption=f"✅ **RECIBO GENERADO**\n\n🆔 Transacción: `{user_steps[uid].get('id_trans')}`\n🎨 Calidad: 4K Render")
        if os.path.exists(path): os.remove(path)
        db["stats"]["total_gen"] += 1
        save_data(db)
    else:
        await m.reply("❌ **ERROR DE RENDERIZADO**\nEl motor gráfico ha fallado. Reintenta en unos minutos.")
    
    del user_steps[uid]

# --- ADMIN ---
@app.on_message(filters.command("admin") & filters.user(ADMIN_ID))
async def admin_panel(c, m):
    await m.reply(f"🛠 **PANEL DE CONTROL**\n\n"
                  f"1. `/gen_token [dias]` - Crea códigos premium.\n"
                  f"2. `/add_premium [id] [dias]` - Da acceso directo.\n"
                  f"3. `/broadcast [mensaje]` - Envía msg a todos.")

@app.on_message(filters.command("gen_token") & filters.user(ADMIN_ID))
async def adm_gen_tk(c, m):
    days = int(m.command[1]) if len(m.command) > 1 else 30
    tk = "PRO-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    db["tokens"][tk] = days
    save_data(db)
    await m.reply(f"🎫 **Token Generado:** `{tk}`\nValidez: {days} días.")

# --- WEB SERVER ---
@web_app.route('/')
def home(): return "OK", 200

if __name__ == "__main__":
    Thread(target=lambda: web_app.run(host='0.0.0.0', port=10000), daemon=True).start()
    print(">>> BOT PAYPAL PRO INICIADO")
    app.run()
