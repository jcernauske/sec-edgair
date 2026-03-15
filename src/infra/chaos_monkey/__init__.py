"""Chaos Monkey — adversarial DQ testing for the SEC EDGAIR pipeline.

Injects realistic data corruption into a shadow copy of raw zone data,
then reconciles DQ results against the injection manifest to prove
rule coverage. Dev-only, with a three-layer kill switch.
"""
