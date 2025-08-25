from flask import Flask
from threading import Thread

# Create Flask app for keep-alive functionality
app = Flask('')

@app.route('/')
def home():
    """Health check endpoint to keep the bot alive"""
    return "Telegram Support Bot is alive and running!"

@app.route('/status')
def status():
    """Status endpoint for monitoring"""
    return {
        "status": "online",
        "service": "Telegram Support Bot",
        "message": "Bot is running and ready to handle support tickets"
    }

def run():
    """Run the Flask server"""
    # Bind to 0.0.0.0 and port 8000 as per requirements
    app.run(host='0.0.0.0', port=8000, debug=False)

def keep_alive():
    """Start the keep-alive server in a separate thread"""
    t = Thread(target=run)
    t.daemon = True  # Dies when main thread dies
    t.start()
    print("Keep-alive server started on port 8000")
