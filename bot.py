import os
import json
from uuid import uuid4
from dotenv import load_dotenv
try:
    from telegram import Update
    from telegram.ext import (
        ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
    )
except ImportError:
    # Alternative import for python-telegram-bot
    from telegram.update import Update
    from telegram.ext import (
        ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
    )
from keep_alive import keep_alive

# ------------------------- LOAD ENV -------------------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID_ENV = os.getenv("ADMIN_CHAT_ID", "").strip()

# Support multiple admin IDs (comma-separated)
ADMIN_CHAT_IDS = []
if ADMIN_CHAT_ID_ENV:
    try:
        ADMIN_CHAT_IDS = [int(id_str.strip()) for id_str in ADMIN_CHAT_ID_ENV.split(",") if id_str.strip()]
        print(f"DEBUG: Loaded admin IDs: {ADMIN_CHAT_IDS}")
    except ValueError as e:
        print(f"ERROR: Invalid ADMIN_CHAT_ID format: {e}")
        ADMIN_CHAT_IDS = []

# ------------------------- DATA PERSISTENCE -------------------------
def load_data():
    """Load ticket data from JSON file"""
    try:
        with open("ticket_data.json", "r") as f:
            data = json.load(f)
            return data.get("ticket_mappings", {}), data.get("user_tickets", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}, {}

def save_data():
    """Save ticket data to JSON file"""
    with open("ticket_data.json", "w") as f:
        json.dump({
            "ticket_mappings": ticket_mappings,
            "user_tickets": user_tickets
        }, f, indent=2)

# Load data on startup
ticket_mappings, user_tickets = load_data()

# ------------------------- HELPERS -------------------------
def new_ticket_id() -> str:
    """Generate a new unique ticket ID"""
    return str(uuid4())[:8].upper()

def pretty_user(user) -> str:
    """Format user information for display"""
    username = f"@{user.username}" if user.username else "(no username)"
    first_name = user.first_name or ""
    last_name = user.last_name or ""
    return f"{first_name} {last_name} {username}".strip()

def is_admin(chat_id: int) -> bool:
    """Check if the given chat ID belongs to an admin"""
    return chat_id in ADMIN_CHAT_IDS

# ------------------------- HANDLERS -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    chat_id = update.effective_chat.id
    
    if is_admin(chat_id):
        await update.message.reply_text(
            "👋 Welcome Admin!\n"
            "You will receive user questions here.\n"
            "Reply to any message to respond to the user.\n\n"
            "Use /debug to check your admin status."
        )
    else:
        await update.message.reply_text(
            "👋 Welcome to Nuner Support!\n"
            "Send your question and our team will reply here.\n"
            "📝 Tip: Send one question per message.\n\n"
            "Use /close to close your current ticket."
        )

async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /debug command - show debug information"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    
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
    await update.message.reply_text(debug_info)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    if is_admin(update.effective_chat.id):
        await update.message.reply_text(
            "ℹ️ Admin Help:\n"
            "• Reply to any user message to respond\n"
            "• /reply <TICKET_ID> <message> - reply to a specific ticket\n"
            "• /close_ticket <TICKET_ID> - close a ticket\n"
            "• /whoami - show your chat ID\n"
            "• /debug - show debug information"
        )
    else:
        await update.message.reply_text(
            "ℹ️ User Help:\n"
            "• Send a message to create a support ticket\n"
            "• /close - close your current ticket\n"
            "• /whoami - show your chat ID"
        )

async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /whoami command - show user's chat ID and admin status"""
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"Your Chat ID: {chat_id}\n"
        f"Admin Status: {'✅ Yes' if is_admin(chat_id) else '❌ No'}"
    )

async def close_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /close command - close user's current ticket"""
    if update.effective_chat.type != "private":
        return
        
    user_id = update.effective_user.id
    ticket_id = user_tickets.get(user_id)
    
    if not ticket_id:
        await update.message.reply_text("You don't have any open tickets.")
        return
        
    # Remove user's ticket
    user_tickets.pop(user_id, None)
    
    # Remove all mappings for this ticket
    global ticket_mappings
    ticket_mappings = {k: v for k, v in ticket_mappings.items() if v[0] != ticket_id}
    
    save_data()
    await update.message.reply_text(f"✅ Ticket #{ticket_id} has been closed.")

