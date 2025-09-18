# Ethiopian History AI Bot

A sophisticated Telegram bot that delivers daily Ethiopian history facts powered by AI. Built with modern Python technologies and integrated with Groq's LLaMA-3 model for intelligent content generation.

## 🌟 Features

- **AI-Powered Content Generation**: Uses Groq's LLaMA-3 model via LangChain for intelligent history fact generation
- **Telegram Bot Integration**: Seamless user interaction through Telegram's messaging platformcommim
- **Automated Scheduling**: Daily fact delivery at configurable times using APScheduler
- **Subscription Management**: Users can subscribe/unsubscribe from daily facts
- **On-Demand Facts**: Request instant history facts with `/fact` command
- **Production-Ready**: Built with async/await patterns and proper error handling
- **Scalable Architecture**: Clean separation of concerns and modular design

## 🛠️ Tech Stack

- **Python 3.8+**: Core programming language
- **python-telegram-bot**: Telegram Bot API wrapper
- **LangChain**: AI/ML framework for language model integration
- **Groq**: High-performance AI inference platform
- **APScheduler**: Advanced Python scheduler
- **python-dotenv**: Environment variable management
- **asyncio**: Asynchronous programming support

## 📋 Prerequisites

- Python 3.8 or higher
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Groq API Key (from [Groq Console](https://console.groq.com/))

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/ethiopian-history-ai-bot.git
cd ethiopian-history-ai-bot
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file in the project root:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
GROQ_API_KEY=your_groq_api_key_here
DAILY_SEND_TIME=09:00
```

### 5. Run the Bot

```bash
python src/bot.py
```

## 📖 Usage Guide

### Bot Commands

- `/start` - Subscribe to daily Ethiopian history facts
- `/stop` - Unsubscribe from daily facts
- `/fact` - Get an instant history fact
- `/theme` - Manage Weekly Themed History Series (see below)

### Example Interaction

```
User: /start
Bot: Subscribed ✅ You will receive one short Ethiopian history fact daily.

User: /fact
Bot: The Kingdom of Aksum, one of the great powers of the ancient world, was located in what is now northern Ethiopia and Eritrea. It was the first major empire to convert to Christianity in the 4th century AD and controlled trade routes between the Roman Empire and India.
```

### Configuration

The bot can be configured through environment variables:

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token (required)
- `GROQ_API_KEY`: Your Groq API key (required)
- `DAILY_SEND_TIME`: Time for daily fact delivery in HH:MM format (default: 09:00)
- `ENABLE_THEMES`: Enable Weekly Themed Series feature (`true`/`false`, default: false)
- `THEME_ADMIN_IDS`: Optional comma-separated list of admin chat IDs allowed to set weekly theme manually

### Weekly Themed History Series

When `ENABLE_THEMES=true`, users can opt in to receive a 7-day themed mini-series each week.

- Subscribe: `/theme on` or `/theme subscribe`
- Unsubscribe: `/theme off` or `/theme unsubscribe`
- Status: `/theme status`
- Admin set theme: `/theme set Ancient Kingdoms of Ethiopia`

How it works:
- Each week a theme is chosen (random by default, or admin-set).
- Subscribed users receive a themed fact daily (Day 1–7) that builds a narrative.
- A weekly summary is sent every Sunday at 20:00 local time, compiling the week’s facts.

## 🏗️ Project Structure

```
ethiopian-history-ai-bot/
├── src/
│   └── bot.py              # Main bot application
├── subscribers.json         # User subscription data (auto-generated)
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── .gitignore            # Git ignore rules
├── LICENSE               # MIT License
├── CONTRIBUTORS.md       # Contributors list
└── README.md            # This file
```

## 🔧 Development

### Code Style

This project follows PEP 8 guidelines. Code is formatted and linted for consistency.

### Adding Features

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Error Handling

The bot includes comprehensive error handling for:
- Network connectivity issues
- API rate limits
- Invalid user inputs
- Database/file system errors

## 📊 Monitoring

The bot includes structured logging for monitoring:
- Subscription events
- Daily fact generation
- Error tracking
- Performance metrics

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTORS.md](CONTRIBUTORS.md) for guidelines.

### Development Setup

1. Fork the repository
2. Create a virtual environment
3. Install dependencies: `pip install -r requirements.txt`
4. Create a `.env` file with your test credentials
5. Run the bot: `python src/bot.py`

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) for the excellent Telegram API wrapper
- [LangChain](https://github.com/langchain-ai/langchain) for AI/ML framework
- [Groq](https://groq.com/) for high-performance AI inference
- The Ethiopian history community for inspiration

## 📞 Support

For support, please open an issue on GitHub or contact the maintainers.

---

**Note**: This bot is for educational and informational purposes. Please ensure you have proper API keys and follow the terms of service for all integrated services.