"""
Address Verification using Smarty API
Checks if address is residential or commercial using RDI (Residential Delivery Indicator)
"""

import os
import requests
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class AddressVerifier:
    """
    Verify if business address is residential using Smarty API.

    Uses USPS RDI (Residential Delivery Indicator) to determine address type.
    Free tier: 250 lookups/month
    """

    def __init__(self):
        """Initialize with Smarty API credentials from environment"""
        self.auth_id = os.getenv("SMARTY_AUTH_ID", "")
        self.auth_token = os.getenv("SMARTY_AUTH_TOKEN", "")
        self.base_url = "https://us-street.api.smarty.com/street-address"

        if not self.auth_id or not self.auth_token:
            logger.warning("Smarty API credentials not found. Using mock mode.")
            self.mock_mode = True
        else:
            self.mock_mode = False
            logger.info("Smarty API initialized successfully")

    def verify_address(
        self,
        address: str,
        city: str,
        state: str,
        zip_code: str
    ) -> Dict:
        """
        Verify if address is residential or commercial.

        Returns:
            {
                "is_residential": bool,
                "address_type": "residential" | "commercial" | "unknown",
                "verified": bool,
                "formatted_address": str (optional),
                "error": str (optional)
            }
        """
        try:
            # Mock mode for testing without API key
            if self.mock_mode:
                return self._mock_verification(address, city, state, zip_code)

            # Make Smarty API request
            params = {
                "auth-id": self.auth_id,
                "auth-token": self.auth_token,
                "street": address,
                "city": city,
                "state": state,
                "zipcode": zip_code,
                "match": "invalid"  # Return best match
            }

            response = requests.get(self.base_url, params=params, timeout=10)

            # Handle non-200 responses
            if response.status_code != 200:
                logger.error(f"Smarty API error: {response.status_code} - {response.text}")
                return {
                    "is_residential": False,
                    "address_type": "unknown",
                    "verified": False,
                    "error": f"API error: {response.status_code}"
                }

            results = response.json()

            # No results = invalid address
            if not results or len(results) == 0:
                logger.warning(f"No results for address: {address}, {city}, {state}")
                return {
                    "is_residential": False,
                    "address_type": "unknown",
                    "verified": False,
                    "error": "Address not found"
                }

            # Parse first result
            result = results[0]
            metadata = result.get("metadata", {})
            rdi = metadata.get("rdi")  # R = Residential, C = Commercial, "" = Unknown

            # Get formatted address
            delivery_line_1 = result.get("delivery_line_1", "")
            last_line = result.get("last_line", "")
            formatted_address = f"{delivery_line_1}, {last_line}" if delivery_line_1 and last_line else None

            # Determine address type
            is_residential = rdi == "Residential"
            address_type = "residential" if rdi == "Residential" else "commercial" if rdi == "Commercial" else "unknown"

            logger.info(f"Address verified: {formatted_address} - Type: {address_type}")

            return {
                "is_residential": is_residential,
                "address_type": address_type,
                "verified": True,
                "formatted_address": formatted_address
            }

        except requests.exceptions.Timeout:
            logger.error("Smarty API timeout")
            return {
                "is_residential": False,
                "address_type": "unknown",
                "verified": False,
                "error": "API timeout"
            }
        except Exception as e:
            logger.error(f"Verification error: {str(e)}")
            return {
                "is_residential": False,
                "address_type": "unknown",
                "verified": False,
                "error": str(e)
            }

    def _mock_verification(self, address: str, city: str, state: str, zip_code: str) -> Dict:
        """
        Mock verification for testing without API key.

        Simple heuristics:
        - Suite/Unit/Apt = Residential
        - Office/Building/Plaza = Commercial
        - Default = Unknown
        """
        address_lower = address.lower()

        # Residential indicators
        residential_keywords = ["apt", "apartment", "unit", "suite #", "#", "home"]

        # Commercial indicators
        commercial_keywords = ["office", "building", "bldg", "plaza", "center", "centre", "suite"]

        is_residential = any(kw in address_lower for kw in residential_keywords)
        is_commercial = any(kw in address_lower for kw in commercial_keywords)

        if is_residential and not is_commercial:
            address_type = "residential"
            is_res = True
        elif is_commercial and not is_residential:
            address_type = "commercial"
            is_res = False
        else:
            # Default to unknown
            address_type = "unknown"
            is_res = False

        logger.info(f"Mock verification: {address} - Type: {address_type}")

        return {
            "is_residential": is_res,
            "address_type": address_type,
            "verified": False,  # Mock = not truly verified
            "formatted_address": f"{address}, {city}, {state} {zip_code}",
            "error": "Mock mode - no API key configured"
        }
