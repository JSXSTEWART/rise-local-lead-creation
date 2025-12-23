const puppeteer = require('puppeteer');
const path = require('path');

async function testScaled() {
    console.log('Testing scaled scanner form on mobile...\n');

    const browser = await puppeteer.launch({
        headless: true,
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

    await page.setUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15');

    console.log('Loading page...');
    await page.goto('http://localhost:8080/category-1-invisible.html', {
        waitUntil: 'networkidle0',
        timeout: 60000
    });

    // Scroll to scanner
    await page.evaluate(() => {
        document.querySelector('#scanner').scrollIntoView({ behavior: 'instant', block: 'start' });
    });

    console.log('Waiting 8 seconds for form to load...');
    await new Promise(resolve => setTimeout(resolve, 8000));

    // Screenshot scanner section
    await page.screenshot({
        path: path.join(__dirname, 'screenshots/mobile-scaled-1.png'),
        fullPage: false
    });
    console.log('Screenshot 1: Scanner top');

    // Scroll down a bit
    await page.evaluate(() => window.scrollBy(0, 300));
    await new Promise(resolve => setTimeout(resolve, 1000));

    await page.screenshot({
        path: path.join(__dirname, 'screenshots/mobile-scaled-2.png'),
        fullPage: false
    });
    console.log('Screenshot 2: Scanner scrolled');

    // Get container info
    const info = await page.evaluate(() => {
        const container = document.querySelector('.scanner-container');
        const wrapper = document.querySelector('.scanner-wrapper');
        const iframe = document.querySelector('.scanner-iframe');

        return {
            container: container ? {
                width: container.offsetWidth,
                height: container.offsetHeight
            } : null,
            wrapper: wrapper ? {
                width: wrapper.offsetWidth,
                height: wrapper.offsetHeight,
                transform: getComputedStyle(wrapper).transform
            } : null,
            iframe: iframe ? {
                width: iframe.offsetWidth,
                height: iframe.offsetHeight
            } : null
        };
    });

    console.log('\nElement dimensions:');
    console.log('  Container:', info.container);
    console.log('  Wrapper:', info.wrapper);
    console.log('  Iframe:', info.iframe);

    await browser.close();
    console.log('\nDone!');
}

testScaled().catch(console.error);
