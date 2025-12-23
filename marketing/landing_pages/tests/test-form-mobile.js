const puppeteer = require('puppeteer');
const path = require('path');

async function testFormMobile() {
    console.log('Testing scanner form on mobile with 4G LTE...\n');

    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();

    // Emulate iPhone 12 Pro
    await page.setViewport({
        width: 390,
        height: 844,
        deviceScaleFactor: 3,
        isMobile: true,
        hasTouch: true
    });

    // Set user agent to mobile
    await page.setUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1');

    // Enable 4G LTE throttling
    const client = await page.target().createCDPSession();
    await client.send('Network.emulateNetworkConditions', {
        offline: false,
        downloadThroughput: (12 * 1024 * 1024) / 8,
        uploadThroughput: (6 * 1024 * 1024) / 8,
        latency: 70
    });

    console.log('Loading page on 4G LTE...');
    const startTime = Date.now();

    await page.goto('http://localhost:8080/category-1-invisible.html', {
        waitUntil: 'networkidle2',
        timeout: 60000
    });

    const loadTime = Date.now() - startTime;
    console.log(`Page loaded in ${loadTime}ms\n`);

    // Take screenshot of hero
    await page.screenshot({
        path: path.join(__dirname, 'screenshots/mobile-hero.png'),
        fullPage: false
    });
    console.log('Screenshot: Hero section');

    // Scroll to scanner section
    console.log('Scrolling to scanner section...');
    await page.evaluate(() => {
        const scanner = document.querySelector('#scanner');
        if (scanner) {
            scanner.scrollIntoView({ behavior: 'instant', block: 'start' });
        }
    });

    await new Promise(resolve => setTimeout(resolve, 3000));

    // Take screenshot of scanner section
    await page.screenshot({
        path: path.join(__dirname, 'screenshots/mobile-scanner-top.png'),
        fullPage: false
    });
    console.log('Screenshot: Scanner section top');

    // Get iframe details
    const iframeInfo = await page.evaluate(() => {
        const iframe = document.querySelector('.scanner-iframe');
        if (!iframe) return { error: 'Iframe not found' };

        const rect = iframe.getBoundingClientRect();
        const style = window.getComputedStyle(iframe);

        return {
            width: Math.round(rect.width),
            height: Math.round(rect.height),
            top: Math.round(rect.top),
            bottom: Math.round(rect.bottom),
            computedHeight: style.height,
            computedMinHeight: style.minHeight,
            isVisible: rect.width > 0 && rect.height > 0,
            viewportHeight: window.innerHeight,
            visibleInViewport: rect.top < window.innerHeight && rect.bottom > 0
        };
    });

    console.log('\nIframe Analysis:');
    console.log(`  Width: ${iframeInfo.width}px`);
    console.log(`  Height: ${iframeInfo.height}px`);
    console.log(`  Computed Height: ${iframeInfo.computedHeight}`);
    console.log(`  Viewport Height: ${iframeInfo.viewportHeight}px`);
    console.log(`  Visible: ${iframeInfo.isVisible}`);

    // Scroll within the page to show different parts of iframe
    await page.evaluate(() => window.scrollBy(0, 400));
    await new Promise(resolve => setTimeout(resolve, 1000));

    await page.screenshot({
        path: path.join(__dirname, 'screenshots/mobile-scanner-mid.png'),
        fullPage: false
    });
    console.log('Screenshot: Scanner section middle');

    await page.evaluate(() => window.scrollBy(0, 400));
    await new Promise(resolve => setTimeout(resolve, 1000));

    await page.screenshot({
        path: path.join(__dirname, 'screenshots/mobile-scanner-bottom.png'),
        fullPage: false
    });
    console.log('Screenshot: Scanner section bottom');

    // Full page screenshot
    await page.screenshot({
        path: path.join(__dirname, 'screenshots/mobile-full.png'),
        fullPage: true
    });
    console.log('Screenshot: Full page');

    // Check if iframe needs to be taller
    const frames = page.frames();
    let scannerFrame = null;
    for (const frame of frames) {
        if (frame.url().includes('optimizelocation')) {
            scannerFrame = frame;
            break;
        }
    }

    if (scannerFrame) {
        await new Promise(resolve => setTimeout(resolve, 2000));

        try {
            const formHeight = await scannerFrame.evaluate(() => {
                return document.body.scrollHeight;
            });

            console.log(`\nForm content height: ${formHeight}px`);
            console.log(`Iframe height: ${iframeInfo.height}px`);

            if (formHeight > iframeInfo.height) {
                console.log(`\n❌ FORM IS CUT OFF!`);
                console.log(`   Need to increase iframe height to at least ${formHeight + 50}px`);
            } else {
                console.log(`\n✅ Form fits within iframe`);
            }
        } catch (e) {
            console.log('\nCould not measure form height (cross-origin)');
        }
    }

    console.log('\n' + '='.repeat(50));
    console.log('Done! Check screenshots folder.');

    await browser.close();
}

testFormMobile().catch(console.error);
