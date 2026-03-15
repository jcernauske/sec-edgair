"""Iceberg schema definitions for base.concept_mappings and base.tag_normalization_audit."""

from pyiceberg.schema import Schema
from pyiceberg.types import (
    DateType,
    DoubleType,
    IntegerType,
    NestedField,
    StringType,
    TimestamptzType,
)

CONCEPT_MAPPINGS_SCHEMA = Schema(
    NestedField(field_id=1, name="mapping_id", field_type=StringType(), required=True),
    NestedField(field_id=2, name="concept", field_type=StringType(), required=True),
    NestedField(field_id=3, name="business_term", field_type=StringType(), required=False),
    NestedField(field_id=4, name="business_term_id", field_type=StringType(), required=False),
    NestedField(field_id=5, name="financial_statement", field_type=StringType(), required=True),
    NestedField(field_id=6, name="category", field_type=StringType(), required=True),
    NestedField(field_id=7, name="tier", field_type=IntegerType(), required=True),
    NestedField(field_id=8, name="confidence", field_type=DoubleType(), required=True),
    NestedField(field_id=9, name="mapping_method", field_type=StringType(), required=True),
    NestedField(field_id=10, name="status", field_type=StringType(), required=True),
    NestedField(field_id=11, name="mapped_by", field_type=StringType(), required=True),
    NestedField(field_id=12, name="mapped_at", field_type=TimestamptzType(), required=True),
    NestedField(field_id=13, name="load_date", field_type=DateType(), required=True),
)

TAG_NORMALIZATION_AUDIT_SCHEMA = Schema(
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
