# Telegram Support Bot

## Overview

This is a Telegram support bot designed to handle customer support tickets through a ticketing system. The bot creates a bridge between users and administrators, allowing users to submit support requests that get routed to admin users for handling. The system maintains ticket mappings and user associations through persistent JSON storage, enabling organized support ticket management within Telegram's messaging platform.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Bot Framework
- **Python-telegram-bot Library**: Uses the modern async-based telegram library for handling Telegram API interactions
- **Command and Message Handlers**: Implements both command handlers for specific bot commands and message handlers for general user interactions
- **Event-driven Architecture**: Processes incoming messages and commands through registered handlers

### Data Persistence
- **JSON File Storage**: Simple file-based persistence using `ticket_data.json` for storing ticket mappings and user ticket associations
- **In-memory Caching**: Loads data into memory on startup for fast access during runtime
- **Automatic Save Operations**: Persists changes to disk when ticket data is modified

### Ticket Management System
- **UUID-based Ticket IDs**: Generates unique 8-character uppercase ticket identifiers using UUID4
- **Ticket Mappings**: Maintains relationships between ticket IDs and user chat IDs
- **User Ticket Tracking**: Tracks multiple tickets per user for comprehensive support history

### Authentication & Authorization
- **Admin-based Access Control**: Uses environment variable configuration to define admin chat IDs
- **Multi-admin Support**: Supports comma-separated list of admin IDs for scalable team management
- **Chat ID Validation**: Validates and parses admin IDs with error handling for malformed configurations

### Keep-alive Service
- **Flask Web Server**: Runs a lightweight Flask server on port 8000 for external monitoring
- **Health Check Endpoints**: Provides `/` and `/status` endpoints for service availability monitoring
- **Threading Implementation**: Runs the web server in a daemon thread to avoid blocking the main bot process

### Configuration Management
- **Environment Variables**: Uses python-dotenv for loading configuration from `.env` files
- **Runtime Configuration**: Supports dynamic admin ID parsing and validation during startup
- **Error Handling**: Implements graceful fallbacks for missing or invalid configuration values

## External Dependencies

### Telegram API Integration
- **python-telegram-bot**: Official Telegram Bot API wrapper for Python
- **Telegram Bot Token**: Requires valid bot token from BotFather for API authentication
- **Webhook/Polling Support**: Framework supports both webhook and polling modes for receiving updates

### Python Libraries
- **python-dotenv**: Environment variable loading and management
- **Flask**: Lightweight web framework for keep-alive service
- **UUID**: Built-in Python library for generating unique ticket identifiers
- **JSON**: Built-in Python library for data serialization and persistence
- **Threading**: Built-in Python library for concurrent execution of keep-alive service

### Environment Configuration
- **BOT_TOKEN**: Telegram bot authentication token (required)
- **ADMIN_CHAT_ID**: Comma-separated list of admin chat IDs for support staff access
- **Port 8000**: Fixed port binding for keep-alive service availability checks

### File System Dependencies
- **ticket_data.json**: Local file storage for persistent ticket and user data
- **Read/Write Permissions**: Requires file system access for data persistence operations