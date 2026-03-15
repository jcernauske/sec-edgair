"""Configuration for XBRL tag normalization pipeline.

Defines 25 canonical business terms (BT-024 through BT-048) and the tiered mapping
rules that classify 3,285 us-gaap XBRL concepts into those business terms.
"""

from pathlib import Path

from src.config import REQUIRE_HUMAN_APPROVAL  # noqa: F401 — re-exported for local imports

# Confidence threshold — mappings below this ALWAYS require human approval
CONFIDENCE_FLOOR = 0.7

# Paths (relative to project root)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
WAREHOUSE_PATH = PROJECT_ROOT / "data" / "base" / "iceberg_warehouse"
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog" / "catalog.db"
STAGING_DIR = PROJECT_ROOT / "governance" / "tag-normalization"
STAGING_FILE = STAGING_DIR / "proposed-mappings.json"
ARCHIVE_DIR = STAGING_DIR / "archive"

# ---------------------------------------------------------------------------
# Business Term Definitions: 25 canonical financial concepts (BT-024 through BT-048)
# ---------------------------------------------------------------------------

BUSINESS_TERM_DEFINITIONS: dict[str, dict] = {
    # Balance Sheet (8)
    "BT-024": {
        "name": "Total Assets",
        "category": "balance_sheet",
        "subcategory": "assets",
        "definition": "Sum of all current and non-current assets reported on the balance sheet.",
    },
    "BT-027": {
        "name": "Total Liabilities",
        "category": "balance_sheet",
        "subcategory": "liabilities",
        "definition": "Sum of all current and non-current liabilities reported on the balance sheet.",
    },
    "BT-028": {
        "name": "Total Stockholders Equity",
        "category": "balance_sheet",
        "subcategory": "equity",
        "definition": "Total equity attributable to shareholders, including common stock, APIC, retained earnings, and AOCI.",
    },
    "BT-029": {
        "name": "Cash and Cash Equivalents",
        "category": "balance_sheet",
        "subcategory": "assets",
        "definition": "Cash on hand and short-term, highly liquid investments readily convertible to known cash amounts.",
    },
    "BT-030": {
        "name": "Accounts Receivable",
        "category": "balance_sheet",
        "subcategory": "assets",
        "definition": "Amounts owed to the company by customers for goods or services delivered, net of allowances.",
    },
    "BT-031": {
        "name": "Inventory",
        "category": "balance_sheet",
        "subcategory": "assets",
        "definition": "Goods available for sale or in production, including raw materials, WIP, and finished goods.",
    },
    "BT-032": {
        "name": "Property Plant and Equipment",
        "category": "balance_sheet",
        "subcategory": "assets",
        "definition": "Tangible long-lived assets used in operations, net of accumulated depreciation.",
    },
    "BT-033": {
        "name": "Goodwill",
        "category": "balance_sheet",
        "subcategory": "assets",
        "definition": "Excess of purchase price over fair value of net identifiable assets acquired in a business combination.",
    },
    # Income Statement (8)
    "BT-022": {
        "name": "Revenue",
        "category": "income_statement",
        "subcategory": "revenue",
        "definition": "Total revenue recognized from the sale of goods and services, before deductions.",
    },
    "BT-034": {
        "name": "Cost of Revenue",
        "category": "income_statement",
        "subcategory": "expenses",
        "definition": "Direct costs attributable to the production of goods and services sold.",
    },
    "BT-035": {
        "name": "Gross Profit",
        "category": "income_statement",
        "subcategory": "profit",
        "definition": "Revenue minus cost of revenue. Measures production efficiency.",
    },
    "BT-036": {
        "name": "Operating Income",
        "category": "income_statement",
        "subcategory": "profit",
        "definition": "Profit from core business operations, after operating expenses but before interest and taxes.",
    },
    "BT-023": {
        "name": "Net Income",
        "category": "income_statement",
        "subcategory": "profit",
        "definition": "Total profit after all expenses, interest, and taxes. Bottom line.",
    },
    "BT-037": {
        "name": "Income Tax Expense",
        "category": "income_statement",
        "subcategory": "expenses",
        "definition": "Total income tax expense (benefit) recognized for the period.",
    },
    "BT-038": {
        "name": "Research and Development Expense",
        "category": "income_statement",
        "subcategory": "expenses",
        "definition": "Costs incurred for research and development activities.",
    },
    "BT-039": {
        "name": "Selling General and Administrative Expense",
        "category": "income_statement",
        "subcategory": "expenses",
        "definition": "Operating expenses for selling, general, and administrative activities.",
    },
    # Cash Flow (4)
    "BT-040": {
        "name": "Operating Cash Flow",
        "category": "cash_flow",
        "subcategory": "operating",
        "definition": "Net cash provided by or used in operating activities.",
    },
    "BT-041": {
        "name": "Investing Cash Flow",
        "category": "cash_flow",
        "subcategory": "investing",
        "definition": "Net cash provided by or used in investing activities.",
    },
    "BT-042": {
        "name": "Financing Cash Flow",
        "category": "cash_flow",
        "subcategory": "financing",
        "definition": "Net cash provided by or used in financing activities.",
    },
    "BT-043": {
        "name": "Capital Expenditures",
        "category": "cash_flow",
        "subcategory": "investing",
        "definition": "Payments to acquire property, plant, and equipment.",
    },
    # Per-Share (3)
    "BT-044": {
        "name": "Earnings Per Share Basic",
        "category": "per_share",
        "subcategory": "eps",
        "definition": "Net income divided by weighted average basic shares outstanding.",
    },
    "BT-045": {
        "name": "Earnings Per Share Diluted",
        "category": "per_share",
        "subcategory": "eps",
        "definition": "Net income divided by weighted average diluted shares outstanding.",
    },
    "BT-046": {
        "name": "Dividends Per Share",
        "category": "per_share",
        "subcategory": "dividends",
        "definition": "Cash dividends declared per common share.",
    },
    # Other (2)
    "BT-047": {
        "name": "Comprehensive Income",
        "category": "other",
        "subcategory": "comprehensive_income",
        "definition": "Net income plus other comprehensive income items (unrealized gains/losses, foreign currency adjustments).",
    },
    "BT-048": {
        "name": "Retained Earnings",
        "category": "other",
        "subcategory": "equity",
        "definition": "Cumulative net income retained in the business, not distributed as dividends.",
    },
}

