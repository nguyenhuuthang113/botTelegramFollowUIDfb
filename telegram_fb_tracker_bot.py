import json
import os
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import asyncio

DATA_FILE = "fb_watch_list.json"
CHECK_INTERVAL = 600  # 10 phút

# Tải dữ liệu UID
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []

# Lưu dữ liệu UID
def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# Kiểm tra trạng thái UID
def check_facebook_uid(uid):
    url = f"https://www.facebook.com/{uid}"
    try:
        r = requests.get(url, timeout=10)
        if "Bạn hiện không xem được nội dung này" in r.text:
            return False
        return True
    except:
        return False

# /add lệnh
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Dùng: /add <uid> <ghi chú>")
        return
    uid = context.args[0]
    note = " ".join(context.args[1:]) if len(context.args) > 1 else ""
    data = load_data()
    if any(u["uid"] == uid for u in data):
        await update.message.reply_text(f"UID {uid} đã có trong danh sách.")
        return
    data.append({
        "uid": uid,
        "note": note,
        "active": None,
        "last_checked": None
    })
    save_data(data)
    await update.message.reply_text(f"Đã thêm UID {uid} vào danh sách.")

# /list lệnh
async def list_uids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    if not data:
        await update.message.reply_text("Chưa có UID nào trong danh sách.")
        return
    msg = "\n\n".join([
        f"UID: {u['uid']}\nGhi chú: {u['note']}\nTrạng thái: {'✅ Hoạt động' if u['active'] else '❌ Không hoạt động' if u['active'] == False else '⏳ Chưa kiểm tra'}"
        for u in data
    ])
    await update.message.reply_text(msg)

# /remove lệnh
async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Dùng: /remove <uid>")
        return
    uid = context.args[0]
    data = load_data()
    new_data = [u for u in data if u["uid"] != uid]
    save_data(new_data)
    await update.message.reply_text(f"Đã xóa UID {uid} khỏi danh sách.")

# Tự động kiểm tra
async def check_all_uids(application):
    while True:
        data = load_data()
        updated = False
        for user in data:
            old_status = user["active"]
            new_status = check_facebook_uid(user["uid"])
            if old_status != new_status:
                user["active"] = new_status
                user["last_checked"] = datetime.now().isoformat()
                updated = True
                chat_id = application.bot_data.get("chat_id")
                if chat_id:
                    msg = f"📢 UID: {user['uid']} ({user['note']})\n"
                    msg += f"➡️ {'Đã hoạt động trở lại ✅' if new_status else 'Đã ngừng hoạt động ❌'}\n"
                    msg += f"https://www.facebook.com/{user['uid']}"
                    await application.bot.send_message(chat_id=chat_id, text=msg)
        if updated:
            save_data(data)
        await asyncio.sleep(CHECK_INTERVAL)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.application.bot_data["chat_id"] = update.effective_chat.id
    await update.message.reply_text("🔍 Bot đã sẵn sàng theo dõi UID Facebook.")

# Main bot
def main():
    TOKEN = "7773938869:AAE4ewCX3zhFSESunz6CHo5J3xSxn7wzt1Q"
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("list", list_uids))
    app.add_handler(CommandHandler("remove", remove))

    app.create_task(check_all_uids(app))
    print("Bot đang chạy...")
    app.run_polling()

if __name__ == "__main__":
    main()
