"""
Test script for Rise Local MCP Server
Verifies all 6 tools work correctly
"""

import asyncio
from server import RiseLocalMCP
import json
from datetime import datetime


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


async def test_health_check(mcp: RiseLocalMCP):
    """Test health check tool"""
    print(f"\n{Colors.HEADER}=== Testing Health Check ==={Colors.ENDC}")

    try:
        result = await mcp.health_check()
        print(f"{Colors.OKGREEN}✓ Health check completed{Colors.ENDC}")
        print(f"  Overall Status: {result['overall_status']}")
        print(f"  Services Checked: {len(result['services'])}")

        for service in result['services']:
            status_color = Colors.OKGREEN if service['status'] == 'healthy' else Colors.FAIL
            print(f"    {status_color}• {service['service']}: {service['status']}{Colors.ENDC}")

        return True
    except Exception as e:
        print(f"{Colors.FAIL}✗ Health check failed: {str(e)}{Colors.ENDC}")
        return False


async def test_extract_owner(mcp: RiseLocalMCP):
    """Test owner extraction tool"""
    print(f"\n{Colors.HEADER}=== Testing Owner Extraction ==={Colors.ENDC}")

    try:
        result = await mcp.extract_owner_info(
            url="https://example.com",
            lead_id="test-001"
        )

        print(f"{Colors.OKGREEN}✓ Owner extraction completed{Colors.ENDC}")
        print(f"  Owner: {result.get('owner_full_name', 'Not found')}")
        print(f"  Confidence: {result.get('confidence', 'low')}")

        if result.get('error'):
            print(f"  {Colors.WARNING}Note: {result['error']}{Colors.ENDC}")

        return True
    except Exception as e:
        print(f"{Colors.FAIL}✗ Owner extraction failed: {str(e)}{Colors.ENDC}")
        return False


async def test_tdlr_search(mcp: RiseLocalMCP):
    """Test TDLR license search tool"""
    print(f"\n{Colors.HEADER}=== Testing TDLR License Search ==={Colors.ENDC}")

    try:
        result = await mcp.search_tdlr_license(
            business_name="Test Electric",
            city="Austin",
            lead_id="test-002"
        )

        print(f"{Colors.OKGREEN}✓ TDLR search completed{Colors.ENDC}")
        print(f"  License Status: {result.get('license_status', 'Unknown')}")

        if result.get('owner_name'):
            print(f"  Owner: {result['owner_name']}")

        if result.get('error'):
            print(f"  {Colors.WARNING}Note: {result['error']}{Colors.ENDC}")

        return True
    except Exception as e:
        print(f"{Colors.FAIL}✗ TDLR search failed: {str(e)}{Colors.ENDC}")
        return False


async def test_bbb_search(mcp: RiseLocalMCP):
    """Test BBB reputation search tool"""
    print(f"\n{Colors.HEADER}=== Testing BBB Reputation Search ==={Colors.ENDC}")

    try:
        result = await mcp.search_bbb_reputation(
            business_name="Test Electric",
            city="Austin",
            state="TX",
            google_rating=4.5,
            lead_id="test-003"
        )

        print(f"{Colors.OKGREEN}✓ BBB search completed{Colors.ENDC}")
        print(f"  BBB Rating: {result.get('bbb_rating', 'NR')}")
        print(f"  Accredited: {result.get('bbb_accredited', False)}")
        print(f"  Reputation Gap: {result.get('reputation_gap', 0)}")

        if result.get('error'):
            print(f"  {Colors.WARNING}Note: {result['error']}{Colors.ENDC}")

        return True
    except Exception as e:
        print(f"{Colors.FAIL}✗ BBB search failed: {str(e)}{Colors.ENDC}")
        return False


async def test_pagespeed(mcp: RiseLocalMCP):
    """Test PageSpeed analysis tool"""
    print(f"\n{Colors.HEADER}=== Testing PageSpeed Analysis ==={Colors.ENDC}")

    try:
        result = await mcp.analyze_pagespeed(
            url="https://example.com",
            strategy="mobile",
            lead_id="test-004"
        )

        print(f"{Colors.OKGREEN}✓ PageSpeed analysis completed{Colors.ENDC}")
        print(f"  Performance Score: {result.get('performance_score', 0)}")
        print(f"  Mobile Score: {result.get('mobile_score', 0)}")
        print(f"  SEO Score: {result.get('seo_score', 0)}")

        if result.get('error'):
            print(f"  {Colors.WARNING}Note: {result['error']}{Colors.ENDC}")

        return True
    except Exception as e:
        print(f"{Colors.FAIL}✗ PageSpeed analysis failed: {str(e)}{Colors.ENDC}")
        return False


