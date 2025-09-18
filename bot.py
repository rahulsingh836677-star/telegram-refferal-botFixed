import os
import time
from telebot import TeleBot, types
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = TeleBot(BOT_TOKEN)

# In-memory storage
users = {}
referrals = {}
payouts_total = 0
total_users = 0

def get_user(uid):
    if uid not in users:
        users[uid] = {
            "balance": 0,
            "wallet": None,
            "referral_id": None,
            "last_bonus": 0,
            "status": "active",
            "refer_status": False
        }
    return users[uid]

def is_admin(uid):
    return uid == ADMIN_ID

def format_currency(val):
    return f"{val:.2f}"

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    args = message.text.split()
    ref_id = int(args[1]) if len(args) > 1 else None
    user = get_user(uid)
    global total_users
    total_users += 1
    bot.send_message(
        uid,
        f"👋 Welcome {message.from_user.first_name}!\n"
        "✅ You have started the bot.\n"
        f"👥 Your referral link: https://t.me/{bot.get_me().username}?start={uid}"
    )

@bot.message_handler(commands=['mainmenu'])
def main_menu(message):
    uid = message.from_user.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("💰 Balance","🫂 Invite")
    markup.row("🗂 Wallet","🎁 Bonus")
    markup.row("📤 Withdraw","📊 Statistics")
    bot.send_message(uid,"🏡 Main Menu",reply_markup=markup)

@bot.message_handler(func=lambda m: m.text=="💰 Balance")
def balance(message):
    uid = message.from_user.id
    user = get_user(uid)
    bot.send_message(
        uid,
        f"🙌🏻 User: {message.from_user.first_name}\n"
        f"💰 Balance: {format_currency(user['balance'])} Points\n"
        "🪢 Invite To Earn More"
    )

@bot.message_handler(func=lambda m: m.text=="🎁 Bonus")
def bonus(message):
    uid = message.from_user.id
    user = get_user(uid)
    now = time.time()
    if now - user["last_bonus"] < 86400:
        bot.send_message(uid,"⛔ You Already Received Bonus in Last 24 Hours")
        return
    user["last_bonus"] = now
    user["balance"] += 4
    bot.send_message(uid,"🎁 Congrats, You Received 4 INR!\nCheck Back After 24 Hours!")

@bot.message_handler(func=lambda m: m.text=="📤 Withdraw")
def withdraw(message):
    uid = message.from_user.id
    user = get_user(uid)
    min_with = 10
    max_with = 15
    if not user["wallet"]:
        bot.send_message(uid,"🗂 You Need To Setup Your Wallet First")
        return
    if user["balance"] < min_with:
        bot.send_message(uid,f"⚠ Must Own Atleast {min_with} Points To Withdraw")
        return
    msg = bot.send_message(uid,f"📤 Enter Amount to Withdraw (Min: {min_with}, Max: {max_with})")
    bot.register_next_step_handler(msg, process_withdraw)

def process_withdraw(message):
    uid = message.from_user.id
    user = get_user(uid)
    try:
        amount = float(message.text)
    except:
        bot.send_message(uid,"❌ Invalid value. Enter only numeric value")
        return
    if amount < 10 or amount > 15:
        bot.send_message(uid,"❌ Withdraw amount must be between 10 and 15")
        return
    if amount > user["balance"]:
        bot.send_message(uid,"❌ Balance Not Enough")
        return
    user["balance"] -= amount
    global payouts_total
    payouts_total += amount
    bot.send_message(
        uid,
        f"✅ Withdrawal Requested Successfully\n"
        f"💰 Amount: {amount}\n"
        f"💼 Wallet: {user['wallet']}"
    )

@bot.message_handler(func=lambda m: m.text=="🗂 Wallet")
def wallet(message):
    uid = message.from_user.id
    user = get_user(uid)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💠 Configure Wallet 💠", callback_data="set_wallet"))
    bot.send_message(uid,f"💡 Your Currently Set Upi ID: {user['wallet'] or '⛔ Not Set'}",reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data=="set_wallet")
def set_wallet_callback(call):
    uid = call.from_user.id
    msg = bot.send_message(uid,"✏️ Now Send Your Upi ID To Use It For Future Withdrawals")
    bot.register_next_step_handler(msg, save_wallet)

def save_wallet(message):
    uid = message.from_user.id
    user = get_user(uid)
    user["wallet"] = message.text
    bot.send_message(uid,f"👉🏻 Wallet Set: {message.text}")

@bot.message_handler(func=lambda m: m.text=="📊 Statistics")
def stats(message):
    uid = message.from_user.id
    bot.send_message(
        uid,
        f"📊 Bot Live Stats 📊\n\n"
        f"📤 Total Payouts: {format_currency(payouts_total)} Points\n"
        f"💡 Total Users: {total_users} User(s)"
    )

@bot.message_handler(func=lambda m: m.text=="🫂 Invite")
def invite(message):
    uid = message.from_user.id
    user = get_user(uid)
    user_refs = referrals.get(uid, [])
    inv_link = f"https://t.me/{bot.get_me().username}?start={uid}"
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("🔍 My Refers", callback_data="my_refers"),
        types.InlineKeyboardButton("🔥 Top List", callback_data="top_list")
    )
    bot.send_message(
        uid,
        f"🙌🏻 Total Refers = {len(user_refs)} User(s)\n"
        f"🙌🏻 Your Invite Link = {inv_link}\n"
        "🪢 Invite to Earn 1 Point Per Invite",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda c: c.data=="my_refers")
def my_refers(call):
    uid = call.from_user.id
    user_refs = referrals.get(uid, [])
    if not user_refs:
        bot.send_message(uid,"No any affiliated users")
        return
    msg = f"➡️ Your Total Refers: {len(user_refs)}\n\n👥 Your Refer Users:\n"
    for u in user_refs:
        msg += f"👤 User ID: {u}\n"
    bot.send_message(uid,msg)

@bot.callback_query_handler(func=lambda c: c.data=="top_list")
def top_list(call):
    uid = call.from_user.id
    leaderboard = sorted(users.items(), key=lambda x: len(referrals.get(x[0], [])), reverse=True)
    msg = "🏆 Top Referral Leaderboard\n\n"
    for i, (u_id, u_data) in enumerate(leaderboard[:10], 1):
        msg += f"{i}. User ID: {u_id} ➡️ {len(referrals.get(u_id, []))} refers\n"
    bot.send_message(uid,msg)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    uid = message.from_user.id
    if uid != ADMIN_ID:
        bot.send_message(uid,"❌ You are not admin")
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Add Balance","Set Balance")
    markup.row("Ban User","Unban User")
    markup.row("Broadcast","Gift Code")
    bot.send_message(uid,"🛠 Admin Panel",reply_markup=markup)

bot.infinity_polling()
