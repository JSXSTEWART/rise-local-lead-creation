const puppeteer = require('puppeteer');
const path = require('path');

async function testFormWait() {
    console.log('Testing scanner form with extended wait...\n');

    const browser = await puppeteer.launch({
        headless: false, // Show browser so we can see what's happening
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();

    // Emulate iPhone 12 Pro
    await page.setViewport({
        width: 390,
        height: 844,
        deviceScaleFactor: 2,
        isMobile: true,
        hasTouch: true
    });

    await page.setUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1');

    console.log('Loading page...');
    await page.goto('http://localhost:8080/category-1-invisible.html', {
        waitUntil: 'networkidle0',
        timeout: 60000
    });

    // Scroll to scanner
    await page.evaluate(() => {
        document.querySelector('#scanner').scrollIntoView({ behavior: 'instant', block: 'start' });
    });

    console.log('Waiting 10 seconds for iframe to fully load...');
    await new Promise(resolve => setTimeout(resolve, 10000));

    // Take screenshot
    await page.screenshot({
        path: path.join(__dirname, 'screenshots/form-after-wait.png'),
        fullPage: false
    });
    console.log('Screenshot saved: form-after-wait.png');

    // Check iframe
    const frames = page.frames();
    console.log(`\nFound ${frames.length} frames:`);

    for (const frame of frames) {
        const url = frame.url();
        if (url && url.length > 0) {
            console.log(`  - ${url.substring(0, 80)}...`);
        }
    }

    // Try to find form elements in iframe
    const scannerFrame = frames.find(f => f.url().includes('optimizelocation'));

    if (scannerFrame) {
        console.log('\nAnalyzing scanner iframe content...');

        try {
            const formInfo = await scannerFrame.evaluate(() => {
                const inputs = document.querySelectorAll('input, select, button, textarea');
                const elements = [];

                inputs.forEach(el => {
                    const rect = el.getBoundingClientRect();
                    elements.push({
                        tag: el.tagName,
                        type: el.type || '',
                        name: el.name || el.placeholder || el.className || 'unnamed',
                        visible: rect.width > 0 && rect.height > 0,
                        width: Math.round(rect.width),
                        height: Math.round(rect.height),
                        top: Math.round(rect.top)
                    });
                });

                return {
                    bodyHeight: document.body.scrollHeight,
                    bodyWidth: document.body.scrollWidth,
                    elements: elements,
                    html: document.body.innerHTML.substring(0, 500)
                };
            });

            console.log(`\nForm body size: ${formInfo.bodyWidth}x${formInfo.bodyHeight}px`);
            console.log(`Form elements found: ${formInfo.elements.length}`);

            if (formInfo.elements.length > 0) {
                console.log('\nForm elements:');
                formInfo.elements.forEach((el, i) => {
                    const vis = el.visible ? '✓' : '✗';
                    console.log(`  ${vis} [${el.tag}] ${el.type} "${el.name}" - ${el.width}x${el.height}px at y:${el.top}`);
                });
            }

            console.log('\nHTML preview:');
            console.log(formInfo.html);

        } catch (e) {
            console.log('Could not access iframe content:', e.message);
        }
    }

    console.log('\n\nBrowser left open - inspect manually. Press Ctrl+C to close.');
    await new Promise(() => {});
}

testFormWait().catch(console.error);
