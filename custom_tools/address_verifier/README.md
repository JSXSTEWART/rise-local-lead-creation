# Address Verifier - Phase 2F

Verifies if a business address is residential or commercial using Smarty API's RDI (Residential Delivery Indicator).

## Purpose

Identifies residential addresses for **DealMachine skip trace eligibility**. If a business operates from a residential address, you can use DealMachine's unlimited contact lookup instead of paid skip trace services.

## API Endpoint

### POST /verify

**Request:**
```json
{
  "address": "123 Main St",
  "city": "Austin",
  "state": "TX",
  "zip_code": "78701",
  "lead_id": "optional-uuid"
}
```

**Response:**
```json
{
  "is_residential": true,
  "address_type": "residential",
  "verified": true,
  "formatted_address": "123 Main St, Austin TX 78701",
  "lead_id": "optional-uuid",
  "error": null
}
```

### GET /health

Health check endpoint.

## Configuration

### Environment Variables

- `SMARTY_AUTH_ID`: Smarty API Auth ID (required)
- `SMARTY_AUTH_TOKEN`: Smarty API Auth Token (required)

### Getting Smarty API Keys

1. Sign up at https://www.smarty.com/
2. Free tier: 250 lookups/month (no credit card)
3. Go to API Keys section
4. Copy Auth ID and Auth Token
5. Add to `.env` file

## Mock Mode

If no API credentials are provided, the service runs in **mock mode** with simple heuristics:
- Detects keywords like "apt", "unit", "suite #" → residential
- Detects "office", "building", "plaza" → commercial
- Default → unknown

**Note:** Mock mode is for testing only. Use real API for production.

## Docker

```bash
# Build
docker build -t address-verifier .

# Run
docker run -p 8006:8006 \
  -e SMARTY_AUTH_ID=your_auth_id \
  -e SMARTY_AUTH_TOKEN=your_auth_token \
  address-verifier
```

## Integration

This service is called in **Phase 2F** of the pipeline, after Phase 2D (TDLR) and before Phase 3 (Pain Scoring).

**Pipeline Flow:**
```
Phase 2D: TDLR → Get owner_name
Phase 2F: Address Verifier → Get is_residential
Phase 5: Skip Trace → Use DealMachine if is_residential=true
```

## Supabase Schema

Add to `leads` table:
```sql
-- Phase 2F: Address Verification
is_residential        BOOLEAN,
address_type          TEXT,           -- residential, commercial, unknown
address_verified      BOOLEAN,
formatted_address     TEXT,
address_verified_at   TIMESTAMPTZ
```

## Cost

- **Free Tier:** 250 lookups/month (Smarty)
- **Paid:** Starting at $0.005/lookup for higher volumes
- **DealMachine Savings:** Unlimited skip trace vs $0.10-0.15/lookup with BatchLeads

## Testing

```bash
# Test health
curl http://localhost:8006/health

# Test verification
curl -X POST http://localhost:8006/verify \
  -H "Content-Type: application/json" \
  -d '{
    "address": "123 Main St",
    "city": "Austin",
    "state": "TX",
    "zip_code": "78701"
  }'
```

## Phase 2F Pain Scoring

**No pain points added** - this is purely for skip trace optimization, not qualification scoring.

## References

- [Smarty API Docs](https://www.smarty.com/docs)
- [Smarty RDI](https://www.smarty.com/articles/what-is-rdi)
- [DealMachine Skip Trace](https://www.dealmachine.com/skip-tracing)
