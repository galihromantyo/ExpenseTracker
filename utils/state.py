# Flow names
FLOW_INPUT = "input"
FLOW_REPORT = "report"
FLOW_BUDGET = "budget"
FLOW_EDIT = "edit"
FLOW_DELETE = "delete"
FLOW_EXPORT = "export"

# Step names – input flow
STEP_CONFIRMING = "confirming"
STEP_EDITING_FIELD = "editing_field"
STEP_EDITING_VALUE = "editing_value"

# Step names – report flow
STEP_ASK_MONTH = "ask_month"
STEP_ASK_CURRENCY_CHOICE = "ask_currency_choice"
STEP_ASK_CHART = "ask_chart"

# Step names – budget flow
STEP_ASK_BUDGET_TYPE = "ask_budget_type"
STEP_ASK_BUDGET_TOTAL = "ask_budget_total"
STEP_ASK_BUDGET_CATEGORY = "ask_budget_category"

# Step names – edit/delete flow
STEP_SELECT_EXPENSE = "select_expense"
STEP_SELECT_FIELD = "select_field"
STEP_ENTER_VALUE = "enter_value"
STEP_CONFIRM_DELETE = "confirm_delete"

# Step names – export flow
STEP_ASK_EXPORT_RANGE = "ask_export_range"

# user_data keys
_K_FLOW = "flow"
_K_STEP = "step"
_K_DATA = "data"


def get_state(ud: dict) -> tuple[str | None, str | None, dict]:
    return ud.get(_K_FLOW), ud.get(_K_STEP), ud.get(_K_DATA, {})


def set_state(ud: dict, flow: str | None, step: str | None, data: dict | None = None) -> None:
    ud[_K_FLOW] = flow
    ud[_K_STEP] = step
    ud[_K_DATA] = data or {}


def update_data(ud: dict, **kwargs) -> None:
    ud.setdefault(_K_DATA, {}).update(kwargs)


def clear_state(ud: dict) -> None:
    ud[_K_FLOW] = None
    ud[_K_STEP] = None
    ud[_K_DATA] = {}
