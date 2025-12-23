# Landing Pages

## Directory Structure

### `assets/`
Landing page source files:
- `category-1-invisible.html`: Main landing page template
- `index.html`: Simple landing page index
- `category_copy.md`: Marketing copy and messaging
- `Category one LP.txt`: Alternative copy document

### `tests/`
Puppeteer test scripts for landing page functionality:
- `test-form-mobile.js`: Mobile form submission tests
- `test-form-wait.js`: Form validation and wait tests
- `test-scaled.js`: Responsive scaling tests
- `mobile-test.js`: Mobile-specific functionality tests

## Running Tests

```bash
npm install
node tests/test-form-mobile.js
```

## Notes

Uses Puppeteer for headless browser testing. Requires Chrome/Chromium.
