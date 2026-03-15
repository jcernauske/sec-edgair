"""Iceberg schema for consumable.company_financials table.

23 fields: the denormalized, collision-resolved, one-row-per-grain table
for cross-company financial comparison.
"""

from pyiceberg.schema import Schema
from pyiceberg.types import (
    DateType,
    DoubleType,
    IntegerType,
    NestedField,
    StringType,
    TimestamptzType,
)

COMPANY_FINANCIALS_SCHEMA = Schema(
    NestedField(field_id=1, name="record_id", field_type=StringType(), required=True),
    NestedField(field_id=2, name="cik", field_type=IntegerType(), required=True),
    NestedField(field_id=3, name="entity_id", field_type=StringType(), required=True),
    NestedField(field_id=4, name="ticker", field_type=StringType(), required=False),
    NestedField(field_id=5, name="canonical_name", field_type=StringType(), required=True),
    NestedField(field_id=6, name="sector", field_type=StringType(), required=True),
    NestedField(field_id=7, name="business_term_id", field_type=StringType(), required=True),
    NestedField(field_id=8, name="business_term", field_type=StringType(), required=True),
    NestedField(field_id=9, name="financial_statement", field_type=StringType(), required=True),
    NestedField(field_id=10, name="category", field_type=StringType(), required=True),
    NestedField(field_id=11, name="val", field_type=DoubleType(), required=True),
    NestedField(field_id=12, name="unit", field_type=StringType(), required=True),
    NestedField(field_id=13, name="source_concept", field_type=StringType(), required=True),
    NestedField(field_id=14, name="fiscal_year", field_type=IntegerType(), required=True),
    NestedField(field_id=15, name="fiscal_period", field_type=StringType(), required=True),
    NestedField(field_id=16, name="fiscal_year_end", field_type=StringType(), required=False),
    NestedField(field_id=17, name="period_end_date", field_type=DateType(), required=True),
    NestedField(field_id=18, name="calendar_year", field_type=IntegerType(), required=True),
    NestedField(field_id=19, name="calendar_quarter", field_type=IntegerType(), required=True),
    NestedField(field_id=20, name="accession_number", field_type=StringType(), required=True),
    NestedField(field_id=21, name="filed_date", field_type=DateType(), required=True),
    NestedField(field_id=22, name="companies_reporting", field_type=IntegerType(), required=True),
    NestedField(field_id=23, name="promoted_at", field_type=TimestamptzType(), required=True),
    NestedField(field_id=24, name="load_date", field_type=DateType(), required=True),
)
