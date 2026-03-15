"""Iceberg schema for consumable.amendment_analysis table.

22 fields: company amendment pattern summary per fiscal year.
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

AMENDMENT_ANALYSIS_SCHEMA = Schema(
    NestedField(field_id=1, name="record_id", field_type=StringType(), required=True),
    NestedField(field_id=2, name="cik", field_type=IntegerType(), required=True),
    NestedField(field_id=3, name="entity_id", field_type=StringType(), required=True),
    NestedField(field_id=4, name="ticker", field_type=StringType(), required=False),
    NestedField(field_id=5, name="canonical_name", field_type=StringType(), required=True),
    NestedField(field_id=6, name="sector", field_type=StringType(), required=True),
    NestedField(field_id=7, name="fiscal_year", field_type=IntegerType(), required=True),
    NestedField(field_id=8, name="amendment_count", field_type=IntegerType(), required=True),
    NestedField(field_id=9, name="distinct_concepts", field_type=IntegerType(), required=True),
    NestedField(field_id=10, name="distinct_filings", field_type=IntegerType(), required=True),
    NestedField(field_id=11, name="mean_abs_change", field_type=DoubleType(), required=True),
    NestedField(field_id=12, name="median_abs_change", field_type=DoubleType(), required=True),
    NestedField(field_id=13, name="max_abs_change", field_type=DoubleType(), required=True),
    NestedField(field_id=14, name="mean_pct_change", field_type=DoubleType(), required=False),
    NestedField(field_id=15, name="median_pct_change", field_type=DoubleType(), required=False),
    NestedField(field_id=16, name="total_val_impact", field_type=DoubleType(), required=True),
    NestedField(field_id=17, name="largest_concept", field_type=StringType(), required=True),
    NestedField(field_id=18, name="largest_change", field_type=DoubleType(), required=True),
    NestedField(field_id=19, name="days_to_amend_avg", field_type=DoubleType(), required=True),
    NestedField(field_id=20, name="days_to_amend_median", field_type=DoubleType(), required=True),
    NestedField(field_id=21, name="promoted_at", field_type=TimestamptzType(), required=True),
    NestedField(field_id=22, name="load_date", field_type=DateType(), required=True),
)
