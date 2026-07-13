# CIBIL API Frontend Integration Documentation

Underwriting Tool Backend

Generated from current repository code on 2026-07-13.

## Source Scope

This document covers the active FastAPI CIBIL routes registered in:

- `routes/cibil_router.py`
- `controller/cibil_controller/cibil_bereau_controller.py`
- `controller/webhook/scoreme_webhook_controller.py`
- `routes/webhook_router.py`
- `middleware/authorization_middleware.py`
- `custom_exceptions/scoreme_exceptions.py`
- `utils/error_codes_utility.py`
- `config/config.py`

This is frontend-integration-centric documentation. It describes what the frontend should send, what it can expect back, and the integration caveats visible in the current backend implementation.

## 1. Base Path And Authentication

Base path:

```text
{API_BASE_URL}/v1/cibil
```

Authentication:

All `/v1/cibil/*` endpoints are protected by the global authorization middleware. The frontend must already be logged in and must send the `access_token` cookie with every request.

Frontend fetch requirement:

```ts
credentials: "include"
```

Example:

```ts
await fetch(`${API_BASE_URL}/v1/cibil/list-reports`, {
  method: "GET",
  credentials: "include",
});
```

Auth failure responses:

```json
{
  "message": "Unauthorized Access"
}
```

```json
{
  "message": "Invalid Token"
}
```

## 2. Response Shapes And Frontend Normalization

Most successful CIBIL responses follow:

```json
{
  "message": "...",
  "data": {},
  "responseCode": "SYS_OK"
}
```

Important current caveat:

Some CIBIL error responses use lowercase `responsecode` instead of `responseCode`. The frontend should normalize both until the backend standardizes this.

Recommended frontend response parser:

```ts
export async function parseApiResponse(response: Response) {
  const body = await response.json().catch(() => ({}));
  const payload = body.detail || body;

  return {
    ok: response.ok,
    status: response.status,
    message: payload.message || "Request failed",
    responseCode: payload.responseCode || payload.responsecode || null,
    data: payload.data ?? null,
    raw: body,
  };
}
```

## 3. Active Endpoint Summary

The current CIBIL router exposes 8 frontend endpoints:

```text
POST /v1/cibil/generate-otp
POST /v1/cibil/validate-otp
POST /v1/cibil/resend-otp
GET  /v1/cibil/webhook-status/{otp_flow_id}
GET  /v1/cibil/list-reports
GET  /v1/cibil/overview/{reference_id}
GET  /v1/cibil/account-summary/{reference_id}
GET  /v1/cibil/payment-history/{reference_id}
GET  /v1/cibil/analysis/{reference_id}
```

Backend callback endpoint:

```text
POST /webhook/credit-bureau
```

The frontend should not call the webhook endpoint. It is public so ScoreMe can call it.

## 4. Recommended Frontend Flow

1. Generate OTP:

```text
POST /v1/cibil/generate-otp
```

Store `data.otp_flow_id`.

2. Validate OTP:

```text
POST /v1/cibil/validate-otp
```

Use the same `otp_flow_id` and the OTP entered by the user.

3. Poll report generation status:

```text
GET /v1/cibil/webhook-status/{otp_flow_id}
```

Expected `data.webhook_status` values:

```text
IN_PROGRESS
SUCCESS
FAILED
```

4. After `SUCCESS`, fetch reports:

```text
GET /v1/cibil/list-reports
```

The current backend does not return `reference_id` from `webhook-status`, `generate-otp`, or `validate-otp`. The frontend needs `reference_id` to call report section APIs, so the current workaround is to call `list-reports` and select the relevant report, usually the newest `cibil_pulled_date`.

Recommended backend improvement:

Return the matching `reference_id` in `GET /v1/cibil/webhook-status/{otp_flow_id}` when status is `SUCCESS`.

5. Fetch report sections:

```text
GET /v1/cibil/overview/{reference_id}
GET /v1/cibil/account-summary/{reference_id}
GET /v1/cibil/payment-history/{reference_id}
GET /v1/cibil/analysis/{reference_id}
```

## 5. Endpoint Details

### 5.1 Generate CIBIL OTP

Endpoint:

```text
POST /v1/cibil/generate-otp
```

Purpose:

Validates basic required fields, calls ScoreMe retail bureau OTP API, stores OTP flow metadata in MongoDB, and returns an internal `otp_flow_id`.

Request body:

```json
{
  "first_name": "Rahul",
  "middle_name": "",
  "last_name": "Sharma",
  "date_of_birth": "1990-01-31",
  "gender": "M",
  "mobile_number": "9876543210",
  "address": "123 Example Street",
  "state": "MH",
  "pincode": "400001",
  "identity": {
    "idType": "PAN",
    "idNumber": "ABCDE1234F"
  }
}
```

Current backend validation:

- All listed keys are required.
- Values are rejected only when `null`.
- Empty strings are currently accepted for this endpoint.
- `middle_name` is required by the current backend even if the person has no middle name.
- Field format validation is delegated mostly to ScoreMe.

