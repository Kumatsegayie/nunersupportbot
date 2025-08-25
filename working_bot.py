from keep_alive import keep_alive
keep_alive()

import os
import json
import telebot
from uuid import uuid4
from dotenv import load_dotenv

# Load environment
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID_ENV = os.getenv("ADMIN_CHAT_ID", "").strip()

print(f"Bot token present: {bool(BOT_TOKEN)}")
print(f"Admin chat ID: {ADMIN_CHAT_ID_ENV}")

if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN is missing!")
    exit(1)

# Parse admin IDs
ADMIN_CHAT_IDS = []
if ADMIN_CHAT_ID_ENV:
    try:
        ADMIN_CHAT_IDS = [int(id_str.strip()) for id_str in ADMIN_CHAT_ID_ENV.split(",") if id_str.strip()]
        print(f"Loaded admin IDs: {ADMIN_CHAT_IDS}")
    except ValueError as e:
        print(f"ERROR: Invalid ADMIN_CHAT_ID format: {e}")

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# Data storage
ticket_mappings = {}
user_tickets = {}

def load_data():
    global ticket_mappings, user_tickets
    try:
        with open("ticket_data.json", "r") as f:
            data = json.load(f)
            ticket_mappings = data.get("ticket_mappings", {})
            user_tickets = data.get("user_tickets", {})
        print("✓ Data loaded from file")
    except (FileNotFoundError, json.JSONDecodeError):
        ticket_mappings = {}
        user_tickets = {}
        print("✓ Starting with empty data")

def save_data():
    with open("ticket_data.json", "w") as f:
        json.dump({
            "ticket_mappings": ticket_mappings,
            "user_tickets": user_tickets
        }, f, indent=2)

def new_ticket_id():
    return str(uuid4())[:8].upper()

def pretty_user(user):
    username = f"@{user.username}" if user.username else "(no username)"
    first_name = user.first_name or ""
    last_name = user.last_name or ""
    return f"{first_name} {last_name} {username}".strip()

def is_admin(chat_id):
    return chat_id in ADMIN_CHAT_IDS

# Bot command handlers
@bot.message_handler(commands=['start'])
def handle_start(message):
    chat_id = message.chat.id
    
    if is_admin(chat_id):
        bot.reply_to(message,
            "👋 Welcome Admin!\n"
            "You will receive user questions here.\n"
            "Reply to any message to respond to the user.\n\n"
            "Use /debug to check your admin status."
        )
    else:
        bot.reply_to(message,
            "👋 Welcome to Nuner Support!\n"
            "Send your question and our team will reply here.\n"
            "📝 Tip: Send one question per message.\n\n"
            "Use /close to close your current ticket."
        )

@bot.message_handler(commands=['debug'])
def handle_debug(message):
    chat_id = message.chat.id
    user = message.from_user
    
    debug_info = (
        f"🛠 DEBUG INFO:\n"
        f"• Your Chat ID: {chat_id}\n"
        f"• Your User ID: {user.id}\n"
        f"• Username: @{user.username if user.username else 'N/A'}\n"
        f"• Name: {user.first_name or ''} {user.last_name or ''}\n"
        f"• ADMIN_CHAT_IDS: {ADMIN_CHAT_IDS}\n"
        f"• Is Admin: {is_admin(chat_id)}\n"
        f"• Bot Token Present: {bool(BOT_TOKEN)}\n"
        f"• Admin IDs Configured: {bool(ADMIN_CHAT_IDS)}"
    )
    
    print(f"DEBUG: {debug_info}")
    bot.reply_to(message, debug_info)

@bot.message_handler(commands=['close'])
def handle_close(message):
    if message.chat.type != "private":
        return
        
    user_id = message.from_user.id
    ticket_id = user_tickets.get(user_id)
    
    if not ticket_id:
        bot.reply_to(message, "You don't have any open tickets.")
        return
        
    # Remove user's ticket
    user_tickets.pop(user_id, None)
    
    # Remove all mappings for this ticket
    global ticket_mappings
    ticket_mappings = {k: v for k, v in ticket_mappings.items() if v[0] != ticket_id}
    
    save_data()
    bot.reply_to(message, f"✅ Ticket #{ticket_id} has been closed.")

# Handle regular messages
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        text = message.text or ""
        
        print(f"Received message from {user_id} in chat {chat_id}: {text}")
        
        # Handle admin replies
        if is_admin(chat_id) and message.reply_to_message:
            reply_msg_id = message.reply_to_message.message_id
            mapping = ticket_mappings.get(reply_msg_id)
            
            if mapping:
                ticket_id, target_user_id = mapping
                content = text
                
                try:
                    # Send reply to user
                    bot.send_message(target_user_id, f"💬 Support (#{ticket_id}):\n{content}")
                    
                    # Forward admin reply to admin chat and map it
                    for admin_id in ADMIN_CHAT_IDS:
                        admin_forward = bot.send_message(admin_id, f"💬 You replied to #{ticket_id}:\n{content}")
                        ticket_mappings[admin_forward.message_id] = (ticket_id, target_user_id)
                    
                    save_data()
                    print(f"Admin {user_id} replied to ticket {ticket_id}")
                except Exception as e:
                    bot.reply_to(message, f"Error sending message to user: {e}")
                    print(f"Error in admin reply: {e}")
                return
        
        # Handle user messages (create/update tickets)
        if message.chat.type == "private" and not is_admin(chat_id):
            # Check if user has existing ticket
            ticket_id = user_tickets.get(user_id)
            if not ticket_id:
                ticket_id = new_ticket_id()
                user_tickets[user_id] = ticket_id
                bot.reply_to(message, f"✅ Your ticket #{ticket_id} has been created. Admin will reply here.\nUse /close to close this ticket.")
            else:
                bot.reply_to(message, f"ℹ️ Your message has been added to ticket #{ticket_id}.")
            
            # Forward to admin
            if ADMIN_CHAT_IDS:
                header = (
                    f"🆕 Ticket #{ticket_id}\n"
                    f"From: {pretty_user(message.from_user)} (ID: {user_id})\n\n"
                    f"{text}\n\n"
                    f"↩️ Reply by replying to this message."
                )
                try:
                    for admin_id in ADMIN_CHAT_IDS:
                        admin_msg = bot.send_message(admin_id, header)
                        ticket_mappings[admin_msg.message_id] = (ticket_id, user_id)
                    save_data()
                    print(f"Created/updated ticket {ticket_id} for user {user_id}")
                except Exception as e:
                    bot.reply_to(message, "Error sending message to admin. Please try again later.")
                    print(f"Error forwarding to admin: {e}")
        
        # Handle admin messages that aren't replies
        elif is_admin(chat_id):
            bot.reply_to(message,
                "👋 You're an admin! \n"
                "If you want to test user functionality, please use a different account.\n"
                "To reply to users, reply to their messages in the admin chat."
            )
            
    except Exception as e:
        print(f"Error in handle_message: {e}")

def main():
    print("Starting Nuner Support Bot...")
    
    # Load existing data
    load_data()
    
    print("🤖 Nuner Support Bot is running...")
    print("🌐 Keep-alive server is active on port 8000")
    print("📧 Bot is ready to handle support tickets!")
    print("Bot username: @nunersupportbot")
    
    try:
        # Start the bot
        print("Starting bot polling...")
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"Error running bot: {e}")
        # Keep process alive for Flask server
        import time
        print("Keeping process alive for Flask server...")
        while True:
            time.sleep(60)

if __name__ == "__main__":
    main()