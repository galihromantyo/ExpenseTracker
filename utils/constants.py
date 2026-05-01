SUPPORTED_CURRENCIES = ["IDR", "USD", "EUR", "GBP"]

CATEGORIES = [
    "Rent & Housing",
    "Groceries",
    "Food & Dining",
    "Transport",
    "Travel",
    "Shopping",
    "Health & Medical",
    "Utilities & Bills",
    "Subscriptions",
    "Education",
    "Insurance",
    "Remittance",
    "Entertainment",
    "Personal Care",
    "Other",
]

CATEGORY_EMOJI = {
    "Rent & Housing":   "🏠",
    "Groceries":        "🛒",
    "Food & Dining":    "🍽️",
    "Transport":        "🚇",
    "Travel":           "✈️",
    "Shopping":         "🛍️",
    "Health & Medical": "💊",
    "Utilities & Bills":"💡",
    "Subscriptions":    "📱",
    "Education":        "📚",
    "Insurance":        "🛡️",
    "Remittance":       "💸",
    "Entertainment":    "🎭",
    "Personal Care":    "💆",
    "Other":            "📦",
}

EXPENSES_HEADERS = [
    "chat_id", "date", "description", "amount", "currency",
    "category", "payment_method", "input_type", "created_at",
]

BUDGET_HEADERS = [
    "chat_id", "month", "currency", "budget_type", "category", "amount", "notes",
]

USERS_HEADERS = [
    "chat_id", "username", "display_name", "default_currency", "joined_at", "is_active",
]
