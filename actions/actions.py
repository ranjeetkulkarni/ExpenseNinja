from typing import Any, Dict, List, Text
import sqlite3
import datetime
import re
import logging

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from transformers import pipeline

# Configure logging.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# 1. Extensive Candidate Labels
# ============================================================================

CANDIDATE_LABELS = [
    "food",
    "coffee",
    "online_food",
    "groceries",
    "dining",
    "snacks",
    "alcohol",
    "travel",
    "lodging",
    "transportation",
    "shopping",
    "clothing",
    "electronics",
    "furniture",
    "entertainment",
    "utilities",
    "health",
    "insurance",
    "education",
    "books",
    "personal_care",
    "rent",
    "fuel",
    "maintenance",
    "subscriptions",
    "investments",
    "charity",
    "pet_care",
    "office_supplies",
    "communication",
    "fitness",
    "beauty",
    "stationery",
    "miscellaneous",
    "others"
]

# Mapping from candidate label to emoji for enhanced UI.
CATEGORY_EMOJI = {
    "food": "🍽️",
    "coffee": "☕️",
    "online_food": "🍔",
    "groceries": "🛒",
    "dining": "🍴",
    "snacks": "🍟",
    "alcohol": "🍺",
    "travel": "✈️",
    "lodging": "🏨",
    "transportation": "🚖",
    "shopping": "🛍️",
    "clothing": "👗",
    "electronics": "📱",
    "furniture": "🛋️",
    "entertainment": "🎬",
    "utilities": "💡",
    "health": "🏥",
    "insurance": "🛡️",
    "education": "📚",
    "books": "📖",
    "personal_care": "💅",
    "rent": "🏠",
    "fuel": "⛽️",
    "maintenance": "🔧",
    "subscriptions": "🔔",
    "investments": "💹",
    "charity": "❤️",
    "pet_care": "🐾",
    "office_supplies": "🖊️",
    "communication": "📞",
    "fitness": "🏋️",
    "beauty": "💄",
    "stationery": "✏️",
    "miscellaneous": "🗃️",
    "others": "❓"
}

# ============================================================================
# 2. Initialize Models
# ============================================================================

# Zero-shot classification pipeline as fallback.
try:
    zero_shot_classifier = pipeline(
        "zero-shot-classification",
        model="valhalla/distilbart-mnli-12-1"
    )
    logger.info("Zero-shot classifier loaded with model valhalla/distilbart-mnli-12-1.")
except Exception as e:
    logger.error("Error loading zero-shot classifier: %s", e)
    zero_shot_classifier = None

# NER pipeline for token-based mapping.
try:
    ner_recognizer = pipeline(
        "ner",
        model="dslim/bert-base-NER",
        grouped_entities=True
    )
    logger.info("NER pipeline loaded with model dslim/bert-base-NER.")
except Exception as e:
    logger.error("Error loading NER pipeline: %s", e)
    ner_recognizer = None

# ============================================================================
# 3. Database Setup
# ============================================================================

DB_PATH = 'expenses.db'

