"""
Rise Local MCP Server
Exposes 6 microservices as MCP tools for Zapier AI and Claude agents
"""

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import httpx
import asyncio
from typing import Any, Dict, Optional
import os
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RiseLocalMCP:
    """
    MCP Server for Rise Local Lead Creation Pipeline
    Provides access to 6 intelligence microservices
    """

    def __init__(self):
        self.service_urls = {
            "tdlr": os.getenv("TDLR_SCRAPER_URL", "http://localhost:8001"),
            "bbb": os.getenv("BBB_SCRAPER_URL", "http://localhost:8002"),
            "pagespeed": os.getenv("PAGESPEED_API_URL", "http://localhost:8003"),
            "screenshot": os.getenv("SCREENSHOT_SERVICE_URL", "http://localhost:8004"),
            "owner": os.getenv("OWNER_EXTRACTOR_URL", "http://localhost:8005"),
            "address": os.getenv("ADDRESS_VERIFIER_URL", "http://localhost:8006"),
        }

        # HTTP client with retry logic
        self.client = httpx.AsyncClient(
            timeout=90.0,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        )

        logger.info(f"Initialized RiseLocalMCP with service URLs: {self.service_urls}")

    async def search_tdlr_license(self, **kwargs) -> Dict[str, Any]:
        """
        Search Texas TDLR for electrical contractor license.
        Uses waterfall method: license number → owner name → business name
        """
        logger.info(f"TDLR search requested with params: {kwargs}")

        try:
            response = await self.client.post(
                f"{self.service_urls['tdlr']}/search/waterfall",
                json=kwargs,
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()

            logger.info(f"TDLR search completed: {data.get('license_status', 'Unknown')}")
            return data

        except httpx.TimeoutException:
            logger.error("TDLR service timeout")
            return {
                "error": "TDLR service timeout after 60s",
                "license_status": "Unknown",
                "service": "tdlr"
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"TDLR HTTP error: {e.response.status_code}")
            return {
                "error": f"HTTP {e.response.status_code}",
                "license_status": "Error",
                "service": "tdlr"
            }
        except Exception as e:
            logger.error(f"TDLR unexpected error: {str(e)}")
            return {
                "error": str(e),
                "license_status": "Error",
                "service": "tdlr"
            }

    async def search_bbb_reputation(
        self,
        business_name: str,
        city: str,
        state: str,
        google_rating: float,
        lead_id: str
    ) -> Dict[str, Any]:
        """
        Search Better Business Bureau for reputation data.
        Calculates reputation gap between Google and BBB ratings.
        """
        logger.info(f"BBB search for {business_name} in {city}, {state}")

        try:
            response = await self.client.post(
                f"{self.service_urls['bbb']}/search",
                json={
                    "business_name": business_name,
                    "city": city,
                    "state": state,
                    "google_rating": google_rating,
                    "lead_id": lead_id
                },
                timeout=45.0
            )
            response.raise_for_status()
            data = response.json()

            logger.info(f"BBB search completed: Rating={data.get('bbb_rating', 'NR')}, Gap={data.get('reputation_gap', 0)}")
            return data

        except Exception as e:
            logger.error(f"BBB error: {str(e)}")
            return {
                "error": str(e),
                "bbb_rating": "NR",
                "bbb_accredited": False,
                "complaints_total": 0,
                "reputation_gap": 0.0,
                "service": "bbb"
            }

    async def analyze_pagespeed(
        self,
        url: str,
        strategy: str = "mobile",
        lead_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze website performance using Google PageSpeed Insights.
        Returns Core Web Vitals, performance score, SEO score.
        """
        logger.info(f"PageSpeed analysis for {url} (strategy: {strategy})")

        try:
            response = await self.client.post(
                f"{self.service_urls['pagespeed']}/analyze",
                json={
                    "url": url,
                    "strategy": strategy,
                    "lead_id": lead_id
                },
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()

            logger.info(f"PageSpeed completed: Performance={data.get('performance_score', 0)}, Mobile={data.get('mobile_score', 0)}")
            return data

        except Exception as e:
            logger.error(f"PageSpeed error: {str(e)}")
            return {
                "error": str(e),
                "performance_score": 0,
                "mobile_score": 0,
                "seo_score": 0,
                "service": "pagespeed"
            }

    async def capture_screenshot_and_analyze(
        self,
        url: str,
        include_mobile: bool = True,
        lead_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Capture website screenshots and analyze visual quality using Gemini Vision.
        Also performs FREE tech stack detection (analytics, CRM, chat widgets).
        """
        logger.info(f"Screenshot + analysis for {url}")

        try:
            response = await self.client.post(
                f"{self.service_urls['screenshot']}/analyze",
                json={
                    "url": url,
                    "include_mobile": include_mobile,
                    "lead_id": lead_id
                },
                timeout=90.0
            )
            response.raise_for_status()
            data = response.json()

            logger.info(f"Screenshot completed: Visual={data.get('visual_score', 0)}, Era={data.get('design_era', 'Unknown')}")
            return data

        except Exception as e:
            logger.error(f"Screenshot error: {str(e)}")
            return {
                "error": str(e),
                "visual_score": 0,
                "design_era": "Unknown",
                "mobile_responsive": False,
                "service": "screenshot"
            }

    async def extract_owner_info(
        self,
        url: str,
        lead_id: str
    ) -> Dict[str, Any]:
        """
        Extract owner name, email, phone, and license number from website.
        Uses Claude Vision for intelligent parsing.
        CRITICAL: This must run BEFORE TDLR search for waterfall to work.
        """
        logger.info(f"Owner extraction for {url}")

        try:
            response = await self.client.post(
                f"{self.service_urls['owner']}/extract-owner",
                json={
                    "url": url,
                    "lead_id": lead_id
                },
                timeout=90.0
            )
            response.raise_for_status()
            data = response.json()

            logger.info(f"Owner extraction completed: {data.get('owner_full_name', 'Not found')}, Confidence={data.get('confidence', 'low')}")
            return data

        except Exception as e:
            logger.error(f"Owner extraction error: {str(e)}")
            return {
                "error": str(e),
                "owner_first_name": None,
                "owner_last_name": None,
                "confidence": "low",
                "service": "owner"
            }

    async def verify_address(
        self,
        address: str,
        city: str,
        state: str,
        zip_code: str,
        lead_id: str
    ) -> Dict[str, Any]:
        """
        Verify if business address is residential or commercial.
        Uses Smarty API with USPS RDI (Residential Delivery Indicator).
        """
        logger.info(f"Address verification for {address}, {city}, {state}")

        try:
            response = await self.client.post(
                f"{self.service_urls['address']}/verify",
                json={
                    "address": address,
                    "city": city,
                    "state": state,
                    "zip_code": zip_code,
                    "lead_id": lead_id
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            logger.info(f"Address verification completed: Type={data.get('address_type', 'unknown')}")
            return data

        except Exception as e:
            logger.error(f"Address verification error: {str(e)}")
            return {
                "error": str(e),
                "is_residential": None,
                "address_type": "unknown",
                "verified": False,
                "service": "address"
            }

    async def health_check(self) -> Dict[str, Any]:
        """
        Check health status of all 6 microservices.
        Returns status for each service.
        """
        logger.info("Health check requested for all services")

        async def check_service(name: str, url: str) -> Dict[str, Any]:
            try:
                response = await self.client.get(f"{url}/health", timeout=5.0)
                return {
                    "service": name,
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time_ms": response.elapsed.total_seconds() * 1000
                }
            except Exception as e:
                return {
                    "service": name,
                    "status": "down",
                    "error": str(e)
                }

        # Check all services in parallel
        tasks = [
            check_service(name, url)
            for name, url in self.service_urls.items()
        ]

        results = await asyncio.gather(*tasks)

        overall_status = "healthy" if all(r["status"] == "healthy" for r in results) else "degraded"

        return {
            "overall_status": overall_status,
            "services": results,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def close(self):
        """Close HTTP client connections"""
        await self.client.aclose()
        logger.info("MCP server connections closed")


async def main():
    """
    Main entry point for MCP server.
    Registers all tools and starts stdio server.
    """

    logger.info("Starting Rise Local MCP Server...")

    # Initialize service wrapper
    mcp = RiseLocalMCP()

    # Create MCP server
    server = Server("rise-local-mcp")

    logger.info("Registering MCP tools...")

    # Register tools
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List all available tools"""
        return [
            Tool(
                name="search_tdlr_license",
                description="Search Texas TDLR for electrical contractor license using waterfall method (license number, owner name, business name)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "license_number": {
                            "type": "string",
                            "description": "TECL license number if known"
                        },
                        "owner_first_name": {
                            "type": "string",
                            "description": "Owner first name for waterfall search"
                        },
                        "owner_last_name": {
                            "type": "string",
                            "description": "Owner last name for waterfall search"
                        },
                        "business_name": {
                            "type": "string",
                            "description": "Business name to search"
                        },
                        "city": {
                            "type": "string",
                            "description": "City location"
                        },
                        "lead_id": {
                            "type": "string",
                            "description": "UUID of lead being processed"
                        }
                    },
                    "required": ["lead_id"]
                }
            ),
            Tool(
                name="search_bbb_reputation",
                description="Search Better Business Bureau for reputation data and calculate reputation gap vs Google rating",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "business_name": {
                            "type": "string",
                            "description": "Business name to search"
                        },
                        "city": {
                            "type": "string",
                            "description": "City location"
                        },
                        "state": {
                            "type": "string",
                            "description": "State abbreviation (e.g., TX)"
                        },
                        "google_rating": {
                            "type": "number",
                            "description": "Google rating (0.0-5.0) for gap calculation"
                        },
                        "lead_id": {
                            "type": "string",
                            "description": "UUID of lead being processed"
                        }
                    },
                    "required": ["business_name", "city", "state", "google_rating", "lead_id"]
                }
            ),
            Tool(
                name="analyze_pagespeed",
                description="Analyze website performance using Google PageSpeed Insights (Core Web Vitals, mobile score, SEO)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Website URL to analyze"
                        },
                        "strategy": {
                            "type": "string",
                            "enum": ["mobile", "desktop"],
                            "default": "mobile",
                            "description": "Analysis strategy"
                        },
                        "lead_id": {
                            "type": "string",
                            "description": "UUID of lead being processed"
                        }
                    },
                    "required": ["url", "lead_id"]
                }
            ),
            Tool(
                name="capture_screenshot_and_analyze",
                description="Capture website screenshots (desktop + mobile) and analyze visual quality, design era, tech stack using Gemini Vision",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Website URL to capture and analyze"
                        },
                        "include_mobile": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include mobile viewport screenshot"
                        },
                        "lead_id": {
                            "type": "string",
                            "description": "UUID of lead being processed"
                        }
                    },
                    "required": ["url", "lead_id"]
                }
            ),
            Tool(
                name="extract_owner_info",
                description="Extract owner name, email, phone, and license number from website using Claude Vision (CRITICAL for TDLR waterfall)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Website URL to extract owner info from"
                        },
                        "lead_id": {
                            "type": "string",
                            "description": "UUID of lead being processed"
                        }
                    },
                    "required": ["url", "lead_id"]
                }
            ),
            Tool(
                name="verify_address",
                description="Verify if business address is residential or commercial using Smarty API (USPS RDI)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "address": {
                            "type": "string",
                            "description": "Street address"
                        },
                        "city": {
                            "type": "string",
                            "description": "City"
                        },
                        "state": {
                            "type": "string",
                            "description": "State abbreviation"
                        },
                        "zip_code": {
                            "type": "string",
                            "description": "ZIP code"
                        },
                        "lead_id": {
                            "type": "string",
                            "description": "UUID of lead being processed"
                        }
                    },
                    "required": ["address", "city", "state", "lead_id"]
                }
            ),
            Tool(
                name="health_check",
                description="Check health status of all 6 microservices",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """Execute tool by name"""

        logger.info(f"Tool call: {name} with args: {json.dumps(arguments, default=str)}")

        try:
            if name == "search_tdlr_license":
                result = await mcp.search_tdlr_license(**arguments)
            elif name == "search_bbb_reputation":
                result = await mcp.search_bbb_reputation(**arguments)
            elif name == "analyze_pagespeed":
                result = await mcp.analyze_pagespeed(**arguments)
            elif name == "capture_screenshot_and_analyze":
                result = await mcp.capture_screenshot_and_analyze(**arguments)
            elif name == "extract_owner_info":
                result = await mcp.extract_owner_info(**arguments)
            elif name == "verify_address":
                result = await mcp.verify_address(**arguments)
            elif name == "health_check":
                result = await mcp.health_check()
            else:
                raise ValueError(f"Unknown tool: {name}")

            # Format result as JSON text
            result_text = json.dumps(result, indent=2, default=str)
            logger.info(f"Tool {name} completed successfully")

            return [TextContent(type="text", text=result_text)]

        except Exception as e:
            error_msg = f"Error executing {name}: {str(e)}"
            logger.error(error_msg)
            return [TextContent(
                type="text",
                text=json.dumps({"error": error_msg, "tool": name}, indent=2)
            )]

    # Run server
    logger.info("MCP server ready, starting stdio server...")

    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    finally:
        await mcp.close()
        logger.info("MCP server shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
