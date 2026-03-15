"""Iceberg schema for consumable.financial_ratios table.

24 fields: computed financial ratios with full numerator/denominator transparency.
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

FINANCIAL_RATIOS_SCHEMA = Schema(
    NestedField(field_id=1, name="record_id", field_type=StringType(), required=True),
    NestedField(field_id=2, name="cik", field_type=IntegerType(), required=True),
    NestedField(field_id=3, name="entity_id", field_type=StringType(), required=True),
    NestedField(field_id=4, name="ticker", field_type=StringType(), required=False),
    NestedField(field_id=5, name="canonical_name", field_type=StringType(), required=True),
    NestedField(field_id=6, name="sector", field_type=StringType(), required=True),
    NestedField(field_id=7, name="ratio_id", field_type=StringType(), required=True),
    NestedField(field_id=8, name="ratio_name", field_type=StringType(), required=True),
    NestedField(field_id=9, name="ratio_value", field_type=DoubleType(), required=True),
    NestedField(field_id=10, name="numerator_bt_id", field_type=StringType(), required=True),
    NestedField(field_id=11, name="numerator_bt_name", field_type=StringType(), required=True),
    NestedField(field_id=12, name="numerator_val", field_type=DoubleType(), required=True),
    NestedField(field_id=13, name="denominator_bt_id", field_type=StringType(), required=True),
    NestedField(field_id=14, name="denominator_bt_name", field_type=StringType(), required=True),
    NestedField(field_id=15, name="denominator_val", field_type=DoubleType(), required=True),
    NestedField(field_id=16, name="fiscal_year", field_type=IntegerType(), required=True),
    NestedField(field_id=17, name="fiscal_period", field_type=StringType(), required=True),
    NestedField(field_id=18, name="fiscal_year_end", field_type=StringType(), required=False),
    NestedField(field_id=19, name="period_end_date", field_type=DateType(), required=True),
    NestedField(field_id=20, name="calendar_year", field_type=IntegerType(), required=True),
    NestedField(field_id=21, name="calendar_quarter", field_type=IntegerType(), required=True),
    NestedField(field_id=22, name="companies_reporting", field_type=IntegerType(), required=True),
    NestedField(field_id=23, name="promoted_at", field_type=TimestamptzType(), required=True),
    NestedField(field_id=24, name="load_date", field_type=DateType(), required=True),
)
