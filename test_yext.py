"""
Standalone Yext API Test
Tests the Yext directory scan endpoint (async - results via webhook/email)
"""
import asyncio
import httpx
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

YEXT_API_KEY = os.getenv("YEXT_API_KEY")
YEXT_ACCOUNT_ID = os.getenv("YEXT_ACCOUNT_ID")

async def test_yext_api():
    print("=" * 60)
    print("YEXT API TEST (with Async Polling)")
    print("=" * 60)

    # Check credentials
    print(f"\nCredentials:")
    print(f"  API Key: {YEXT_API_KEY[:10]}..." if YEXT_API_KEY else "  API Key: NOT SET")
    print(f"  Account ID: {YEXT_ACCOUNT_ID}")

    if not YEXT_API_KEY or not YEXT_ACCOUNT_ID:
        print("\nERROR: Missing Yext credentials in .env file")
        return

    # Test business data - using a real business for better results
    test_business = {
        "name": "Joe's Plumbing",
        "address": "1000 Congress Ave",
        "city": "Austin",
        "state": "TX",
        "zip": "78701",
        "phone": "5125551234",
        "countryCode": "US"
    }

    print(f"\nTest Business:")
    for key, value in test_business.items():
        print(f"  {key}: {value}")

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            # Step 1: Initiate scan
            print(f"\n[STEP 1] Initiating scan...")
            print(f"  POST https://api.yext.com/v2/accounts/{YEXT_ACCOUNT_ID}/scan?v=20231201")

            resp = await client.post(
                f"https://api.yext.com/v2/accounts/{YEXT_ACCOUNT_ID}/scan?v=20231201",
                headers={
                    "Api-Key": YEXT_API_KEY,
                    "Content-Type": "application/json"
                },
                json=test_business
            )

            print(f"  Response Status: {resp.status_code}")

            if resp.status_code != 200:
                print(f"  ERROR: {resp.text}")
                return

            data = resp.json()
            job_id = data.get("response", {}).get("jobId")
            sites = data.get("response", {}).get("sites", [])

            print(f"  Job ID: {job_id}")
            print(f"  Sites to scan: {len(sites)}")
            if sites:
                print(f"  Sample sites: {', '.join([s.get('name', 'unknown') for s in sites[:5]])}...")

            if not job_id:
                print("\nERROR: No jobId returned")
                return

            # Step 2: Poll for results
            print(f"\n[STEP 2] Polling for results...")
            max_attempts = 12
            poll_interval = 5

            for attempt in range(max_attempts):
                print(f"\n  Attempt {attempt + 1}/{max_attempts} (waiting {poll_interval}s)...")
                await asyncio.sleep(poll_interval)

                result_resp = await client.get(
                    f"https://api.yext.com/v2/accounts/{YEXT_ACCOUNT_ID}/scan/{job_id}?v=20231201",
                    headers={
                        "Api-Key": YEXT_API_KEY,
                        "Content-Type": "application/json"
                    }
                )

                print(f"  GET /scan/{job_id} - Status: {result_resp.status_code}")

                if result_resp.status_code != 200:
                    print(f"  Response: {result_resp.text[:200]}")
                    continue

                result_data = result_resp.json()
                response = result_data.get("response", {})

                # Print raw response structure for debugging
                print(f"  Response keys: {list(response.keys())}")

                status = response.get("status", "")
                print(f"  Status: {status or 'not specified'}")

                # Check for different completion indicators
                if status == "COMPLETE":
                    print("\n" + "=" * 60)
                    print("SCAN COMPLETE!")
                    print("=" * 60)
                    print(f"\nFull Response:")
                    print(json.dumps(response, indent=2)[:2000])  # Limit output
                    break

                elif "results" in response:
                    results = response.get("results", [])
                    print(f"\n  Results found: {len(results) if isinstance(results, list) else 'N/A'}")
                    print("\n" + "=" * 60)
                    print("RESULTS AVAILABLE!")
                    print("=" * 60)
                    print(f"\nFull Response:")
                    print(json.dumps(response, indent=2)[:2000])
                    break

                elif status in ["PENDING", "RUNNING", "IN_PROGRESS"]:
                    progress = response.get("progress", response.get("percentComplete", "?"))
                    print(f"  Progress: {progress}%")

                elif status == "FAILED":
                    print("\n  SCAN FAILED!")
                    print(f"  Error: {response.get('error', 'Unknown')}")
                    break

                else:
                    # Print whatever we got for debugging
                    print(f"  Raw response (truncated): {json.dumps(response)[:500]}")

            else:
                print("\n" + "=" * 60)
                print("POLLING TIMEOUT - Scan did not complete in 60 seconds")
                print("=" * 60)
                print(f"\nJob ID saved: {job_id}")
                print("You can check results later using:")
                print(f"  GET /v2/accounts/{YEXT_ACCOUNT_ID}/scan/{job_id}")

        except httpx.TimeoutException:
            print("\nERROR: Request timed out")
        except httpx.ConnectError as e:
            print(f"\nERROR: Connection failed - {e}")
        except Exception as e:
            print(f"\nERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_yext_api())