Success:

```json
{
  "message": "OTP successfully sent to mobile number.",
  "data": {
    "otp_flow_id": "0190c9c0-0000-6000-8000-000000000000"
  },
  "responseCode": "SOS174"
}
```

Common frontend-handled errors:

```json
{
  "message": "Invalid JSON",
  "data": null,
  "responsecode": "SYS_INPUT_ERR"
}
```

```json
{
  "message": "first_name is required",
  "data": null,
  "responsecode": "SYS_INPUT_ERR"
}
```

ScoreMe error examples:

```text
EPI022  Payload is Incorrect.
EEI2002 Error in Input.
ELN2004 Error in First Name.
ELN2005 Error in Last Name.
EEA2006 Error in Address.
EEG2015 Error in Gender.
EIN2009 Error in Identity Number.
EMN2010 Error in Mobile Number.
EDB2012 Error in Date of Birth format.
ESC2008 Error in State Code.
EEP2007 Error in Pincode.
EMS2013 Mismatch between State Code and Pincode.
EMN2014 Error in Middle Name.
ENR901 Number of requests exceeds the allowed limit.
ELL420 Login attempts limit exceeded.
```

Frontend action:

Store `data.otp_flow_id` in component/session state. Do not persist it longer than needed.

### 5.2 Validate CIBIL OTP

Endpoint:

```text
POST /v1/cibil/validate-otp
```

Purpose:

Validates the OTP against the ScoreMe reference stored for the logged-in user's OTP flow.

Request body:

```json
{
  "otp_flow_id": "0190c9c0-0000-6000-8000-000000000000",
  "otp": "123456"
}
```

Success:

```json
{
  "message": "OTP validated successfully.",
  "data": {
    "otp_flow_id": "0190c9c0-0000-6000-8000-000000000000"
  },
  "responseCode": "SRS016"
}
```

Important behavior:

- If the OTP flow does not belong to the logged-in user, the backend returns 404.
- If OTP is already verified, the backend returns 400 with `ERU061`.
- The backend blocks verification once `verification_attempts >= 3`.
- Report generation is asynchronous. A successful OTP validation does not mean the report is available immediately.

Common errors:

```text
ETP011  Incorrect OTP
SOS176  OTP expired
SOS177  Maximum OTP attempts exceeded
SOS178  OTP not found
ERR541  OTP either expired or not generated yet. Please reinitiate request again
ECB846  Consumer not found in bureau
```

Frontend action:

Start polling `GET /v1/cibil/webhook-status/{otp_flow_id}` after success.

### 5.3 Resend CIBIL OTP

Endpoint:

```text
POST /v1/cibil/resend-otp
```

Purpose:

Requests ScoreMe to resend OTP for an existing OTP flow.

Request body:

```json
{
  "otp_flow_id": "0190c9c0-0000-6000-8000-000000000000"
}
```

Success:

```json
{
  "message": "OTP successfully sent to mobile number.",
  "data": {
    "otp_flow_id": "0190c9c0-0000-6000-8000-000000000000"
  },
  "responseCode": "SOS174"
}
```

Important behavior:

- Resend is blocked after 3 resend attempts.
- Resend is blocked if OTP is already verified.
- On successful resend, verification attempts are reset to 0.

Common errors:

```text
ERU061 OTP has already been verified.
ERU063 Maximum OTP resend attempts exceeded.
ECI419 Credit Bureau service configuration error.
EGD509 Credit Bureau service is currently unavailable.
ERR541 OTP either expired or not generated yet.
```

### 5.4 Get Webhook Status

Endpoint:

```text
GET /v1/cibil/webhook-status/{otp_flow_id}
```

Purpose:

Allows the frontend to poll the asynchronous report generation state after OTP validation.

Success:

```json
{
  "message": "Otp webhook status fetched successdfully",
  "data": {
    "webhook_status": "IN_PROGRESS"
  },
  "responseCode": "SYS_OK"
}
```

Status mapping:

- Stored `PENDING` is returned to the frontend as `IN_PROGRESS`.
- Stored `SUCCESS` is returned as `SUCCESS`.
- Stored `FAILED` is returned as `FAILED`.

Invalid `otp_flow_id`:

```json
{
  "message": "Invalid otp_flow_id",
  "data": null,
  "responseCode": "SYS_INPUT_ERR"
}
```

Recommended polling:

- Poll every 3 to 5 seconds.
- Stop after a frontend timeout, for example 2 to 3 minutes.
- On `SUCCESS`, call `list-reports`.
- On `FAILED`, show a retry/reinitiate message.

### 5.5 List CIBIL Reports

Endpoint:

```text
GET /v1/cibil/list-reports
```

Purpose:

Returns all stored CIBIL reports for the logged-in user with only reference IDs and pull dates.

Success:

