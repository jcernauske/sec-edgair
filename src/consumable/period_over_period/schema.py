"""Iceberg schema for consumable.period_over_period table.

25 fields: period-over-period growth metrics with full transparency.
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

PERIOD_OVER_PERIOD_SCHEMA = Schema(
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
    NestedField(field_id=11, name="fiscal_year", field_type=IntegerType(), required=True),
    NestedField(field_id=12, name="fiscal_period", field_type=StringType(), required=True),
    NestedField(field_id=13, name="fiscal_year_end", field_type=StringType(), required=False),
    NestedField(field_id=14, name="period_end_date", field_type=DateType(), required=True),
    NestedField(field_id=15, name="calendar_year", field_type=IntegerType(), required=True),
    NestedField(field_id=16, name="calendar_quarter", field_type=IntegerType(), required=True),
    NestedField(field_id=17, name="growth_type", field_type=StringType(), required=True),
    NestedField(field_id=18, name="growth_value", field_type=DoubleType(), required=True),
    NestedField(field_id=19, name="current_val", field_type=DoubleType(), required=True),
    NestedField(field_id=20, name="prior_val", field_type=DoubleType(), required=False),
    NestedField(field_id=21, name="base_val", field_type=DoubleType(), required=False),
    NestedField(field_id=22, name="base_fiscal_year", field_type=IntegerType(), required=False),
    NestedField(field_id=23, name="companies_reporting", field_type=IntegerType(), required=True),
    NestedField(field_id=24, name="promoted_at", field_type=TimestamptzType(), required=True),
    NestedField(field_id=25, name="load_date", field_type=DateType(), required=True),
)