# ---------------------------------------------------------------------------
# Tier 1: Exact match — concept name → (business_term_id, financial_statement, category)
# Confidence: 1.0
# ---------------------------------------------------------------------------

EXACT_MAPPINGS: dict[str, tuple[str, str, str]] = {
    # Balance Sheet — Assets
    "Assets": ("BT-024", "balance_sheet", "assets"),
    "CashAndCashEquivalentsAtCarryingValue": ("BT-029", "balance_sheet", "assets"),
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents": ("BT-029", "balance_sheet", "cash"),
    "AccountsReceivableNetCurrent": ("BT-030", "balance_sheet", "receivables"),
    "AccountsReceivableNet": ("BT-030", "balance_sheet", "receivables"),
    "InventoryNet": ("BT-031", "balance_sheet", "inventory"),
    "PropertyPlantAndEquipmentNet": ("BT-032", "balance_sheet", "ppe"),
    "Goodwill": ("BT-033", "balance_sheet", "goodwill"),
    # Balance Sheet — Liabilities & Equity
    "Liabilities": ("BT-027", "balance_sheet", "liabilities"),
    "LiabilitiesAndStockholdersEquity": ("BT-027", "balance_sheet", "liabilities"),
    "StockholdersEquity": ("BT-028", "balance_sheet", "equity"),
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest": ("BT-028", "balance_sheet", "equity"),
    "RetainedEarningsAccumulatedDeficit": ("BT-048", "other", "retained_earnings"),
    # Income Statement
    "Revenues": ("BT-022", "income_statement", "revenue"),
    "RevenueFromContractWithCustomerExcludingAssessedTax": ("BT-022", "income_statement", "revenue"),
    "SalesRevenueNet": ("BT-022", "income_statement", "revenue"),
    "SalesRevenueGoodsNet": ("BT-022", "income_statement", "revenue"),
    "CostOfRevenue": ("BT-034", "income_statement", "cost_of_revenue"),
    "CostOfGoodsAndServicesSold": ("BT-034", "income_statement", "cost_of_revenue"),
    "CostOfGoodsSold": ("BT-034", "income_statement", "cost_of_revenue"),
    "GrossProfit": ("BT-035", "income_statement", "gross_profit"),
    "OperatingIncomeLoss": ("BT-036", "income_statement", "operating_income"),
    "NetIncomeLoss": ("BT-023", "income_statement", "net_income"),
    "IncomeTaxExpenseBenefit": ("BT-037", "income_statement", "income_tax"),
    "ResearchAndDevelopmentExpense": ("BT-038", "income_statement", "research_and_development"),
    "SellingGeneralAndAdministrativeExpense": ("BT-039", "income_statement", "sga"),
    "GeneralAndAdministrativeExpense": ("BT-039", "income_statement", "sga"),
    # Cash Flow
    "NetCashProvidedByUsedInOperatingActivities": ("BT-040", "cash_flow", "operating"),
    "NetCashProvidedByUsedInInvestingActivities": ("BT-041", "cash_flow", "investing"),
    "NetCashProvidedByUsedInFinancingActivities": ("BT-042", "cash_flow", "financing"),
    "PaymentsToAcquirePropertyPlantAndEquipment": ("BT-043", "cash_flow", "capex"),
    # Per-Share
    "EarningsPerShareBasic": ("BT-044", "per_share", "eps"),
    "EarningsPerShareDiluted": ("BT-045", "per_share", "eps"),
    "CommonStockDividendsPerShareDeclared": ("BT-046", "per_share", "dividends"),
    "CommonStockDividendsPerShareCashPaid": ("BT-046", "per_share", "dividends"),
    # Other
    "ComprehensiveIncomeNetOfTax": ("BT-047", "other", "comprehensive_income"),
    "OtherComprehensiveIncomeLossNetOfTax": ("BT-047", "other", "comprehensive_income"),
}

