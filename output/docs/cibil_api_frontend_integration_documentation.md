# CIBIL API Frontend Integration Documentation

Underwriting Tool Backend

Generated from current repository code on 2026-07-13.

## Source Scope

This document describes the active CIBIL frontend API implemented in:

- `routes/cibil_router.py`
- `controller/cibil_controller/cibil_bereau_controller.py`
- `routes/webhook_router.py`
- `controller/webhook/scoreme_webhook_controller.py`
- `middleware/authorization_middleware.py`
- `custom_exceptions/scoreme_exceptions.py`
- `utils/error_codes_utility.py`
- `config/config.py`

The backend routes are named CIBIL, but the current vendor payload sends `bureauName: ["equifax"]`.

## 1. Base URL And Authentication

Base path:

```text
{API_BASE_URL}/v1/cibil
```

All `/v1/cibil/*` endpoints are protected by the global authorization middleware. The frontend must send the login cookie named `access_token`.

Use `credentials: "include"` in browser requests:

```ts
await fetch(`${API_BASE_URL}/v1/cibil/list-reports`, {
  method: "GET",
  credentials: "include",
});
```

Authentication failure responses come from middleware and do not use the normal API envelope:

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

## 2. Endpoint Summary

Frontend endpoints:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/v1/cibil/generate-otp` | Start bureau OTP flow |
| POST | `/v1/cibil/validate-otp` | Validate user-entered OTP |
| POST | `/v1/cibil/resend-otp` | Resend OTP for an existing flow |
| GET | `/v1/cibil/webhook-status/{otp_flow_id}` | Poll asynchronous report status |
| GET | `/v1/cibil/list-reports` | List stored reports for logged-in user |
| GET | `/v1/cibil/overview/{reference_id}` | Get overview/general info section |
| GET | `/v1/cibil/account-summary/{reference_id}` | Get account summary section |
| GET | `/v1/cibil/payment-history/{reference_id}` | Get repayment history section |
| GET | `/v1/cibil/analysis/{reference_id}` | Get ScoreMe analysis section |

Backend-only callback endpoint:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/webhook/credit-bureau` | ScoreMe callback for report generation |

The frontend should not call `/webhook/credit-bureau`.

## 3. Response Envelope

Most successful CIBIL responses follow this shape:

```json
{
  "message": "Human readable message",
  "data": {},
  "responseCode": "SYS_OK"
}
```

Current implementation caveat:

Some error responses use lowercase `responsecode` instead of `responseCode`. The frontend should normalize both until the backend standardizes the casing.

Recommended response parser:

