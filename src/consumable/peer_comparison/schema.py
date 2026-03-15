"""Iceberg schema for consumable.peer_comparison table.

23 fields: sector-level peer rankings for companies across financial metrics.
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

PEER_COMPARISON_SCHEMA = Schema(
    NestedField(field_id=1, name="record_id", field_type=StringType(), required=True),
    NestedField(field_id=2, name="cik", field_type=IntegerType(), required=True),
    NestedField(field_id=3, name="entity_id", field_type=StringType(), required=True),
    NestedField(field_id=4, name="ticker", field_type=StringType(), required=False),
    NestedField(field_id=5, name="canonical_name", field_type=StringType(), required=True),
    NestedField(field_id=6, name="sector", field_type=StringType(), required=True),
    NestedField(field_id=7, name="metric_source", field_type=StringType(), required=True),
    NestedField(field_id=8, name="metric_id", field_type=StringType(), required=True),
    NestedField(field_id=9, name="metric_name", field_type=StringType(), required=True),
    NestedField(field_id=10, name="metric_value", field_type=DoubleType(), required=True),
    NestedField(field_id=11, name="sector_rank", field_type=IntegerType(), required=True),
    NestedField(field_id=12, name="sector_avg", field_type=DoubleType(), required=True),
    NestedField(field_id=13, name="sector_median", field_type=DoubleType(), required=True),
    NestedField(field_id=14, name="sector_percentile", field_type=DoubleType(), required=True),
    NestedField(field_id=15, name="peer_count", field_type=IntegerType(), required=True),
    NestedField(field_id=16, name="fiscal_year", field_type=IntegerType(), required=True),
    NestedField(field_id=17, name="fiscal_period", field_type=StringType(), required=True),
    NestedField(field_id=18, name="fiscal_year_end", field_type=StringType(), required=False),
    NestedField(field_id=19, name="period_end_date", field_type=DateType(), required=True),
    NestedField(field_id=20, name="calendar_year", field_type=IntegerType(), required=True),
    NestedField(field_id=21, name="calendar_quarter", field_type=IntegerType(), required=True),
    NestedField(field_id=22, name="promoted_at", field_type=TimestamptzType(), required=True),
    NestedField(field_id=23, name="load_date", field_type=DateType(), required=True),
)
