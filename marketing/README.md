# Marketing Assets

This directory contains marketing materials including landing pages and email templates.

## Directory Structure

### `landing_pages/`
Landing page HTML files and related assets.

- **assets/**: HTML, markdown, and text files for landing page content
- **tests/**: Puppeteer test scripts for validating landing page functionality

To run landing page tests:
```bash
cd landing_pages
npm install  # Install dependencies
npm test     # Run tests
```

### `emails/`
Email template and copy for marketing campaigns.

- **category_emails.md**: Category-specific email templates and messaging

## Setup

Landing pages require Node.js and npm installed. Install dependencies with:
```bash
npm install
```

This will install Puppeteer for automated testing.
