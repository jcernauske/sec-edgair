"""Iceberg schemas for base financial facts model tables.

Three tables:
- financial_facts: central fact table joining raw + entity + concept mappings
- fiscal_calendar: dimension for cross-company temporal alignment
- amendment_tracking: supersession audit trail
"""

from pyiceberg.schema import Schema
from pyiceberg.types import (
    BooleanType,
    DateType,
    DoubleType,
    IntegerType,
    NestedField,
    StringType,
    TimestamptzType,
)

FINANCIAL_FACTS_SCHEMA = Schema(
    NestedField(field_id=1, name="fact_id", field_type=StringType(), required=True),
    NestedField(field_id=2, name="entity_id", field_type=StringType(), required=True),
    NestedField(field_id=3, name="cik", field_type=IntegerType(), required=True),
    NestedField(field_id=4, name="canonical_name", field_type=StringType(), required=True),
    NestedField(field_id=5, name="ticker", field_type=StringType(), required=False),
    NestedField(field_id=6, name="concept", field_type=StringType(), required=True),
    NestedField(field_id=7, name="cde_id", field_type=StringType(), required=False),
    NestedField(field_id=8, name="canonical_cde", field_type=StringType(), required=False),
    NestedField(field_id=9, name="financial_statement", field_type=StringType(), required=True),
    NestedField(field_id=10, name="category", field_type=StringType(), required=True),
    NestedField(field_id=11, name="tier", field_type=IntegerType(), required=True),
    NestedField(field_id=12, name="taxonomy", field_type=StringType(), required=True),
    NestedField(field_id=13, name="unit", field_type=StringType(), required=True),
    NestedField(field_id=14, name="val", field_type=DoubleType(), required=True),
    NestedField(field_id=15, name="start_date", field_type=DateType(), required=False),
    NestedField(field_id=16, name="end_date", field_type=DateType(), required=True),
    NestedField(field_id=17, name="fiscal_year", field_type=IntegerType(), required=True),
    NestedField(field_id=18, name="fiscal_period", field_type=StringType(), required=True),
    NestedField(field_id=19, name="fiscal_year_end", field_type=StringType(), required=False),
    NestedField(field_id=20, name="calendar_year", field_type=IntegerType(), required=True),
    NestedField(field_id=21, name="calendar_quarter", field_type=IntegerType(), required=True),
    NestedField(field_id=22, name="accession_number", field_type=StringType(), required=True),
    NestedField(field_id=23, name="form", field_type=StringType(), required=True),
    NestedField(field_id=24, name="filed_date", field_type=DateType(), required=True),
    NestedField(field_id=25, name="is_amendment", field_type=BooleanType(), required=True),
    NestedField(field_id=26, name="is_superseded", field_type=BooleanType(), required=True),
    NestedField(field_id=27, name="superseded_by", field_type=StringType(), required=False),
    NestedField(field_id=28, name="promoted_at", field_type=TimestamptzType(), required=True),
)


FISCAL_CALENDAR_SCHEMA = Schema(
    NestedField(field_id=1, name="calendar_id", field_type=StringType(), required=True),
    NestedField(field_id=2, name="cik", field_type=IntegerType(), required=True),
    NestedField(field_id=3, name="entity_id", field_type=StringType(), required=True),
    NestedField(field_id=4, name="fiscal_year", field_type=IntegerType(), required=True),
    NestedField(field_id=5, name="fiscal_period", field_type=StringType(), required=True),
    NestedField(field_id=6, name="fiscal_year_end", field_type=StringType(), required=True),
    NestedField(field_id=7, name="period_start", field_type=DateType(), required=False),
    NestedField(field_id=8, name="period_end", field_type=DateType(), required=True),
    NestedField(field_id=9, name="calendar_year", field_type=IntegerType(), required=True),
    NestedField(field_id=10, name="calendar_quarter", field_type=IntegerType(), required=True),
    NestedField(field_id=11, name="duration_days", field_type=IntegerType(), required=False),
    NestedField(field_id=12, name="is_annual", field_type=BooleanType(), required=True),
)


AMENDMENT_TRACKING_SCHEMA = Schema(
    NestedField(field_id=1, name="tracking_id", field_type=StringType(), required=True),
    NestedField(field_id=2, name="cik", field_type=IntegerType(), required=True),
    NestedField(field_id=3, name="concept", field_type=StringType(), required=True),
    NestedField(field_id=4, name="unit", field_type=StringType(), required=True),
    NestedField(field_id=5, name="start_date", field_type=DateType(), required=False),
    NestedField(field_id=6, name="end_date", field_type=DateType(), required=True),
    NestedField(field_id=7, name="original_accession", field_type=StringType(), required=True),
    NestedField(field_id=8, name="original_filed_date", field_type=DateType(), required=True),
    NestedField(field_id=9, name="original_val", field_type=DoubleType(), required=True),
    NestedField(field_id=10, name="amendment_accession", field_type=StringType(), required=True),
    NestedField(field_id=11, name="amendment_filed_date", field_type=DateType(), required=True),
    NestedField(field_id=12, name="amendment_val", field_type=DoubleType(), required=True),
    NestedField(field_id=13, name="val_change", field_type=DoubleType(), required=True),
    NestedField(field_id=14, name="val_change_pct", field_type=DoubleType(), required=False),
    NestedField(field_id=15, name="amendment_form", field_type=StringType(), required=True),
    NestedField(field_id=16, name="detected_at", field_type=TimestamptzType(), required=True),
)