def initialize_db() -> None:
    """
    Initialize the SQLite database with an 'expenses' table.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    description TEXT,
                    amount REAL,
                    category TEXT,
                    date TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error("Error initializing database: %s", e)

initialize_db()

# ============================================================================
# 4. Determining Expense Categories
# ============================================================================

def determine_categories(text: str) -> List[str]:
    """
    Classify an expense description into one or more categories using:
      (a) Keyword Overrides,
      (b) A mapping dictionary (NER-based & manual scanning),
      (c) Zero-shot classification fallback.

    This function supports multi-label assignment by accumulating evidence.
    
    Args:
        text: The expense description provided by the user.
    
    Returns:
        A sorted list of candidate category labels.
    """
    text_lower = text.lower()
    labels = set()

    # -- Special Keyword Overrides --
    # E.g., "chai" without "coffee" → food.
    if "chai" in text_lower and "coffee" not in text_lower:
        logger.info("Keyword override: 'chai' detected without 'coffee'.")
        labels.add("food")

    # Dining keywords (if no coffee terms, assign 'dining' and 'food').
    dining_keywords = ["dinner", "lunch", "breakfast", "restaurant"]
    coffee_terms = ["coffee", "cappuccino", "filter coffee", "cold coffee"]
    if any(word in text_lower for word in dining_keywords) and not any(word in text_lower for word in coffee_terms):
        logger.info("Keyword override: dining keywords detected; categorizing as dining and food.")
        labels.add("dining")
        labels.add("food")

    # If explicit coffee terms exist, add both "coffee" and "food".
    if any(word in text_lower for word in coffee_terms):
        logger.info("Keyword override: coffee-related terms detected; categorizing as coffee and food.")
        labels.add("coffee")
        labels.add("food")

    # -- Extensive Mapping Dictionary --
    # Map common tokens to candidate labels.
    MAPPING = {
        "starbucks": ["coffee", "food"],
        "cappuccino": ["coffee", "food"],
        "filter coffee": ["coffee", "food"],
        "cold coffee": ["coffee", "food"],
        "chai": ["food"],
        "dinner": ["dining", "food"],
        "lunch": ["dining", "food"],
        "restaurant": ["dining", "food"],
        "snack": ["snacks", "food"],
        "alcohol": ["alcohol", "food"],
        "swiggy": ["online_food", "food"],
        "blinkit": ["online_food", "food"],
        "uber": ["travel", "transportation"],
        "ola": ["travel", "transportation"],
        "taxi": ["travel", "transportation"],
        "train": ["travel", "transportation"],
        "flight": ["travel", "transportation"],
        "hotel": ["lodging", "travel"],
        "airbnb": ["lodging", "travel"],
        "bigbasket": ["groceries"],
        "zepto": ["groceries"],
        "amazon": ["shopping"],
        "ebay": ["shopping"],
        "netflix": ["entertainment", "subscriptions"],
        "disney": ["entertainment", "subscriptions"],
        "prime": ["entertainment", "subscriptions"],
        "electricity": ["utilities"],
        "water": ["utilities"],
        "gas bill": ["utilities"],
        "internet": ["utilities", "communication"],
        "doctor": ["health"],
        "pharmacy": ["health"],
        "medicine": ["health"],
        "tuition": ["education"],
        "school": ["education"],
        "college": ["education"],
        "course": ["education"],
        "book": ["books"],
        "novel": ["books"],
        "magazine": ["books"],
        "salon": ["personal_care"],
        "spa": ["personal_care"],
        "rent": ["rent"],
        "apartment": ["rent"],
        "fuel": ["fuel"],
        "petrol": ["fuel"],
        "diesel": ["fuel"],
        "repair": ["maintenance"],
        "service": ["maintenance"],
        "subscription": ["subscriptions"],
        "investment": ["investments"],
        "stock": ["investments"],
        "bond": ["investments"],
        "donation": ["charity"],
        "zakat": ["charity"],
        "pet": ["pet_care"],
        "veterinary": ["pet_care"],
        "office": ["office_supplies"],
        "stationery": ["stationery"],
        "clothes": ["clothing", "shopping"],
        "fashion": ["clothing", "shopping"],
        "gadget": ["electronics", "shopping"],
        "furniture": ["furniture", "shopping"],
        "beauty": ["beauty", "personal_care"],
        "gym": ["fitness"],
        "workout": ["fitness"],
        "misc": ["miscellaneous"]
    }

    # First, check the mapping dictionary.
    for key, mapped_labels in MAPPING.items():
        if key in text_lower:
            logger.info("Mapping match: '%s' found; adding %s.", key, mapped_labels)
            labels.update(mapped_labels)

    # -- NER-based Enhancement (if available) --
    if ner_recognizer:
        try:
            entities = ner_recognizer(text)
            for entity in entities:
                token = entity.get("word", "").lower()
                for key, mapped_labels in MAPPING.items():
                    if key in token:
                        logger.info("NER mapping: token '%s' triggers %s.", token, mapped_labels)
                        labels.update(mapped_labels)
        except Exception as e:
            logger.error("NER processing error: %s", e)

    # -- Fallback via Zero-shot Classification --
    if not labels and zero_shot_classifier:
        try:
            result = zero_shot_classifier(text, candidate_labels=CANDIDATE_LABELS)
            top_label = result["labels"][0]
            logger.info("Zero-shot classification fallback returned: '%s'.", top_label)
            labels.add(top_label)
        except Exception as e:
            logger.error("Zero-shot classification error: %s", e)

    if not labels:
        labels.add("others")

    return sorted(labels)

# ============================================================================
# 5. Rasa Action: Adding an Expense
# ============================================================================

class ActionAddExpense(Action):
    def name(self) -> Text:
        return "action_add_expense"

    def run(self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        logger.info("Executing ActionAddExpense.")
        message = tracker.latest_message.get('text', '')
        amount = None

        # Attempt to extract the expense amount from Rasa entities.
        for entity in tracker.latest_message.get('entities', []):
            if entity.get('entity') == 'amount':
                try:
                    amount = float(entity.get('value'))
                    logger.info("Amount extracted from entity: %s", amount)
                    break
                except Exception as e:
                    logger.error("Error parsing amount from entity: %s", e)

        # Fallback: use regex to extract a numeric value.
        if amount is None:
            match = re.search(r"[₹$]?(\d+(?:\.\d{1,2})?)", message)
            if match:
                try:
                    amount = float(match.group(1))
                    logger.info("Amount extracted via regex: %s", amount)
                except Exception as e:
                    logger.error("Regex conversion error: %s", e)

        if amount is None:
            dispatcher.utter_message(text="❗ I couldn't detect an expense amount. Please include one in your message.")
            return []

        # Determine the date (if "yesterday" is mentioned, use that date).
        if "yesterday" in message.lower():
            expense_date = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        else:
            expense_date = datetime.date.today().isoformat()

        # Determine categories for the expense.
        categories = determine_categories(message)
        category_str = ", ".join(categories)

        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO expenses (description, amount, category, date) VALUES (?, ?, ?, ?)",
                    (message, amount, category_str, expense_date)
                )
                conn.commit()
                logger.info("Expense recorded: '%s' | Amount: %s | Categories: %s | Date: %s",
                            message, amount, category_str, expense_date)
        except Exception as e:
            dispatcher.utter_message(text="❗ There was an error recording your expense.")
            logger.error("Database insertion error: %s", e)
            return []

        dispatcher.utter_message(text="✅ *Expense Recorded Successfully!*")
        return []

# ============================================================================
# 6. Rasa Action: Querying Expenses
# ============================================================================

class ActionQueryExpense(Action):
    def name(self) -> Text:
        return "action_query_expense"

    def run(self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        query_text = tracker.latest_message.get('text', '').lower()
        filter_category = None
        filter_date = None

        # Apply a date filter if "yesterday" is mentioned.
        if "yesterday" in query_text:
            filter_date = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
            logger.info("Applying date filter for query: %s", filter_date)

        # Determine category filter based on keywords in the query.
        if any(word in query_text for word in ["coffee"]):
            filter_category = "coffee"
        elif any(word in query_text for word in ["online", "swiggy", "blinkit"]):
            filter_category = "online_food"
        elif any(word in query_text for word in ["grocery", "groceries", "bigbasket", "zepto"]):
            filter_category = "groceries"
        elif any(word in query_text for word in ["dinner", "lunch", "restaurant", "dining"]):
            filter_category = "dining"
        elif any(word in query_text for word in ["travel", "ola", "uber", "taxi", "train", "flight"]):
            filter_category = "travel"
        elif any(word in query_text for word in ["shopping", "clothes", "fashion"]):
            filter_category = "shopping"
        elif any(word in query_text for word in ["book", "books", "novel", "magazine"]):
            filter_category = "books"
        elif any(word in query_text for word in ["food", "snack", "alcohol"]):
            filter_category = "food"
        elif any(word in query_text for word in ["entertainment", "netflix", "disney", "prime"]):
            filter_category = "entertainment"
        elif any(word in query_text for word in ["utilities", "electricity", "water", "internet", "gas"]):
            filter_category = "utilities"
        elif any(word in query_text for word in ["health", "doctor", "pharmacy", "medicine"]):
            filter_category = "health"
        elif any(word in query_text for word in ["education", "tuition", "school", "college", "course"]):
            filter_category = "education"
        elif any(word in query_text for word in ["personal care", "salon", "spa", "beauty"]):
            filter_category = "personal_care"
        elif any(word in query_text for word in ["rent", "apartment"]):
            filter_category = "rent"
        elif any(word in query_text for word in ["fuel", "petrol", "diesel"]):
            filter_category = "fuel"
        elif any(word in query_text for word in ["repair", "maintenance", "service"]):
            filter_category = "maintenance"
        elif any(word in query_text for word in ["subscription", "invest", "donation", "charity"]):
            # You can further refine these if needed.
            filter_category = "subscriptions"  # or "investments"/"charity" as appropriate.
        
        logger.info("Query filters – Category: %s, Date: %s", filter_category, filter_date)

        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                base_query = "SELECT description, amount, date, category FROM expenses"
                conditions = []
                params: List[Any] = []
                if filter_category:
                    conditions.append("category LIKE ?")
                    params.append(f"%{filter_category}%")
                if filter_date:
                    conditions.append("date = ?")
                    params.append(filter_date)
                query = base_query + (" WHERE " + " AND ".join(conditions) if conditions else "")
                logger.info("Executing query: %s with params: %s", query, params)
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
        except Exception as e:
            dispatcher.utter_message(text="❗ There was an error retrieving your expenses.")
            logger.error("SQL query error: %s", e)
            return []

        if rows:
            total_amount = sum(row[1] for row in rows)
            response_lines = []

            # Build header using Markdown and emojis.
            if filter_category and not filter_date:
                emoji = CATEGORY_EMOJI.get(filter_category, "")
                header = f"**Your total {filter_category.replace('_', ' ').title()} expenditure {emoji} is ₹{total_amount}, which includes:**"
                response_lines.append(header)
            elif filter_date and not filter_category:
                formatted_date = datetime.datetime.strptime(filter_date, "%Y-%m-%d").strftime("%b %d, %Y")
                response_lines.append(f"**Expenses on {formatted_date}:**")
            elif filter_date and filter_category:
                formatted_date = datetime.datetime.strptime(filter_date, "%Y-%m-%d").strftime("%b %d, %Y")
                emoji = CATEGORY_EMOJI.get(filter_category, "")
                response_lines.append(f"**Your {filter_category.replace('_', ' ').title()} expenses {emoji} on {formatted_date}:**")
            else:
                response_lines.append(f"**Your Total Expenses are ₹{total_amount}:**")

            # Detailed breakdown.
            for desc, amt, exp_date, cats in rows:
                try:
                    formatted_date = datetime.datetime.strptime(exp_date, "%Y-%m-%d").strftime("%b %d, %Y")
                except Exception:
                    formatted_date = exp_date
                response_lines.append(f"- **{desc}** – ₹{amt} on {formatted_date} _(Categories: {cats})_")
            response_message = "\n".join(response_lines)
        else:
            response_message = "❗ *No expenses found for the given criteria.*"

        dispatcher.utter_message(text=response_message)
        return []