# ---------------------------------------------------------------------------
# Tier 2: Prefix rules — if concept starts with prefix → (business_term_id, stmt, cat)
# Confidence: 0.7
# Order matters: first match wins.
# ---------------------------------------------------------------------------

PREFIX_RULES: list[tuple[str, str, str, str]] = [
    # (prefix, business_term_id, financial_statement, category)
    # Revenue variants
    ("RevenueFromContract", "BT-022", "income_statement", "revenue"),
    ("SalesRevenue", "BT-022", "income_statement", "revenue"),
    # Cost variants
    ("CostOfGoods", "BT-034", "income_statement", "cost_of_revenue"),
    ("CostOfRevenue", "BT-034", "income_statement", "cost_of_revenue"),
    # Cash variants
    ("CashAndCashEquivalents", "BT-029", "balance_sheet", "cash"),
    ("CashCashEquivalents", "BT-029", "balance_sheet", "cash"),
    # Receivables
    ("AccountsReceivable", "BT-030", "balance_sheet", "receivables"),
    # Inventory
    ("Inventory", "BT-031", "balance_sheet", "inventory"),
    # PP&E
    ("PropertyPlantAndEquipment", "BT-032", "balance_sheet", "ppe"),
    # Goodwill
    ("GoodwillAcquired", "BT-033", "balance_sheet", "goodwill"),
    ("GoodwillImpairment", "BT-033", "balance_sheet", "goodwill"),
    # Earnings per share
    ("EarningsPerShare", "BT-044", "per_share", "eps"),
    # Dividends
    ("CommonStockDividendsPerShare", "BT-046", "per_share", "dividends"),
    ("DividendsCommonStock", "BT-046", "per_share", "dividends"),
    # R&D
    ("ResearchAndDevelopment", "BT-038", "income_statement", "research_and_development"),
    # SG&A
    ("SellingGeneralAndAdministrative", "BT-039", "income_statement", "sga"),
    # Comprehensive income
    ("ComprehensiveIncome", "BT-047", "other", "comprehensive_income"),
    ("OtherComprehensiveIncome", "BT-047", "other", "comprehensive_income"),
    # Retained earnings
    ("RetainedEarnings", "BT-048", "other", "retained_earnings"),
]

# ---------------------------------------------------------------------------
# Tier 2: Pattern rules — regex patterns for broader matching
# Confidence: 0.6
# ---------------------------------------------------------------------------

PATTERN_RULES: list[tuple[str, str, str, str]] = [
    # (regex_pattern, business_term_id, financial_statement, category)
    (r"(?i).*Revenue.*(?!Deferred|Remaining|Recognized)", "BT-022", "income_statement", "revenue"),
    (r"(?i).*NetIncome.*", "BT-023", "income_statement", "net_income"),
    (r"(?i).*OperatingIncome.*", "BT-036", "income_statement", "operating_income"),
    (r"(?i).*IncomeTax(?!Reconciliation|Credits|Receivable|Deferred).*ExpenseBenefit.*", "BT-037", "income_statement", "income_tax"),
    (r"(?i).*CapitalExpenditure.*", "BT-043", "cash_flow", "capex"),
]

# ---------------------------------------------------------------------------
# Heuristic category assignment for Tier 3 (unmapped) concepts
# Maps concept name substrings to (financial_statement, category)
# ---------------------------------------------------------------------------

HEURISTIC_CATEGORIES: list[tuple[str, str, str]] = [
    # (substring, financial_statement, category)
    ("Tax", "income_statement", "tax"),
    ("Lease", "balance_sheet", "leases"),
    ("Debt", "balance_sheet", "debt"),
    ("Stock", "balance_sheet", "equity"),
    ("Share", "per_share", "shares"),
    ("Depreciation", "income_statement", "depreciation"),
    ("Amortization", "income_statement", "amortization"),
    ("Interest", "income_statement", "interest"),
    ("Derivative", "balance_sheet", "derivatives"),
    ("Segment", "other", "segment"),
    ("Pension", "balance_sheet", "pension"),
    ("Impairment", "income_statement", "impairment"),
    ("Restructuring", "income_statement", "restructuring"),
    ("Acquisition", "balance_sheet", "acquisitions"),
    ("Receivable", "balance_sheet", "receivables"),
    ("Payable", "balance_sheet", "payables"),
    ("Asset", "balance_sheet", "assets"),
    ("Liability", "balance_sheet", "liabilities"),
    ("Equity", "balance_sheet", "equity"),
    ("Revenue", "income_statement", "revenue"),
    ("Expense", "income_statement", "expenses"),
    ("Income", "income_statement", "income"),
    ("Cash", "cash_flow", "cash"),
    ("Operating", "income_statement", "operating"),
    ("Investing", "cash_flow", "investing"),
    ("Financing", "cash_flow", "financing"),
]
