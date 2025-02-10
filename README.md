# WhatsApp Expense Tracker Chatbot with Rasa

## Overview
This is a WhatsApp Expense Tracker chatbot built using Rasa that allows users to record and query their expenses efficiently. The bot uses NLP techniques, a database for expense storage, and integrates with Twilio for WhatsApp messaging.

## Features
📌 **Expense Recording**: Users can log their expenses with categories, amounts, and descriptions.  
🏷 **Category Classification**: Uses NLP (Zero-shot learning & NER) to categorize expenses.  
🔍 **Expense Querying**: Retrieve expenses based on date, category, or both.  
📊 **Insights & Summaries**: Provides a breakdown of expenses by category.  
💾 **SQLite Database**: Persistent storage for expense records.  
📡 **Twilio Integration**: Send and receive messages via WhatsApp.  

## Technologies Used
- **Rasa**: NLP-powered chatbot framework  
- **Twilio API**: WhatsApp messaging  
- **SQLite**: Lightweight database  
- **Transformers (Hugging Face)**: Zero-shot classification & NER  
- **Python**: Core backend logic  
- **Logging**: Debugging and monitoring  

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/your-repo/whatsapp-expense-tracker.git
cd whatsapp-expense-tracker
```

### 2. Install Dependencies
Create a virtual environment and install required Python packages.
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Set Up Twilio Account
- Sign up at [Twilio](https://www.twilio.com/)
- Get your **Account SID**, **Auth Token**, and **WhatsApp Number**
- Update `credentials.yml` with Twilio credentials

### 4. Train the Rasa Model
```bash
rasa train
```

### 5. Start Rasa Server & Actions Server
In separate terminals, run:
```bash
rasa run --enable-api
rasa run actions
```

## Usage

### 📩 Adding an Expense
Send a message like:
```plaintext
I spent $20 on Starbucks coffee yesterday.
```
💾 The bot extracts amount, category, and date automatically.

### 🔎 Querying Expenses
Ask questions like:
```plaintext
How much did I spend on coffee this week?
Show me my expenses for yesterday.
```
📊 The bot fetches relevant data from the database.

## Database Schema (`expenses.db`)

| ID | Description       | Amount | Category | Date       | Timestamp          |
|----|-----------------|--------|----------|------------|--------------------|
| 1  | Starbucks coffee | 20.0   | Coffee   | 2024-02-09 | 2024-02-09 10:30:00 |
| 2  | Uber ride       | 15.5   | Travel   | 2024-02-08 | 2024-02-08 15:00:00 |

## Enhancements & Future Scope
📌 **Dashboard for visualization**  
📉 **Expense trend analysis**  
🗣 **Voice-based interaction support**  
🏦 **Bank statement auto-categorization**  

## Contributors
👨‍💻 Your Name - [GitHub](https://github.com/ranjeetkulkarni)

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
