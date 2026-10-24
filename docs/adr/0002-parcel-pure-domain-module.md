# 0002. Keep the parcel lifecycle in a pure domain module

## Status

Accepted

## Context
The parcel lifecycle (dispatch, deliver, fail, return, ...) changes as the business changes.
If the rules were written inside every endpoint, each change would have to be repeated across all those functions, and a lot of changes means bugs can appear in the code.

## Decision

We will keep all lifecycle rules in `app/domain.py` as plain Python. The function
`apply_event(parcel, event)` returns a new frozen `Parcel` and raises
`InvalidTransition` for forbidden moves. The API layer only calls it,
and turns `InvalidTransition` into a 409 problem document. (The task specified this structure); the reasons above are why we keep it.

## Consequences

Rules can be tested directly with no HTTP server, and a rule change touches one file.
Because `Parcel` is frozen, the API must store the returned copy (`store[id] = updated`), or the change is lost.
The API and domain also have to be kept in ((sync)) by hand: for example, the 409 mapping lives in the API, while the rule that causes it lives in the domain. There is a little more code than putting everything in the endpoints.