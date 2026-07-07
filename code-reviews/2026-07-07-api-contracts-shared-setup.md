# 🏛️ Council Review Report

**Date**: 2026-07-07
**Change**: api-contracts-shared-setup
**Mode**: diff (working tree changes)
**Branch**: main (2 commits ahead of origin/main)
**Rebase Status**: ✅ Clean
**Verdict**: 🟡 NEEDS_DISCUSSION

---

## 📊 Summary

| Severity | Count |
|----------|-------|
| 🔴 BLOCKER | 2 |
| 🟡 WARNING | 9 |
| 💡 SUGGESTION | 8 |
| ✨ PRAISE | 4 |

**Categories**: architecture (5), security (4), test-gap (8), logic-bug (2)
**Council Members Active**: Senior Python Developer, Security Engineer, QA/Test Engineer
**Consensus Findings**: 3 (flagged independently by 2+ reviewers)

---

## 🔴 Blockers

### 1. Stub routers stack decorators on single function — `app/routes/products.py:9-14`
**Category**: architecture | **Flagged by**: Senior Python Dev
**Detail**: Stacking `@router.get("")` + `@router.get("/{product_id}")` on a single async function creates ambiguous OpenAPI operations. FastAPI generates one `operationId` shared across both routes, which breaks API client code generators and confuses auto-docs. This pattern will need to be undone when implementing real handlers.
**Suggested Fix**:
```python
def _stub_response(msg: str) -> JSONResponse:
    return JSONResponse(status_code=501, content={"error": {"code": "NOT_IMPLEMENTED", "message": msg, "details": None}})

@router.get("")
async def list_products() -> JSONResponse:
    return _stub_response("List products not yet implemented")

@router.get("/{product_id}")
async def get_product(product_id: str) -> JSONResponse:
    return _stub_response("Get product not yet implemented")
```

### 2. `.env` files not in .gitignore — `.gitignore`
**Category**: security | **Flagged by**: Security Engineer
**Detail**: Backend config loads from `.env` (`env_file=".env"` in Settings). If a developer creates `.env` with real `JWT_SECRET`, `GOOGLE_CLIENT_SECRET`, or `ADMIN_API_KEY` values, it could be committed accidentally. No gitignore rule prevents this.
**Suggested Fix**: Add to `.gitignore`:
```
.env
.env.local
.env.*.local
```

---

## 🟡 Warnings

### 3. Timestamp fields typed as `str` instead of `datetime` — `app/models/products.py:20-21` 🤝
**Category**: architecture | **Flagged by**: Senior Python Dev
**Detail**: All `created_at`/`updated_at`/`added_at` fields are `str`. Loses Pydantic validation, timezone awareness, and standardized serialization. Service layer must manually ensure ISO format.
**Suggested Fix**: Use `datetime` — Pydantic serializes to ISO by default.

### 4. CORS allows all methods and headers — `app/main.py:37-38` 🤝
**Category**: security | **Flagged by**: Senior Python Dev, Security Engineer
**Detail**: `allow_methods=["*"]` + `allow_headers=["*"]` is overly permissive. Combined with `allow_credentials=True`, a misconfigured origin list could enable credential theft.
**Suggested Fix**: `allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"]`, `allow_headers=["Content-Type", "Authorization"]`

### 5. Empty secret defaults not validated in production — `app/config.py:25-26`
**Category**: security | **Flagged by**: Security Engineer
**Detail**: `admin_api_key`, `google_client_id`, `google_client_secret` default to empty strings. Only `jwt_secret` is validated for production. Missing secrets cause silent auth failures.

### 6. CreateOrderRequest doesn't reference cart — `app/models/orders.py:42-48`
**Category**: logic-bug | **Flagged by**: Senior Python Dev
**Detail**: Model has customer info but no items. The implicit "convert current session cart" contract isn't documented in the model. Implementers may be confused.

### 7. Missing validation tests for UpdateProductRequest constraints — `tests/test_models.py:73-82` 🤝
**Category**: test-gap | **Flagged by**: Senior Python Dev, QA Engineer
**Detail**: When optional fields *are* provided (e.g., `price=-100`), constraints should still reject them. No test verifies this.

### 8. Missing tests for ProductListResponse, OrderListResponse, CartResponse — `tests/test_models.py`
**Category**: test-gap | **Flagged by**: QA Engineer
**Detail**: Response wrapper models are untested. ProductImportRequest nested validation also untested.

### 9. Missing tests for ProductImportRequest nested validation — `tests/test_models.py`
**Category**: test-gap | **Flagged by**: QA Engineer
**Detail**: Does `ProductImportRequest(products=[CreateProductRequest(price=-1, ...)])` cascade the validation error? No test verifies.

### 10. CORS origins not validated for production — `app/config.py:28`
**Category**: security | **Flagged by**: Security Engineer
**Detail**: `cors_origins` accepts any list from env, including `["*"]`. Combined with `allow_credentials=True`, wildcard origin is a critical CORS misconfiguration.

### 11. OrderResponse exposes customer_email (PII) — `app/models/orders.py:26`
**Category**: security | **Flagged by**: Senior Python Dev
**Detail**: Every order response includes customer email. If access control is missed during implementation, PII leaks. CLAUDE.md mentions GDPR.

---

## 💡 Suggestions

### 12. Product ID has no format validation — `app/models/products.py:9`
Accepts any string including empty. Consider UUID type or regex pattern.

### 13. OrderStatus as StrEnum — `app/models/orders.py:7`
`Literal` works, but `StrEnum` enables methods like `can_transition_to()` for the state machine.

### 14. Missing name min_length test — `tests/test_models.py`
`CreateProductRequest(name="")` should be rejected, but no test covers it.

### 15. days_to_craft accepts negatives — `app/models/products.py:14`
Add `ge=1` constraint.

### 16. ErrorDetail.details is untyped `dict` — `app/models/common.py:11`
Makes frontend error handling inconsistent.

### 17. Missing Secure flag on session cookie — `app/middleware/session.py:36-42`
Cookie sent over HTTP in production without `secure=True`. Should be conditional on environment.

### 18. Mock JWT token visible in production bundle — `frontend/lib/mock-api.ts:241`
`"mock-jwt-token"` will be tree-shaken if dead code, but could confuse security scanners.

### 19. API prefix as constant — `app/main.py:52-56`
String `/v1/` repeated; extract to constant.

---

## ✨ Praise

- **Senior Python Dev**: PaginationParams with `ge=1, le=100` is excellent API hygiene — prevents abuse without silent capping.
- **Senior Python Dev**: Production JWT secret validator (`validate_production_config`) prevents a critical misconfiguration.
- **Security Engineer**: Session cookie uses `httponly=True` + `samesite="lax"` — correct balance for anonymous e-commerce.
- **QA Engineer**: Cart `quantity >= 0` for update vs `quantity >= 1` for add correctly models the "0 = remove" semantic.

---

## 📋 Pre-Review Notes

- **Rebase**: ✅ Clean — 2 commits ahead of origin/main
- **Blast Radius**: 30 files across 4 modules (app/models, app/routes, frontend/lib, tests)
- **Commit Hygiene**: Not yet committed (working tree changes)
- **node_modules**: `frontend/node_modules/` is in the working tree diff — add to `.gitignore` before committing

---

## Architectural Observation

This change establishes the API contract layer cleanly — models are well-structured, the mock/real API switching pattern is sound, and the separation between backend models and frontend types is explicit. The main risk is that the stacked-decorator stub pattern becomes a copy-paste template for real implementations. Fix the router stubs to use one-function-per-route before the next developer sees them.