```json
{
  "message": "Cibil report list fetched successfully",
  "data": [
    {
      "reference_id": "SCOREME_REFERENCE_ID",
      "cibil_pulled_date": "2026-07-13T10:30:00+00:00"
    }
  ],
  "responseCode": "SYS_OK"
}
```

Frontend action:

Use `reference_id` to fetch report sections. If this call is used immediately after a webhook status success, select the newest report only if users cannot have overlapping CIBIL flows. Otherwise ask backend to return `reference_id` from the status endpoint.

### 5.6 Get Overview

Endpoint:

```text
GET /v1/cibil/overview/{reference_id}
```

Purpose:

Returns high-level bureau analysis and general information.

Success:

```json
{
  "message": "Overview fetched successfully",
  "data": {
    "reference_id": "SCOREME_REFERENCE_ID",
    "cibil_pulled_date": "2026-07-13T10:30:00+00:00",
    "cibil_report": {
      "EquifaxRetail": {
        "BureauAnalysis": {},
        "generalInfo": {}
      }
    }
  },
  "responseCode": "SYS_OK"
}
```

Not found:

```json
{
  "message": "CIBIL report not found",
  "data": null,
  "responseCode": "SYS_NOT_FOUND"
}
```

### 5.7 Get Account Summary

Endpoint:

```text
GET /v1/cibil/account-summary/{reference_id}
```

Success:

```json
{
  "message": "Account summary fetched successfully",
  "data": {
    "reference_id": "SCOREME_REFERENCE_ID",
    "cibil_report": {
      "EquifaxRetail": {
        "accountSummary": {}
      }
    }
  },
  "responseCode": "SYS_OK"
}
```

Not found response code:

```text
CBL_NOT_FOUND
```

### 5.8 Get Payment History

Endpoint:

```text
GET /v1/cibil/payment-history/{reference_id}
```

Success:

```json
{
  "message": "Payment history fetched successfully",
  "data": {
    "reference_id": "SCOREME_REFERENCE_ID",
    "cibil_report": {
      "EquifaxRetail": {
        "activeAccountRepaymentTrack": [],
        "closedAccountRepaymentTrack": []
      }
    }
  },
  "responseCode": "SYS_OK"
}
```

### 5.9 Get Analysis

Endpoint:

```text
GET /v1/cibil/analysis/{reference_id}
```

Success:

```json
{
  "message": "Analysis fetched successfully",
  "data": {
    "reference_id": "SCOREME_REFERENCE_ID",
    "cibil_report": {
      "EquifaxRetail": {
        "ScoremeAnalysis": {}
      }
    }
  },
  "responseCode": "SYS_OK"
}
```

## 6. Frontend Integration Example

```ts
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

async function cibilRequest(path: string, init: RequestInit = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init.headers || {}),
    },
  });

  return parseApiResponse(response);
}

export async function generateCibilOtp(payload: unknown) {
  return cibilRequest("/v1/cibil/generate-otp", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function validateCibilOtp(otpFlowId: string, otp: string) {
  return cibilRequest("/v1/cibil/validate-otp", {
    method: "POST",
    body: JSON.stringify({ otp_flow_id: otpFlowId, otp }),
  });
}

export async function getCibilWebhookStatus(otpFlowId: string) {
  return cibilRequest(`/v1/cibil/webhook-status/${otpFlowId}`, {
    method: "GET",
  });
}

export async function listCibilReports() {
  return cibilRequest("/v1/cibil/list-reports", {
    method: "GET",
  });
}

export async function getCibilOverview(referenceId: string) {
  return cibilRequest(`/v1/cibil/overview/${referenceId}`, {
    method: "GET",
  });
}
```

## 7. Frontend Validation Recommendations

Validate before calling `generate-otp`:

- `first_name`: required, non-empty string.
- `last_name`: required, non-empty string.
- `middle_name`: send empty string if unavailable because backend currently requires the key.
- `date_of_birth`: required, use the exact format expected by ScoreMe for the configured bureau.
- `gender`: required, use the vendor-supported value set.
- `mobile_number`: 10 digits.
- `address`: required, non-empty string.
- `state`: required, use vendor-supported state code.
- `pincode`: 6 digits.
- `identity`: required, keep the shape aligned with ScoreMe's identity payload.

Validate before calling `validate-otp`:

- `otp_flow_id`: required.
- `otp`: required, non-empty string.

## 8. Backend Integration Caveats Visible To Frontend

- `responseCode` casing is inconsistent. Normalize `responseCode || responsecode`.
- `generate-otp` returns only `otp_flow_id`, not `reference_id`.
- `validate-otp` returns only `otp_flow_id`, not `reference_id`.
- `webhook-status` returns only status, not `reference_id`.
- `list-reports` is the only current frontend-accessible way to discover `reference_id`.
- Report section data shape depends on ScoreMe's `EquifaxRetail` JSON and is not strongly modeled by backend response schemas.
- Error response shape from auth middleware is different from controller responses.