```ts
export type ApiResult<T> = {
  ok: boolean;
  status: number;
  message: string;
  responseCode: string | null;
  data: T | null;
  raw: unknown;
};

export async function parseApiResponse<T>(response: Response): Promise<ApiResult<T>> {
  const body = await response.json().catch(() => ({}));
  const payload = (body as any).detail || body;

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

## 4. Recommended Frontend Flow

1. Collect applicant details and call `POST /v1/cibil/generate-otp`.
2. Store `data.otp_flow_id` in component/session state.
3. Ask the user to enter the OTP.
4. Call `POST /v1/cibil/validate-otp`.
5. After successful validation, poll `GET /v1/cibil/webhook-status/{otp_flow_id}`.
6. Continue polling while `data.webhook_status` is `IN_PROGRESS`.
7. On `SUCCESS`, call `GET /v1/cibil/list-reports`.
8. Select the relevant `reference_id`, usually the newest report if only one CIBIL flow is active.
9. Call section APIs using the selected `reference_id`.

Important: the current backend does not return `reference_id` from `generate-otp`, `validate-otp`, or `webhook-status`. The only frontend-accessible way to discover it is `list-reports`.

Recommended polling behavior:

- Poll every 3 to 5 seconds.
- Stop after a UI timeout, for example 2 to 3 minutes.
- On `FAILED`, show a retry/reinitiate message.
- On auth failure, redirect to login or refresh session.

## 5. Endpoint Details

### 5.1 Generate CIBIL OTP

```text
POST /v1/cibil/generate-otp
```

Starts a ScoreMe credit bureau OTP flow and stores an internal OTP manager document.

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

| Field | Required | Current validation |
| --- | --- | --- |
| `first_name` | Yes | Key must exist and value must not be `null` |
| `middle_name` | Yes | Key must exist and value must not be `null`; send `""` if not available |
| `last_name` | Yes | Key must exist and value must not be `null` |
| `date_of_birth` | Yes | Key must exist and value must not be `null` |
| `gender` | Yes | Key must exist and value must not be `null` |
| `mobile_number` | Yes | Key must exist and value must not be `null` |
| `address` | Yes | Key must exist and value must not be `null` |
| `state` | Yes | Key must exist and value must not be `null` |
| `pincode` | Yes | Key must exist and value must not be `null` |
| `identity` | Yes | Key must exist and value must not be `null` |

Empty strings are currently accepted by the backend for this endpoint, but the frontend should still validate user input before submission.

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

Common validation errors:

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

```json
{
  "message": "first_name value is empty",
  "data": null,
  "responsecode": "SYS_INPUT_ERR"
}
```

Vendor error codes handled by backend:

| Code | Meaning | HTTP status |
| --- | --- | --- |
| `EPI022` | Payload is incorrect | 400 |
| `EEI2002` | Error in input | 400 |
| `ELN2004` | Error in first name | 400 |
| `ELN2005` | Error in last name | 400 |
| `EEA2006` | Error in address | 400 |
| `EBF017` | Blank input field | 400 |
| `EIB721` | Incorrect bureau type | 400 |
| `ENR901` | Request limit exceeded | 429 |
| `EEG2015` | Error in gender | 400 |
| `EIN2009` | Error in identity number | 400 |
| `EMN2010` | Error in mobile number | 400 |
| `EDB2012` | Error in date of birth format | 400 |
| `ESC2008` | Error in state code | 400 |
| `EEP2007` | Error in pincode | 400 |
| `EMS2013` | State code and pincode mismatch | 400 |
| `EMN2014` | Error in middle name | 400 |
| `ELL420` | Login attempts limit exceeded | 429 |

Frontend action:

Store `data.otp_flow_id` and show OTP entry UI.

### 5.2 Validate CIBIL OTP

```text
POST /v1/cibil/validate-otp
```

Validates the OTP using the ScoreMe `reference_id` stored for the logged-in user's OTP flow.

Request body:

```json
{
  "otp_flow_id": "0190c9c0-0000-6000-8000-000000000000",
  "otp": "123456"
}
```

Current backend validation:

| Field | Required | Current validation |
| --- | --- | --- |
| `otp_flow_id` | Yes | Must exist and must not be blank |
| `otp` | Yes | Must exist and must not be blank |

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

- If the OTP flow does not exist for the logged-in user, backend returns 404.
- If OTP is already verified, backend returns 400 with `ERU061`.
- Backend blocks verification when stored `verification_attempts >= 3`.
- Successful validation only means the report request moved forward. The report is delivered later through webhook.

Common frontend-handled errors:

```json
{
  "message": "OTP flow not found.",
  "data": null,
  "responseCode": "SYS_INPUT_ERR"
}
```

```json
{
  "message": "OTP has already been verified.",
  "data": null,
  "responseCode": "ERU061"
}
```

```json
{
  "message": "Maximum OTP verification attempts exceeded.",
  "data": null,
  "responseCode": "SYS_INPUT_ERR"
}
```

Vendor error codes handled by backend:

| Code | Meaning | HTTP status |
| --- | --- | --- |
| `ETP011` | Incorrect OTP | 400 |
| `SOS176` | OTP expired | 400 |
| `SOS177` | Maximum OTP attempts exceeded | 429 |
| `SOS178` | OTP not found | 404 |
| `ERR541` | OTP expired or not generated | 400 |
| `ECB846` | Consumer not found in bureau | 400 |

Frontend action:

On success, start polling `GET /v1/cibil/webhook-status/{otp_flow_id}`.

### 5.3 Resend CIBIL OTP

```text
POST /v1/cibil/resend-otp
```

Requests a new OTP for an existing OTP flow.

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

- Resend is blocked when the OTP is already verified.
- Resend is blocked after 3 resend attempts.
- On successful resend, `verification_attempts` is reset to `0`.

Common errors:

| Code | Meaning | HTTP status |
| --- | --- | --- |
| `ERU061` | OTP has already been verified | 400 |
| `ERU063` | Maximum resend attempts exceeded | 429 |
| `ECI419` | Credit bureau service configuration error | 500 |
| `EGD509` | Credit bureau service unavailable | 502 |
| `ERR541` | OTP expired or not generated | 400 |

Frontend action:

Keep the same `otp_flow_id`; do not call `generate-otp` again unless the user restarts the full flow.

### 5.4 Get Webhook Status

```text
GET /v1/cibil/webhook-status/{otp_flow_id}
```

Polls asynchronous report generation state for the logged-in user's OTP flow.

Path parameter:

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `otp_flow_id` | string | Yes | Internal flow ID returned by `generate-otp` |

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

Possible `data.webhook_status` values:

| Value | Meaning | Frontend action |
| --- | --- | --- |
| `IN_PROGRESS` | Backend is waiting for ScoreMe webhook or report fetch is not finished | Keep polling |
| `SUCCESS` | Report was saved in backend | Call `list-reports`, then section APIs |
| `FAILED` | ScoreMe webhook reported failure or was ignored as failed | Stop polling and show retry/reinitiate UI |

Invalid flow:

```json
{
  "message": "Invalid otp_flow_id",
  "data": null,
  "responseCode": "SYS_INPUT_ERR"
}
```

Current limitation:

This endpoint does not return `reference_id`, even when status is `SUCCESS`.

### 5.5 List CIBIL Reports

```text
GET /v1/cibil/list-reports
```

Returns the logged-in user's saved report references.

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

Use `reference_id` to call report section APIs. If this call is used immediately after status `SUCCESS`, choose the newest `cibil_pulled_date` only when the user cannot have multiple active CIBIL flows.

Current limitation:

The endpoint has no pagination or sorting parameters. The backend returns every report for the user.

### 5.6 Get Overview

```text
GET /v1/cibil/overview/{reference_id}
```

Returns high-level bureau analysis and general information.

Path parameter:

| Parameter | Type | Required |
| --- | --- | --- |
| `reference_id` | string | Yes |

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

```text
GET /v1/cibil/account-summary/{reference_id}
```

Returns account summary from the saved bureau report.

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

Not found:

```json
{
  "message": "CIBIL report not found",
  "data": null,
  "responseCode": "CBL_NOT_FOUND"
}
```

### 5.8 Get Payment History

```text
GET /v1/cibil/payment-history/{reference_id}
```

Returns active and closed account repayment track sections.

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

Not found:

```json
{
  "message": "CIBIL report not found",
  "data": null,
  "responseCode": "CBL_NOT_FOUND"
}
```

### 5.9 Get Analysis

```text
GET /v1/cibil/analysis/{reference_id}
```

Returns ScoreMe analysis from the saved bureau report.

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

Not found:

```json
{
  "message": "CIBIL report not found",
  "data": null,
  "responseCode": "CBL_NOT_FOUND"
}
```

## 6. Frontend TypeScript Client Example

```ts
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

