"""
Rise Local Lead Processing Pipeline

A pure Python replacement for the Dify workflow.

Usage:
    # Process single lead
    python -m rise_pipeline.pipeline --lead-id <uuid>

    # Process batch
    python -m rise_pipeline.pipeline --batch "id1,id2,id3"

    # Fetch and process new leads
    python -m rise_pipeline.pipeline --fetch-new 10

Modules:
    - config: Environment variables and settings
    - models: Data classes for all entities
    - services: External service clients (Supabase, Clay, etc.)
    - scoring: Pain point scoring algorithm
    - email_generator: Claude API email generation
    - pipeline: Main orchestrator
"""

__version__ = "1.0.0"
__author__ = "Rise Local"
