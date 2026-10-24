## Tools

<!-- Which tools you used (ChatGPT, Copilot, Claude, Cursor, none...) and for which parts. -->
claude 

parts:
In APIError class, Exception handler, fields beside endpoints like operation_id and responses, and storing parcels in dictionary
and nonlocal counter to be used inside functions. All of this was inside api.py .

## What AI got wrong

<!-- At least one thing an assistant got wrong that you changed, and how you noticed
(a test failed, the docs said otherwise, you ran it). -->
1) The assistant first said one HTTPException handler was enough. That was wrong, because Pydantic errors raise RequestValidationError, which needs its own handler to build Error (RFC 9457) template.

2) The assistant fetched `limit + 1` rows and built the cursor from `items[-1]`, which was the 11th row, not the last row of the page. That would skip parcel 11 on the next page. I noticed it by reading the code and checking it against the page 1 / page 2  (1-10, then 11-20). The cursor is now taken from the last item of the trimmed page.

## In my own words

<!-- Answer without AI, one or two sentences each. -->

1. Why does `listParcels` need a cursor rather than an offset?
Because Cursor stops at the last element of the page so when you start reading from no matter what happened to elements behind it,
but for Offset: it depends on position so if the first 10 elements for any reason got trimmed or left the filter, then it will skip the second 10 elements and start from the third 10. 

2. Which of your four operations would break the courier app if you renamed one field, and who would have to approve that change?
If you renamed a field in the request(body,query,path)(Examples:merchant_ref,parcel_id, ......) it will break code at the moment the request hit the API,but If you renamed a field in the response body(Examples:next_cursor,items, ......) then the break will be at processing that response.

The client/frontend who approves it because they depend on it.
