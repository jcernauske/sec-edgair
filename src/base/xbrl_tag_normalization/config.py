"""Configuration for XBRL tag normalization pipeline.

Defines 25 canonical CDEs (CDE-007 through CDE-031) and the tiered mapping
rules that classify 3,285 us-gaap XBRL concepts into those CDEs.
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
# CDE Definitions: 25 canonical financial concepts (CDE-007 through CDE-031)
# ---------------------------------------------------------------------------

CDE_DEFINITIONS: dict[str, dict] = {
    # Balance Sheet (8)
    "CDE-007": {
        "name": "Total Assets",
        "category": "balance_sheet",
        "subcategory": "assets",
        "definition": "Sum of all current and non-current assets reported on the balance sheet.",
    },
    "CDE-008": {
        "name": "Total Liabilities",
        "category": "balance_sheet",
        "subcategory": "liabilities",
        "definition": "Sum of all current and non-current liabilities reported on the balance sheet.",
    },
    "CDE-009": {
        "name": "Total Stockholders Equity",
        "category": "balance_sheet",
        "subcategory": "equity",
        "definition": "Total equity attributable to shareholders, including common stock, APIC, retained earnings, and AOCI.",
    },
    "CDE-010": {
        "name": "Cash and Cash Equivalents",
        "category": "balance_sheet",
        "subcategory": "assets",
        "definition": "Cash on hand and short-term, highly liquid investments readily convertible to known cash amounts.",
    },
    "CDE-011": {
        "name": "Accounts Receivable",
        "category": "balance_sheet",
        "subcategory": "assets",
        "definition": "Amounts owed to the company by customers for goods or services delivered, net of allowances.",
    },
    "CDE-012": {
        "name": "Inventory",
        "category": "balance_sheet",
        "subcategory": "assets",
        "definition": "Goods available for sale or in production, including raw materials, WIP, and finished goods.",
    },
    "CDE-013": {
        "name": "Property Plant and Equipment",
        "category": "balance_sheet",
        "subcategory": "assets",
        "definition": "Tangible long-lived assets used in operations, net of accumulated depreciation.",
    },
    "CDE-014": {
        "name": "Goodwill",
        "category": "balance_sheet",
        "subcategory": "assets",
        "definition": "Excess of purchase price over fair value of net identifiable assets acquired in a business combination.",
    },
    # Income Statement (8)
    "CDE-015": {
        "name": "Revenue",
        "category": "income_statement",
        "subcategory": "revenue",
        "definition": "Total revenue recognized from the sale of goods and services, before deductions.",
    },
    "CDE-016": {
        "name": "Cost of Revenue",
        "category": "income_statement",
        "subcategory": "expenses",
        "definition": "Direct costs attributable to the production of goods and services sold.",
    },
    "CDE-017": {
        "name": "Gross Profit",
        "category": "income_statement",
        "subcategory": "profit",
        "definition": "Revenue minus cost of revenue. Measures production efficiency.",
    },
    "CDE-018": {
        "name": "Operating Income",
        "category": "income_statement",
        "subcategory": "profit",
        "definition": "Profit from core business operations, after operating expenses but before interest and taxes.",
    },
    "CDE-019": {
        "name": "Net Income",
        "category": "income_statement",
        "subcategory": "profit",
        "definition": "Total profit after all expenses, interest, and taxes. Bottom line.",
    },
    "CDE-020": {
        "name": "Income Tax Expense",
        "category": "income_statement",
        "subcategory": "expenses",
        "definition": "Total income tax expense (benefit) recognized for the period.",
    },
    "CDE-021": {
        "name": "Research and Development Expense",
        "category": "income_statement",
        "subcategory": "expenses",
        "definition": "Costs incurred for research and development activities.",
    },
    "CDE-022": {
        "name": "Selling General and Administrative Expense",
        "category": "income_statement",
        "subcategory": "expenses",
        "definition": "Operating expenses for selling, general, and administrative activities.",
    },
    # Cash Flow (4)
    "CDE-023": {
        "name": "Operating Cash Flow",
        "category": "cash_flow",
        "subcategory": "operating",
        "definition": "Net cash provided by or used in operating activities.",
    },
    "CDE-024": {
        "name": "Investing Cash Flow",
        "category": "cash_flow",
        "subcategory": "investing",
        "definition": "Net cash provided by or used in investing activities.",
    },
    "CDE-025": {
        "name": "Financing Cash Flow",
        "category": "cash_flow",
        "subcategory": "financing",
        "definition": "Net cash provided by or used in financing activities.",
    },
    "CDE-026": {
        "name": "Capital Expenditures",
        "category": "cash_flow",
        "subcategory": "investing",
        "definition": "Payments to acquire property, plant, and equipment.",
    },
    # Per-Share (3)
    "CDE-027": {
        "name": "Earnings Per Share Basic",
        "category": "per_share",
        "subcategory": "eps",
        "definition": "Net income divided by weighted average basic shares outstanding.",
    },
    "CDE-028": {
        "name": "Earnings Per Share Diluted",
        "category": "per_share",
        "subcategory": "eps",
        "definition": "Net income divided by weighted average diluted shares outstanding.",
    },
    "CDE-029": {
        "name": "Dividends Per Share",
        "category": "per_share",
        "subcategory": "dividends",
        "definition": "Cash dividends declared per common share.",
    },
    # Other (2)
    "CDE-030": {
        "name": "Comprehensive Income",
        "category": "other",
        "subcategory": "comprehensive_income",
        "definition": "Net income plus other comprehensive income items (unrealized gains/losses, foreign currency adjustments).",
    },
    "CDE-031": {
        "name": "Retained Earnings",
        "category": "other",
        "subcategory": "equity",
        "definition": "Cumulative net income retained in the business, not distributed as dividends.",
    },
}

# ---------------------------------------------------------------------------
# Tier 1: Exact match — concept name → (cde_id, financial_statement, category)
# Confidence: 1.0
# ---------------------------------------------------------------------------

EXACT_MAPPINGS: dict[str, tuple[str, str, str]] = {
    # Balance Sheet — Assets
    "Assets": ("CDE-007", "balance_sheet", "assets"),
    "CashAndCashEquivalentsAtCarryingValue": ("CDE-010", "balance_sheet", "assets"),
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents": ("CDE-010", "balance_sheet", "cash"),
    "AccountsReceivableNetCurrent": ("CDE-011", "balance_sheet", "receivables"),
    "AccountsReceivableNet": ("CDE-011", "balance_sheet", "receivables"),
    "InventoryNet": ("CDE-012", "balance_sheet", "inventory"),
    "PropertyPlantAndEquipmentNet": ("CDE-013", "balance_sheet", "ppe"),
    "Goodwill": ("CDE-014", "balance_sheet", "goodwill"),
    # Balance Sheet — Liabilities & Equity
    "Liabilities": ("CDE-008", "balance_sheet", "liabilities"),
    "LiabilitiesAndStockholdersEquity": ("CDE-008", "balance_sheet", "liabilities"),
    "StockholdersEquity": ("CDE-009", "balance_sheet", "equity"),
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest": ("CDE-009", "balance_sheet", "equity"),
    "RetainedEarningsAccumulatedDeficit": ("CDE-031", "other", "retained_earnings"),
    # Income Statement
    "Revenues": ("CDE-015", "income_statement", "revenue"),
    "RevenueFromContractWithCustomerExcludingAssessedTax": ("CDE-015", "income_statement", "revenue"),
    "SalesRevenueNet": ("CDE-015", "income_statement", "revenue"),
    "SalesRevenueGoodsNet": ("CDE-015", "income_statement", "revenue"),
    "CostOfRevenue": ("CDE-016", "income_statement", "cost_of_revenue"),
    "CostOfGoodsAndServicesSold": ("CDE-016", "income_statement", "cost_of_revenue"),
    "CostOfGoodsSold": ("CDE-016", "income_statement", "cost_of_revenue"),
    "GrossProfit": ("CDE-017", "income_statement", "gross_profit"),
    "OperatingIncomeLoss": ("CDE-018", "income_statement", "operating_income"),
    "NetIncomeLoss": ("CDE-019", "income_statement", "net_income"),
    "IncomeTaxExpenseBenefit": ("CDE-020", "income_statement", "income_tax"),
    "ResearchAndDevelopmentExpense": ("CDE-021", "income_statement", "research_and_development"),
    "SellingGeneralAndAdministrativeExpense": ("CDE-022", "income_statement", "sga"),
    "GeneralAndAdministrativeExpense": ("CDE-022", "income_statement", "sga"),
    # Cash Flow
    "NetCashProvidedByUsedInOperatingActivities": ("CDE-023", "cash_flow", "operating"),
    "NetCashProvidedByUsedInInvestingActivities": ("CDE-024", "cash_flow", "investing"),
    "NetCashProvidedByUsedInFinancingActivities": ("CDE-025", "cash_flow", "financing"),
    "PaymentsToAcquirePropertyPlantAndEquipment": ("CDE-026", "cash_flow", "capex"),
    # Per-Share
    "EarningsPerShareBasic": ("CDE-027", "per_share", "eps"),
    "EarningsPerShareDiluted": ("CDE-028", "per_share", "eps"),
    "CommonStockDividendsPerShareDeclared": ("CDE-029", "per_share", "dividends"),
    "CommonStockDividendsPerShareCashPaid": ("CDE-029", "per_share", "dividends"),
    # Other
    "ComprehensiveIncomeNetOfTax": ("CDE-030", "other", "comprehensive_income"),
    "OtherComprehensiveIncomeLossNetOfTax": ("CDE-030", "other", "comprehensive_income"),
}

# ---------------------------------------------------------------------------
# Tier 2: Prefix rules — if concept starts with prefix → (cde_id, stmt, cat)
# Confidence: 0.7
# Order matters: first match wins.
# ---------------------------------------------------------------------------

PREFIX_RULES: list[tuple[str, str, str, str]] = [
    # (prefix, cde_id, financial_statement, category)
    # Revenue variants
    ("RevenueFromContract", "CDE-015", "income_statement", "revenue"),
    ("SalesRevenue", "CDE-015", "income_statement", "revenue"),
    # Cost variants
    ("CostOfGoods", "CDE-016", "income_statement", "cost_of_revenue"),
    ("CostOfRevenue", "CDE-016", "income_statement", "cost_of_revenue"),
    # Cash variants
    ("CashAndCashEquivalents", "CDE-010", "balance_sheet", "cash"),
    ("CashCashEquivalents", "CDE-010", "balance_sheet", "cash"),
    # Receivables
    ("AccountsReceivable", "CDE-011", "balance_sheet", "receivables"),
    # Inventory
    ("Inventory", "CDE-012", "balance_sheet", "inventory"),
    # PP&E
    ("PropertyPlantAndEquipment", "CDE-013", "balance_sheet", "ppe"),
    # Goodwill
    ("GoodwillAcquired", "CDE-014", "balance_sheet", "goodwill"),
    ("GoodwillImpairment", "CDE-014", "balance_sheet", "goodwill"),
    # Earnings per share
    ("EarningsPerShare", "CDE-027", "per_share", "eps"),
    # Dividends
    ("CommonStockDividendsPerShare", "CDE-029", "per_share", "dividends"),
    ("DividendsCommonStock", "CDE-029", "per_share", "dividends"),
    # R&D
    ("ResearchAndDevelopment", "CDE-021", "income_statement", "research_and_development"),
    # SG&A
    ("SellingGeneralAndAdministrative", "CDE-022", "income_statement", "sga"),
    # Comprehensive income
    ("ComprehensiveIncome", "CDE-030", "other", "comprehensive_income"),
    ("OtherComprehensiveIncome", "CDE-030", "other", "comprehensive_income"),
    # Retained earnings
    ("RetainedEarnings", "CDE-031", "other", "retained_earnings"),
]

# ---------------------------------------------------------------------------
# Tier 2: Pattern rules — regex patterns for broader matching
# Confidence: 0.6
# ---------------------------------------------------------------------------

PATTERN_RULES: list[tuple[str, str, str, str]] = [
    # (regex_pattern, cde_id, financial_statement, category)
    (r"(?i).*Revenue.*(?!Deferred|Remaining|Recognized)", "CDE-015", "income_statement", "revenue"),
    (r"(?i).*NetIncome.*", "CDE-019", "income_statement", "net_income"),
    (r"(?i).*OperatingIncome.*", "CDE-018", "income_statement", "operating_income"),
    (r"(?i).*IncomeTax(?!Reconciliation|Credits|Receivable|Deferred).*ExpenseBenefit.*", "CDE-020", "income_statement", "income_tax"),
    (r"(?i).*CapitalExpenditure.*", "CDE-026", "cash_flow", "capex"),
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