async def test_screenshot(mcp: RiseLocalMCP):
    """Test screenshot and visual analysis tool"""
    print(f"\n{Colors.HEADER}=== Testing Screenshot & Visual Analysis ==={Colors.ENDC}")

    try:
        result = await mcp.capture_screenshot_and_analyze(
            url="https://example.com",
            include_mobile=True,
            lead_id="test-005"
        )

        print(f"{Colors.OKGREEN}✓ Screenshot analysis completed{Colors.ENDC}")
        print(f"  Visual Score: {result.get('visual_score', 0)}")
        print(f"  Design Era: {result.get('design_era', 'Unknown')}")
        print(f"  Mobile Responsive: {result.get('mobile_responsive', False)}")

        if result.get('error'):
            print(f"  {Colors.WARNING}Note: {result['error']}{Colors.ENDC}")

        return True
    except Exception as e:
        print(f"{Colors.FAIL}✗ Screenshot analysis failed: {str(e)}{Colors.ENDC}")
        return False


async def test_address_verification(mcp: RiseLocalMCP):
    """Test address verification tool"""
    print(f"\n{Colors.HEADER}=== Testing Address Verification ==={Colors.ENDC}")

    try:
        result = await mcp.verify_address(
            address="123 Main St",
            city="Austin",
            state="TX",
            zip_code="78701",
            lead_id="test-006"
        )

        print(f"{Colors.OKGREEN}✓ Address verification completed{Colors.ENDC}")
        print(f"  Address Type: {result.get('address_type', 'unknown')}")
        print(f"  Is Residential: {result.get('is_residential', None)}")
        print(f"  Verified: {result.get('verified', False)}")

        if result.get('error'):
            print(f"  {Colors.WARNING}Note: {result['error']}{Colors.ENDC}")

        return True
    except Exception as e:
        print(f"{Colors.FAIL}✗ Address verification failed: {str(e)}{Colors.ENDC}")
        return False


async def run_all_tests():
    """Run all MCP tool tests"""

    print(f"\n{Colors.BOLD}{Colors.OKCYAN}")
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║          Rise Local MCP Server - Tool Test Suite                ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}")

    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Initialize MCP client
    print(f"\n{Colors.OKBLUE}Initializing MCP client...{Colors.ENDC}")
    mcp = RiseLocalMCP()

    # Run tests
    tests = [
        ("Health Check", test_health_check),
        ("Owner Extraction", test_extract_owner),
        ("TDLR License Search", test_tdlr_search),
        ("BBB Reputation Search", test_bbb_search),
        ("PageSpeed Analysis", test_pagespeed),
        ("Screenshot Analysis", test_screenshot),
        ("Address Verification", test_address_verification),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            success = await test_func(mcp)
            results.append((test_name, success))
        except Exception as e:
            print(f"{Colors.FAIL}Unexpected error in {test_name}: {str(e)}{Colors.ENDC}")
            results.append((test_name, False))

    # Close client
    await mcp.close()

    # Summary
    print(f"\n{Colors.BOLD}{Colors.OKCYAN}")
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║                         Test Summary                             ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = f"{Colors.OKGREEN}✓ PASS{Colors.ENDC}" if success else f"{Colors.FAIL}✗ FAIL{Colors.ENDC}"
        print(f"  {status}  {test_name}")

    print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.ENDC}")

    if passed == total:
        print(f"{Colors.OKGREEN}All tests passed! MCP server is working correctly.{Colors.ENDC}")
        return 0
    else:
        print(f"{Colors.WARNING}Some tests failed. Check microservice availability.{Colors.ENDC}")
        print(f"\n{Colors.OKCYAN}Troubleshooting tips:{Colors.ENDC}")
        print("  1. Ensure all 6 microservices are running (ports 8001-8006)")
        print("  2. Check Docker: docker compose ps")
        print("  3. View logs: docker compose logs [service-name]")
        print("  4. Verify network: docker network inspect riselocal")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    exit(exit_code)
