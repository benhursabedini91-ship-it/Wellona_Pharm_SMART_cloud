# WPH_AI Monitoring System - Setup Guide

## 📋 Overview
Real-time system monitoring with Telegram alerts for:
- CPU, Memory, Disk usage
- Database connection status
- Critical path availability
- Automated alerts for issues

---

## 🚀 Quick Setup

### **Step 1: Install Dependencies**
```powershell
cd C:\Wellona\wphAI
pip install -r app/requirements.txt
```

### **Step 2: Create Telegram Bot** (Optional but recommended)

1. **Open Telegram** and search for `@BotFather`

2. **Create new bot:**
   ```
   /newbot
   ```
   - Choose a name (e.g., "WPH AI Monitor")
   - Choose a username (e.g., "wph_ai_alerts_bot")

3. **Copy the bot token** (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

4. **Start chat with your bot** (search for your bot username and click START)

5. **Get your Chat ID:**
   - Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   - Look for `"chat":{"id":123456789,...}`
   - Copy the chat ID number

6. **Add to `.env` file:**
   ```bash
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   TELEGRAM_CHAT_ID=123456789
   ```

### **Step 3: Test Telegram Connection**