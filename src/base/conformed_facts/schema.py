"""Iceberg schema for base.conformed_facts table.

Matches the approved physical model: governance/models/base-conformed-facts-physical.md
25 columns, field_ids 1-25.
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

CONFORMED_FACTS_SCHEMA = Schema(
    NestedField(field_id=1, name="conformed_id", field_type=StringType(), required=True),
    NestedField(field_id=2, name="source_fact_id", field_type=StringType(), required=True),
    NestedField(field_id=3, name="entity_id", field_type=StringType(), required=True),
    NestedField(field_id=4, name="cik", field_type=IntegerType(), required=True),
    NestedField(field_id=5, name="canonical_name", field_type=StringType(), required=True),
    NestedField(field_id=6, name="ticker", field_type=StringType(), required=False),
    NestedField(field_id=7, name="business_term_id", field_type=StringType(), required=True),
    NestedField(field_id=8, name="business_term", field_type=StringType(), required=True),
    NestedField(field_id=9, name="financial_statement", field_type=StringType(), required=True),
    NestedField(field_id=10, name="category", field_type=StringType(), required=True),
    NestedField(field_id=11, name="source_concept", field_type=StringType(), required=True),
    NestedField(field_id=12, name="val", field_type=DoubleType(), required=True),
    NestedField(field_id=13, name="unit", field_type=StringType(), required=True),
    NestedField(field_id=14, name="fiscal_year", field_type=IntegerType(), required=True),
    NestedField(field_id=15, name="fiscal_period", field_type=StringType(), required=True),
    NestedField(field_id=16, name="fiscal_year_end", field_type=StringType(), required=False),
    NestedField(field_id=17, name="period_end_date", field_type=DateType(), required=True),
    NestedField(field_id=18, name="calendar_year", field_type=IntegerType(), required=True),
    NestedField(field_id=19, name="calendar_quarter", field_type=IntegerType(), required=True),
    NestedField(field_id=20, name="accession_number", field_type=StringType(), required=True),
    NestedField(field_id=21, name="filed_date", field_type=DateType(), required=True),
    NestedField(field_id=22, name="competing_fact_count", field_type=IntegerType(), required=True),
    NestedField(field_id=23, name="selection_reason", field_type=StringType(), required=True),
    NestedField(field_id=24, name="promoted_at", field_type=TimestamptzType(), required=True),
    NestedField(field_id=25, name="load_date", field_type=DateType(), required=True),
)