async def close_ticket_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /close_ticket command - admin closes a specific ticket"""
    chat_id = update.effective_chat.id
    
    if not is_admin(chat_id):
        await update.message.reply_text("❌ Admin only command.")
        return
        
    if not context.args:
        await update.message.reply_text("Usage: /close_ticket <TICKET_ID>")
        return
        
    ticket_id = context.args[0].upper()
    
    # Find user ID for this ticket
    user_id = None
    for uid, tid in user_tickets.items():
        if tid == ticket_id:
            user_id = uid
            break
            
    if not user_id:
        await update.message.reply_text("Ticket not found.")
        return
        
    # Remove user's ticket
    user_tickets.pop(user_id, None)
    
    # Remove all mappings for this ticket
    global ticket_mappings
    ticket_mappings = {k: v for k, v in ticket_mappings.items() if v[0] != ticket_id}
    
    save_data()
    await update.message.reply_text(f"✅ Ticket #{ticket_id} has been closed.")
    try:
        await context.bot.send_message(chat_id=user_id, text=f"✅ Your ticket #{ticket_id} has been closed by support.")
    except Exception as e:
        print(f"Error notifying user: {e}")

# ------------------------- USER HANDLER -------------------------
async def handle_user_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user questions and create/update tickets"""
    chat_id = update.effective_chat.id
    
    # Prevent admins from creating tickets accidentally
    if is_admin(chat_id):
        await update.message.reply_text(
            "👋 You're an admin! \n"
            "If you want to test user functionality, please use a different account.\n"
            "To reply to users, reply to their messages in the admin chat."
        )
        return
        
    if update.effective_chat.type != "private":
        return

    msg = update.message
    text = (msg.text or "").strip()
    if not text:
        await msg.reply_text("Please send a text question.")
        return

    user_id = msg.from_user.id

    # Check if user already has an open ticket
    ticket_id = user_tickets.get(user_id)
    if not ticket_id:
        ticket_id = new_ticket_id()
        user_tickets[user_id] = ticket_id
        await msg.reply_text(f"✅ Your ticket #{ticket_id} has been created. Admin will reply here.\nUse /close to close this ticket.")
    else:
        await msg.reply_text(f"ℹ️ Your message has been added to ticket #{ticket_id}.")

    # Forward to admin if admin chat is configured
    if ADMIN_CHAT_IDS:
        header = (
            f"🆕 Ticket #{ticket_id}\n"
            f"From: {pretty_user(msg.from_user)} (ID: {user_id})\n\n"
            f"{text}\n\n"
            f"↩️ Reply by replying to this message."
        )
        try:
            for admin_id in ADMIN_CHAT_IDS:
                admin_msg = await context.bot.send_message(chat_id=admin_id, text=header)
                ticket_mappings[admin_msg.message_id] = (ticket_id, user_id)
            save_data()
        except Exception as e:
            await msg.reply_text("Error sending message to admin. Please try again later.")
            print(f"Error sending to admin: {e}")
    else:
        await msg.reply_text("(Admin chat not configured. Set ADMIN_CHAT_ID in .env)")

# ------------------------- ADMIN HANDLERS -------------------------
async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin replies to user tickets"""
    chat_id = update.effective_chat.id
    
    if not is_admin(chat_id):
        return

    msg = update.message
    if not msg or not msg.reply_to_message:
        return

    mapping = ticket_mappings.get(msg.reply_to_message.message_id)
    if not mapping:
        await msg.reply_text("This message is not associated with any ticket.")
        return

    ticket_id, user_id = mapping
    content = msg.text or msg.caption or "(Sent without text)"

    # Send reply to user
    try:
        await context.bot.send_message(chat_id=user_id, text=f"💬 Support (#{ticket_id}):\n{content}")
        
        # Forward admin reply as new message in admin chat and map it
        for admin_id in ADMIN_CHAT_IDS:
            admin_forward = await context.bot.send_message(
                chat_id=admin_id,
                text=f"💬 You replied to #{ticket_id}:\n{content}"
            )
            ticket_mappings[admin_forward.message_id] = (ticket_id, user_id)
        save_data()
    except Exception as e:
        await msg.reply_text(f"Error sending message to user: {e}")

async def reply_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /reply command - admin replies to specific ticket"""
    chat_id = update.effective_chat.id
    
    if not is_admin(chat_id):
        await update.message.reply_text("❌ Admin only command.")
        return

    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text("Usage: /reply <TICKET_ID> <message>")
        return

    ticket_id = args[0].upper()
    message_text = " ".join(args[1:])
    
    # Look for ticket in memory
    user_id = None
    for uid, t_id in user_tickets.items():
        if t_id == ticket_id:
            user_id = uid
            break

    if not user_id:
        await update.message.reply_text("Ticket not found.")
        return

    try:
        await context.bot.send_message(chat_id=user_id, text=f"💬 Support (#{ticket_id}):\n{message_text}")
        await update.message.reply_text("✅ Sent to user.")
        
        # Create a mapping for this reply
        for admin_id in ADMIN_CHAT_IDS:
            admin_msg = await context.bot.send_message(
                chat_id=admin_id,
                text=f"💬 You replied to #{ticket_id}:\n{message_text}"
            )
            ticket_mappings[admin_msg.message_id] = (ticket_id, user_id)
        save_data()
    except Exception as e:
        await update.message.reply_text(f"Error sending message: {e}")

# ------------------------- BOT START -------------------------
def main():
    """Main function to start the bot"""
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN missing. Put it in .env")

    print(f"DEBUG: BOT_TOKEN present: {bool(BOT_TOKEN)}")
    print(f"DEBUG: ADMIN_CHAT_IDS: {ADMIN_CHAT_IDS}")

    # Start the keep-alive server
    keep_alive()

    # Build the application
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(CommandHandler("reply", reply_cmd))
    app.add_handler(CommandHandler("close", close_ticket))
    app.add_handler(CommandHandler("close_ticket", close_ticket_admin))
    app.add_handler(CommandHandler("debug", debug))

    # Register message handlers
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_user_question))
    
    # Add admin message handlers for each admin chat
    for admin_id in ADMIN_CHAT_IDS:
        app.add_handler(MessageHandler(filters.Chat(admin_id) & filters.REPLY & ~filters.COMMAND, handle_admin_reply))

    print("🤖 Nuner Support Bot is running...")
    print("🌐 Keep-alive server is active on port 8000")
    print("📧 Bot is ready to handle support tickets!")
    
    # Start polling for messages
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
