import asyncio
from rise_pipeline.tech_stack_scorer import analyze_tech_stack, calculate_pain_score_from_tech
from dotenv import load_dotenv
import json

load_dotenv()

async def test():
    # JC Electrical Services - 4.9 stars, 109 technologies
    result = await analyze_tech_stack(
        business_name='JC Electrical Services',
        technologies='CMS Made Simple, Arvixe, Arvixe DNS, mod_ssl 2.2.24, Apache 2.2, Apache Tomcat JK, OpenSSL, Frontpage Extensions, Apache, Google Analytics, mod_ssl, Unix, Limiter Modules, OpenSSL 0.9.8, Auth Passthrough, PHP, GeoTrust SSL, RapidSSL, Angies List, GlobalSign, AlphaSSL, nginx, Corporate Colocation, Comodo SSL Wildcard, Comodo SSL, InMotion Hosting, SPF, Hover Intent, jQuery, Really Simple Discovery, Font Awesome, jQuery UI, RSS, Apple Mobile Web Clips Icon, Live Writer Support, Wordpress Plugins, Google Font API, jQuery Waypoints, Magnific Popup, WordPress, Contact Form 7, FitVids.JS, Google Maps, Wordpress 4.9, Pingback Support, Viewport Meta, Underscore.js, IPhone / Mobile Compatible, Netlify, DigiCert SSL, Google Cloud, Google, SSL by Default, Gatsby JS, Stripe, Stripe v3, Copyright Year 2017, LetsEncrypt, Webpack, Material UI, core-js, lodash, React, DMARC, Amazon S3 CDN, Amazon, Amazon Frankfurt Region, Google Maps API, Amazon Ohio Region, Amazon Virginia Region, Google Cloud Oregon, Amazon California Region, Amazon London Region, Google Cloud South Carolina, Super Stats, Network Solutions Super Stats, Web Page Maker, Amazon Montreal Region, Google Cloud Frankfurt, U.S. Server Location, InMotion Hosting DNS, Google Webmaster, DMARC None, CommonCrawl Top 50m, jQuery 3.7.1, WordPress 6.4, Facebook, jQuery 3.3.0, CommonCrawl Top 100m, Common Crawl, Wordpress 5.0, Wordpress 5.1, WordPress 5.2, WordPress 5.3, WordPress 5.4, WordPress 5.7, Babel, Twemoji, WordPress 5.8, CPanel SSL, WordPress 5.9, WordPress 6.0, WordPress 6.2, GStatic Google Static Content, imagesLoaded, Lightbox, Salvattore, Elementor, WordPress 6.3',
        tech_count=109
    )

    pain_score = calculate_pain_score_from_tech(result)

    print('\n' + '='*60)
    print('JC ELECTRICAL SERVICES ANALYSIS')
    print('='*60)
    print(f'Rating: 4.9 stars (194 reviews) | Tech Count: 109')
    print(f'\nTech Score: {result.get("tech_score")}/10')
    print(f'Pain Score: {pain_score}')
    print(f'Website Type: {result.get("website_type")}')
    print(f'CMS: {result.get("cms_platform")}')
    print(f'\nBooleans:')
    print(f'  - GTM: {result.get("has_gtm")}')
    print(f'  - GA4: {result.get("has_ga4")}')
    print(f'  - Modern Analytics: {result.get("has_modern_analytics")}')
    print(f'  - CRM: {result.get("has_crm")}')
    print(f'  - Email Marketing: {result.get("has_email_marketing")}')
    print(f'  - Booking: {result.get("has_booking_system")}')
    print(f'  - Lead Capture: {result.get("has_lead_capture")}')

    print(f'\nPain Points ({len(result.get("pain_points", []))}):')
    for pp in result.get('pain_points', []):
        print(f'  • {pp}')

    print(f'\nStrengths ({len(result.get("strengths", []))}):')
    for s in result.get('strengths', []):
        print(f'  • {s}')

    print(f'\nRecommended Pitch:')
    print(f'  "{result.get("recommended_pitch", "N/A")}"')

    print('\n' + '='*60)
    print('Full JSON Response:')
    print('='*60)
    print(json.dumps(result, indent=2))

asyncio.run(test())
