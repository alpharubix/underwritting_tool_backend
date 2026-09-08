# API logging middleware

## Middleware order

The application currently registers middleware in this order:

1. Authorization middleware via `app.middleware("http")(authorization)`.
2. API logging middleware via `app.middleware("http")(api_logging)`.
3. `CORSMiddleware` via `app.add_middleware(...)`.

Starlette inserts each new user middleware at the front of `app.user_middleware` and wraps the stack in reverse order. Therefore, the effective request execution order is:

```text
Incoming request
  -> CORS
  -> API logging start
  -> authorization
  -> FastAPI route
  <- authorization
  <- CORS
  <- API logging end and structured log
```

The desired order is the same as the effective order. API logging is registered after CORS so it wraps both CORS and authorization without changing either middleware's behavior. Authorization remains responsible for authentication and for populating `request.state.user_id` and `request.state.role`.

The final log is built in the logging middleware's `finally` block, after `await call_next(request)` has completed or raised. At that point authorization has already run on the way into the route, so authenticated requests expose `request.state.user_id` to the final log. The middleware only reads that context; it does not authenticate, authorize, or overwrite those values.

Logging errors are caught and ignored so they cannot change response status codes, swallow application exceptions, or make an API request fail.

## Storage

Each record is inserted into the existing `request.app.state.mongo_db` database handle using `await db.logs.insert_one(record)`. The current database initializer selects the `underwriting` database, so records are stored in its `logs` collection.

The same JSON record is also emitted to stdout for Cloud Run operational logging. If MongoDB logging fails, the error is ignored so the API response is preserved.
