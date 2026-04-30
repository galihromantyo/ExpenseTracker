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
    "date", "description", "amount", "currency",
    "category", "payment_method", "input_type", "created_at",
]

BUDGET_HEADERS = [
    "month", "currency", "budget_type", "category", "amount", "notes",
]
