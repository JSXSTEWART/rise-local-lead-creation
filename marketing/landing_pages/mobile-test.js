const puppeteer = require('puppeteer');
const path = require('path');

const devices = [
    { name: 'iPhone-SE', width: 375, height: 667, deviceScaleFactor: 2 },
    { name: 'iPhone-12-Pro', width: 390, height: 844, deviceScaleFactor: 3 },
    { name: 'iPhone-14-Pro-Max', width: 430, height: 932, deviceScaleFactor: 3 },
    { name: 'Pixel-7', width: 412, height: 915, deviceScaleFactor: 2.625 },
    { name: 'iPad-Mini', width: 768, height: 1024, deviceScaleFactor: 2 },
];

async function testMobile() {
    console.log('Starting mobile viewport tests...\n');

    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const results = [];

    for (const device of devices) {
        console.log(`Testing ${device.name} (${device.width}x${device.height})...`);

        const page = await browser.newPage();
        await page.setViewport({
            width: device.width,
            height: device.height,
            deviceScaleFactor: device.deviceScaleFactor,
            isMobile: true,
            hasTouch: true
        });

        await page.goto('http://localhost:8080/category-1-invisible.html', {
            waitUntil: 'networkidle2',
            timeout: 30000
        });

        // Wait for animations to settle
        await new Promise(resolve => setTimeout(resolve, 2000));

        // Take full page screenshot
        const screenshotPath = path.join(__dirname, `screenshots/${device.name}.png`);
        await page.screenshot({
            path: screenshotPath,
            fullPage: true
        });

        // Check for horizontal overflow
        const hasHorizontalOverflow = await page.evaluate(() => {
            return document.documentElement.scrollWidth > document.documentElement.clientWidth;
        });

        // Check text sizes
        const textAnalysis = await page.evaluate(() => {
            const h1 = document.querySelector('h1');
            const h1Style = window.getComputedStyle(h1);
            const h1Size = parseFloat(h1Style.fontSize);

            const body = document.querySelector('body');
            const bodyStyle = window.getComputedStyle(body);
            const bodySize = parseFloat(bodyStyle.fontSize);

            // Check if any text is too small (less than 12px)
            const allText = document.querySelectorAll('p, span, div, a, li');
            let smallTextCount = 0;
            allText.forEach(el => {
                const style = window.getComputedStyle(el);
                if (parseFloat(style.fontSize) < 12 && el.textContent.trim().length > 0) {
                    smallTextCount++;
                }
            });

            // Check button tap targets (should be at least 44x44)
            const buttons = document.querySelectorAll('a, button');
            let smallButtons = [];
            buttons.forEach(btn => {
                const rect = btn.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    if (rect.width < 44 || rect.height < 44) {
                        smallButtons.push({
                            text: btn.textContent.slice(0, 30),
                            width: rect.width,
                            height: rect.height
                        });
                    }
                }
            });

            // Check for content cut off
            const heroSection = document.querySelector('section');
            const heroRect = heroSection ? heroSection.getBoundingClientRect() : null;

            return {
                h1FontSize: h1Size,
                bodyFontSize: bodySize,
                smallTextCount,
                smallButtons,
                heroVisible: heroRect ? heroRect.width <= window.innerWidth : true
            };
        });

        // Check spacing and layout issues
        const layoutAnalysis = await page.evaluate(() => {
            const issues = [];

            // Check if cards are properly stacked on mobile
            const cards = document.querySelectorAll('.glass-card');
            if (cards.length > 0) {
                const firstCard = cards[0].getBoundingClientRect();
                const secondCard = cards[1] ? cards[1].getBoundingClientRect() : null;
                if (secondCard && Math.abs(firstCard.top - secondCard.top) < 10) {
                    issues.push('Cards may not be stacking properly on mobile');
                }
            }

            // Check nav spacing
            const nav = document.querySelector('nav');
            if (nav) {
                const navRect = nav.getBoundingClientRect();
                if (navRect.height < 50) {
                    issues.push('Nav may be too compact');
                }
            }

            // Check padding on sections
            const sections = document.querySelectorAll('section');
            sections.forEach((section, i) => {
                const style = window.getComputedStyle(section);
                const paddingLeft = parseFloat(style.paddingLeft);
                const paddingRight = parseFloat(style.paddingRight);
                if (paddingLeft < 16 || paddingRight < 16) {
                    issues.push(`Section ${i + 1} has insufficient horizontal padding`);
                }
            });

            return issues;
        });

        const deviceResult = {
            device: device.name,
            viewport: `${device.width}x${device.height}`,
            screenshot: screenshotPath,
            hasHorizontalOverflow,
            h1FontSize: textAnalysis.h1FontSize,
            smallTextCount: textAnalysis.smallTextCount,
            smallButtons: textAnalysis.smallButtons,
            layoutIssues: layoutAnalysis,
            pass: !hasHorizontalOverflow && textAnalysis.smallTextCount === 0 && layoutAnalysis.length === 0
        };

        results.push(deviceResult);

        // Log issues
        if (hasHorizontalOverflow) {
            console.log(`  ❌ Horizontal overflow detected`);
        }
        if (textAnalysis.smallTextCount > 0) {
            console.log(`  ⚠️  ${textAnalysis.smallTextCount} elements with small text (<12px)`);
        }
        if (textAnalysis.smallButtons.length > 0) {
            console.log(`  ⚠️  ${textAnalysis.smallButtons.length} buttons with small tap targets`);
        }
        if (layoutAnalysis.length > 0) {
            layoutAnalysis.forEach(issue => console.log(`  ⚠️  ${issue}`));
        }
        if (deviceResult.pass) {
            console.log(`  ✅ All checks passed`);
        }

        console.log(`  H1 font size: ${textAnalysis.h1FontSize}px`);
        console.log('');

        await page.close();
    }

    await browser.close();

    // Summary
    console.log('='.repeat(50));
    console.log('SUMMARY');
    console.log('='.repeat(50));

    const passCount = results.filter(r => r.pass).length;
    console.log(`\nPassed: ${passCount}/${results.length} devices\n`);

    if (passCount < results.length) {
        console.log('Issues to fix:');
        results.forEach(r => {
            if (!r.pass) {
                console.log(`\n${r.device}:`);
                if (r.hasHorizontalOverflow) console.log('  - Fix horizontal overflow');
                if (r.smallTextCount > 0) console.log(`  - Increase font size for ${r.smallTextCount} elements`);
                if (r.smallButtons.length > 0) console.log(`  - Increase tap target size for ${r.smallButtons.length} buttons`);
                r.layoutIssues.forEach(issue => console.log(`  - ${issue}`));
            }
        });
    }

    return results;
}

// Create screenshots directory
const fs = require('fs');
const screenshotsDir = path.join(__dirname, 'screenshots');
if (!fs.existsSync(screenshotsDir)) {
    fs.mkdirSync(screenshotsDir);
}

testMobile().catch(console.error);
