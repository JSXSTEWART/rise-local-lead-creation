# Utility Scripts

This directory contains utility scripts for the Rise Local Lead Creation pipeline.

## Scripts

### `setup_google_sheet.py`
Initialize and configure a Google Sheet for lead management. This script creates the necessary worksheets and column headers.

**Usage:**
```bash
python scripts/setup_google_sheet.py
```

### `configure_sheet.py`
Configure an existing Google Sheet with proper formatting, data validation, and formula setup.

**Usage:**
```bash
python scripts/configure_sheet.py
```

### `import_clay_builtwith.py`
Import BuildWith company data from Clay into the pipeline. Enriches lead information with technology stack data.

**Usage:**
```bash
python scripts/import_clay_builtwith.py
```

### `run_prequalification_batch.py`
Execute the pre-qualification phase for a batch of leads. Performs initial filtering and scoring.

**Usage:**
```bash
python scripts/run_prequalification_batch.py [options]
```

### `run_phase_2_batch.py`
Execute phase 2 processing for qualified leads. Performs detailed analysis and enrichment.

**Usage:**
```bash
python scripts/run_phase_2_batch.py [options]
```

### `dashboard_generator.py`
Generate presentation-ready dashboard visualizations from pipeline results.

**Usage:**
```bash
python scripts/dashboard_generator.py
```

## Notes

All scripts read configuration from environment variables (`.env` file) and require proper API keys to function.
