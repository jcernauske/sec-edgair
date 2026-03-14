"""Iceberg schema definitions for base.entity_mappings and base.entity_resolution_audit."""

from pyiceberg.schema import Schema
from pyiceberg.types import (
    DateType,
    DoubleType,
    IntegerType,
    NestedField,
    StringType,
    TimestamptzType,
)

ENTITY_MAPPINGS_SCHEMA = Schema(
    NestedField(field_id=1, name="mapping_id", field_type=StringType(), required=True),
    NestedField(field_id=2, name="cik", field_type=IntegerType(), required=True),
    NestedField(field_id=3, name="canonical_name", field_type=StringType(), required=True),
    NestedField(field_id=4, name="raw_entity_name", field_type=StringType(), required=True),
    NestedField(field_id=5, name="ticker", field_type=StringType(), required=False),
    NestedField(field_id=6, name="sic_code", field_type=StringType(), required=False),
    NestedField(field_id=7, name="fiscal_year_end", field_type=StringType(), required=False),
    NestedField(field_id=8, name="confidence", field_type=DoubleType(), required=True),
    NestedField(field_id=9, name="resolution_method", field_type=StringType(), required=True),
    NestedField(field_id=10, name="status", field_type=StringType(), required=True),
    NestedField(field_id=11, name="resolved_by", field_type=StringType(), required=True),
    NestedField(field_id=12, name="approved_by", field_type=StringType(), required=False),
    NestedField(field_id=13, name="resolved_at", field_type=TimestamptzType(), required=True),
    NestedField(field_id=14, name="approved_at", field_type=TimestamptzType(), required=False),
    NestedField(field_id=15, name="load_date", field_type=DateType(), required=True),
)

ENTITY_RESOLUTION_AUDIT_SCHEMA = Schema(
    NestedField(field_id=1, name="audit_id", field_type=StringType(), required=True),
    NestedField(field_id=2, name="mapping_id", field_type=StringType(), required=True),
    NestedField(field_id=3, name="action", field_type=StringType(), required=True),
    NestedField(field_id=4, name="actor", field_type=StringType(), required=True),
    NestedField(field_id=5, name="reasoning", field_type=StringType(), required=True),
    NestedField(field_id=6, name="evidence", field_type=StringType(), required=True),
    NestedField(field_id=7, name="confidence_at_action", field_type=DoubleType(), required=True),
    NestedField(field_id=8, name="timestamp", field_type=TimestamptzType(), required=True),
    NestedField(field_id=9, name="load_date", field_type=DateType(), required=True),
)
