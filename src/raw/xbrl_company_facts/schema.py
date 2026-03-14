"""Iceberg schema definition for raw.xbrl_company_facts.

19 columns flattened from the nested SEC EDGAR XBRL Company Facts JSON.
This is the single source of truth for the raw facts table schema.
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

XBRL_COMPANY_FACTS_SCHEMA = Schema(
    NestedField(field_id=1, name="cik", field_type=IntegerType(), required=True),
    NestedField(field_id=2, name="entity_name", field_type=StringType(), required=True),
    NestedField(field_id=3, name="taxonomy", field_type=StringType(), required=True),
    NestedField(field_id=4, name="concept", field_type=StringType(), required=True),
    NestedField(field_id=5, name="label", field_type=StringType(), required=False),
    NestedField(field_id=6, name="description", field_type=StringType(), required=False),
    NestedField(field_id=7, name="unit", field_type=StringType(), required=True),
    NestedField(field_id=8, name="start_date", field_type=DateType(), required=False),
    NestedField(field_id=9, name="end_date", field_type=DateType(), required=True),
    NestedField(field_id=10, name="val", field_type=DoubleType(), required=True),
    NestedField(field_id=11, name="accession_number", field_type=StringType(), required=True),
    NestedField(field_id=12, name="fiscal_year", field_type=IntegerType(), required=False),
    NestedField(field_id=13, name="fiscal_period", field_type=StringType(), required=False),
    NestedField(field_id=14, name="form", field_type=StringType(), required=True),
    NestedField(field_id=15, name="filed_date", field_type=DateType(), required=True),
    NestedField(field_id=16, name="frame", field_type=StringType(), required=False),
    NestedField(field_id=17, name="ingested_at", field_type=TimestamptzType(), required=True),
    NestedField(field_id=18, name="source_url", field_type=StringType(), required=True),
    NestedField(field_id=19, name="source_method", field_type=StringType(), required=True),
    NestedField(field_id=20, name="load_date", field_type=DateType(), required=True),
)
