# 0001. Custom ApiError for problem documents

## Status
Accepted

## Context
Every error must be `application/problem+json` with at least `type`, `title` and `status`.
`HTTPException` carries only `status_code` and `detail`, so the extra fields would have to be packed into a `detail` dict, where a ((mistyped)) key fails silently.


## Decision
We will raise our own `ApiError(type, status, title, more)` for 400, 404, 409, and 422 and
render it with one exception handler that builds the problem document.

## Consequences
Fields are named arguments, so mistakes fail early and the error shape lives in one
place. We still need a separate handler for `HTTPException` raised by the framework
(((unknown routes)), 405) and a (((bit more code))) than using `HTTPException` alone.