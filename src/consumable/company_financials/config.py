"""Configuration for consumable company financials pipeline."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Warehouse paths
WAREHOUSE_PATH = PROJECT_ROOT / "data" / "consumable" / "iceberg_warehouse"
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog" / "catalog.db"

# Table identifiers
NAMESPACE = "consumable"
TABLE_NAME = "company_financials"

# Grain fields for record_id hash
RECORD_ID_GRAIN = ("cik", "business_term_id", "fiscal_year", "fiscal_period")

# Agent identity
AGENT_ID = "@company-financials"

# ---------------------------------------------------------------------------
# Primary Concepts: ordered preference list per business term
# For concept collision resolution — pick the first concept found in each group
# ---------------------------------------------------------------------------

PRIMARY_CONCEPTS: dict[str, list[str]] = {
    "BT-024": ["Assets"],
    "BT-027": ["Liabilities"],
    "BT-028": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "BT-029": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    ],
    "BT-030": ["AccountsReceivableNetCurrent"],
    "BT-031": ["InventoryNet"],
    "BT-032": ["PropertyPlantAndEquipmentNet"],
    "BT-033": ["Goodwill"],
    "BT-022": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenuesNetOfInterestExpense",
        "SalesRevenueNet",
    ],
    "BT-034": [
        "CostOfRevenue",
        "CostOfGoodsAndServicesSold",
        "CostOfGoodsSold",
    ],
    "BT-035": ["GrossProfit"],
    "BT-036": ["OperatingIncomeLoss"],
    "BT-023": ["NetIncomeLoss"],
    "BT-037": ["IncomeTaxExpenseBenefit"],
    "BT-038": ["ResearchAndDevelopmentExpense"],
    "BT-039": [
        "SellingGeneralAndAdministrativeExpense",
        "GeneralAndAdministrativeExpense",
    ],
    "BT-040": ["NetCashProvidedByUsedInOperatingActivities"],
    "BT-041": ["NetCashProvidedByUsedInInvestingActivities"],
    "BT-042": ["NetCashProvidedByUsedInFinancingActivities"],
    "BT-043": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "BT-044": ["EarningsPerShareBasic"],
    "BT-045": ["EarningsPerShareDiluted"],
    "BT-046": [
        "CommonStockDividendsPerShareDeclared",
        "CommonStockDividendsPerShareCashPaid",
    ],
    "BT-047": ["ComprehensiveIncomeNetOfTax"],
    "BT-048": ["RetainedEarningsAccumulatedDeficit"],
}

# ---------------------------------------------------------------------------
# Primary Unit: expected measurement unit per business term category
# USD for dollar amounts, USD/shares for per-share values
# ---------------------------------------------------------------------------

PRIMARY_UNIT: dict[str, str] = {
    # Balance Sheet
    "BT-024": "USD",
    "BT-027": "USD",
    "BT-028": "USD",
    "BT-029": "USD",
    "BT-030": "USD",
    "BT-031": "USD",
    "BT-032": "USD",
    "BT-033": "USD",
    # Income Statement
    "BT-022": "USD",
    "BT-034": "USD",
    "BT-035": "USD",
    "BT-036": "USD",
    "BT-023": "USD",
    "BT-037": "USD",
    "BT-038": "USD",
    "BT-039": "USD",
    # Cash Flow
    "BT-040": "USD",
    "BT-041": "USD",
    "BT-042": "USD",
    "BT-043": "USD",
    # Per-Share
    "BT-044": "USD/shares",
    "BT-045": "USD/shares",
    "BT-046": "USD/shares",
    # Other
    "BT-047": "USD",
    "BT-048": "USD",
}

# ---------------------------------------------------------------------------
# SIC-to-Sector: static mapping from SIC codes to human-readable sectors
# Derived from the 20 companies in scope
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Legacy ID translation: CDE-XXX → BT-XXX
# Existing Iceberg data still contains CDE-XXX values from before the
# governance model alignment refactor. This mapping normalizes them on read.
# Safe to remove once base tables are rebuilt from raw.
# ---------------------------------------------------------------------------

LEGACY_CDE_TO_BT: dict[str, str] = {
    "CDE-007": "BT-024", "CDE-008": "BT-027", "CDE-009": "BT-028",
    "CDE-010": "BT-029", "CDE-011": "BT-030", "CDE-012": "BT-031",
    "CDE-013": "BT-032", "CDE-014": "BT-033", "CDE-015": "BT-022",
    "CDE-016": "BT-034", "CDE-017": "BT-035", "CDE-018": "BT-036",
    "CDE-019": "BT-023", "CDE-020": "BT-037", "CDE-021": "BT-038",
    "CDE-022": "BT-039", "CDE-023": "BT-040", "CDE-024": "BT-041",
    "CDE-025": "BT-042", "CDE-026": "BT-043", "CDE-027": "BT-044",
    "CDE-028": "BT-045", "CDE-029": "BT-046", "CDE-030": "BT-047",
    "CDE-031": "BT-048",
}

SIC_TO_SECTOR: dict[str, str] = {
    "2086": "Consumer Staples",        # Coca-Cola
    "2834": "Healthcare",              # Pfizer, J&J
    "2841": "Consumer Staples",        # P&G
    "2911": "Energy",                  # Exxon
    "3571": "Technology",              # Apple
    "3674": "Technology",              # Intel
    "3711": "Consumer Discretionary",  # Tesla
    "3721": "Industrials",             # Boeing
    "5331": "Consumer Staples",        # Walmart
    "5961": "Consumer Discretionary",  # Amazon
    "6020": "Financials",              # JPMorgan
    "6211": "Financials",              # Goldman Sachs
    "6324": "Healthcare",              # UnitedHealth
    "6331": "Financials",              # Berkshire
    "7370": "Technology",              # Meta
    "7372": "Technology",              # Microsoft, Alphabet
    "7389": "Financials",              # Visa
    "7841": "Communication Services",  # Netflix
}