type GenerateCibilOtpPayload = {
  first_name: string;
  middle_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  mobile_number: string;
  address: string;
  state: string;
  pincode: string;
  identity: {
    idType: string;
    idNumber: string;
  };
};

type OtpFlowResponse = {
  otp_flow_id: string;
};

type WebhookStatusResponse = {
  webhook_status: "IN_PROGRESS" | "SUCCESS" | "FAILED";
};

type CibilReportListItem = {
  reference_id: string;
  cibil_pulled_date: string;
};

async function cibilRequest<T>(path: string, init: RequestInit = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(init.headers || {}),
    },
  });

  return parseApiResponse<T>(response);
}

export function generateCibilOtp(payload: GenerateCibilOtpPayload) {
  return cibilRequest<OtpFlowResponse>("/v1/cibil/generate-otp", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function validateCibilOtp(otpFlowId: string, otp: string) {
  return cibilRequest<OtpFlowResponse>("/v1/cibil/validate-otp", {
    method: "POST",
    body: JSON.stringify({ otp_flow_id: otpFlowId, otp }),
  });
}

export function resendCibilOtp(otpFlowId: string) {
  return cibilRequest<OtpFlowResponse>("/v1/cibil/resend-otp", {
    method: "POST",
    body: JSON.stringify({ otp_flow_id: otpFlowId }),
  });
}

export function getCibilWebhookStatus(otpFlowId: string) {
  return cibilRequest<WebhookStatusResponse>(
    `/v1/cibil/webhook-status/${encodeURIComponent(otpFlowId)}`,
    { method: "GET" },
  );
}

export function listCibilReports() {
  return cibilRequest<CibilReportListItem[]>("/v1/cibil/list-reports", {
    method: "GET",
  });
}

export function getCibilOverview(referenceId: string) {
  return cibilRequest<unknown>(
    `/v1/cibil/overview/${encodeURIComponent(referenceId)}`,
    { method: "GET" },
  );
}

export function getCibilAccountSummary(referenceId: string) {
  return cibilRequest<unknown>(
    `/v1/cibil/account-summary/${encodeURIComponent(referenceId)}`,
    { method: "GET" },
  );
}

export function getCibilPaymentHistory(referenceId: string) {
  return cibilRequest<unknown>(
    `/v1/cibil/payment-history/${encodeURIComponent(referenceId)}`,
    { method: "GET" },
  );
}

export function getCibilAnalysis(referenceId: string) {
  return cibilRequest<unknown>(
    `/v1/cibil/analysis/${encodeURIComponent(referenceId)}`,
    { method: "GET" },
  );
}
```

Polling helper example:

```ts
export async function waitForCibilReport(
  otpFlowId: string,
  options = { intervalMs: 4000, timeoutMs: 180000 },
) {
  const startedAt = Date.now();

  while (Date.now() - startedAt < options.timeoutMs) {
    const result = await getCibilWebhookStatus(otpFlowId);

    if (!result.ok) {
      throw new Error(result.message);
    }

    if (result.data?.webhook_status === "SUCCESS") {
      return result.data;
    }

    if (result.data?.webhook_status === "FAILED") {
      throw new Error("CIBIL report generation failed");
    }

    await new Promise((resolve) => setTimeout(resolve, options.intervalMs));
  }

  throw new Error("CIBIL report generation timed out");
}
```

## 7. UI State Recommendations

Suggested states:

| UI state | Trigger |
| --- | --- |
| `idle` | User has not submitted applicant details |
| `generating_otp` | `generate-otp` request is in progress |
| `otp_sent` | `generate-otp` succeeded |
| `validating_otp` | `validate-otp` request is in progress |
| `waiting_for_report` | OTP validated; webhook status polling is active |
| `report_ready` | Webhook status returned `SUCCESS` and report list/section data is loaded |
| `failed` | Any terminal API/vendor failure |

Frontend validation before `generate-otp`:

- `first_name`: required, non-empty string.
- `middle_name`: send empty string if unavailable.
- `last_name`: required, non-empty string.
- `date_of_birth`: required; use the vendor-supported format.
- `gender`: required; use the vendor-supported value set.
- `mobile_number`: 10 digits.
- `address`: required, non-empty string.
- `state`: required vendor-supported state code.
- `pincode`: 6 digits.
- `identity`: required object with ID type and ID number.

Frontend validation before `validate-otp`:

- `otp_flow_id`: required.
- `otp`: required, non-empty string.

## 8. Current Backend Caveats Frontend Must Handle

- Normalize both `responseCode` and `responsecode`.
- `generate-otp`, `validate-otp`, and `webhook-status` do not return `reference_id`.
- `list-reports` is currently the only frontend-accessible way to discover `reference_id`.
- Report section shapes are vendor-driven under `cibil_report.EquifaxRetail`.
- Auth middleware responses do not follow the CIBIL response envelope.
- Some backend messages contain spelling/casing issues, for example `successdfully`; use response codes for logic, not message text.
- `list-reports` has no pagination or guaranteed sort order in the current implementation.

## 9. Backend Improvement Requests That Would Simplify Frontend

- Return `reference_id` from `GET /v1/cibil/webhook-status/{otp_flow_id}` when `webhook_status` is `SUCCESS`.
- Standardize all responses to `responseCode`.
- Add Pydantic schemas so OpenAPI docs show exact request and response types.
- Add pagination and sorting to `list-reports`.
- Return a normalized report section DTO instead of raw vendor-shaped nested data.
