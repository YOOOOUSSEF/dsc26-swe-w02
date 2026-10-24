"""HTTP layer for the Tawseel parcel service.

The HTTP layer translates requests into calls to app.domain; the domain decides.
See README.md for the four operations, their operationIds and their errors.
"""
from fastapi import FastAPI,responses,Response,Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel,Field,ConfigDict
from app.domain import EventType, InvalidTransition, Parcel, ParcelState, apply_event  # noqa: F401

class parcel_validator(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    merchant_ref:str= Field(min_length=1, max_length=64)
    cod_amount_piastres:int=Field(ge=0, le=5_000_000)
    address_text:str= Field(min_length=1, max_length=500)

class EventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: EventType

class APIError(Exception):
    def __init__(self, type,status, title,errors=None, detail=None):
        self.type,self.status, self.title,self.errors, self.detail = type,status, title,errors, detail


def problem(type,status, title, detail=None,errors=None, **extra):
    body = {"type": type, "title": title, "status": status, **extra}
    if detail:
        body["detail"] = detail
    if errors:
        body["errors"] = errors
    return responses.JSONResponse(body, status_code=status, media_type="application/problem+json")

def create_app() -> FastAPI:
    """Return a NEW FastAPI app with its own empty in-memory store.

    Tests call this once per test, so nothing may be shared between two apps
    (no module-level dicts or counters for parcels).
    """

    store: dict[str, Parcel] = {}
    order: list[str] = []               # ids in creation order

    issued: set[str] = set()
    counter=0
    app=FastAPI(title="Tawseel parcel service", version="0.1.0")

    @app.exception_handler(APIError) # for My own Errors
    async def on_api_error(request, exc: APIError):
        return problem(exc.type,exc.status, exc.title, exc.detail,exc.errors)
    
    @app.exception_handler(RequestValidationError)# for validation Errors raised by FastAPI
    async def on_validation(request, exc: RequestValidationError):
        by_loc = {}
        for e in exc.errors():
            by_loc[tuple(e["loc"])]= {"loc": e["loc"], "msg": e["msg"]}   # one entry per field
        return problem('Validation Error',422, "Invalid body", errors=list(by_loc.values()))



    # 1 
    @app.post('/v1/parcels', status_code=201, operation_id='createParcel',
          responses={
              409: {"description": "Duplicate merchant_ref", "content": {"application/problem+json": {}}},
              422: {"description": "Invalid body", "content": {"application/problem+json": {}}},
          },response_model=Parcel)
    def create_parcel(body:parcel_validator,response:Response):
        nonlocal counter
        if any(item.merchant_ref == body.merchant_ref for item in store.values()):
            raise APIError('Uniqueness Error',409,'Duplicate merchant_ref')
        
        parcel_id:str=f"pcl_{counter}"
        counter+=1

        p = Parcel(id=parcel_id,merchant_ref=body.merchant_ref,cod_amount_piastres=body.cod_amount_piastres,
        address_text=body.address_text)
        store[parcel_id]=p
        order.append(parcel_id)


        response.headers['Location']=f"/v1/parcels/{parcel_id}"
        return p


    # 2
    @app.get('/v1/parcels/{parcel_id}',status_code=200,operation_id='getParcel',responses={
        404:{'description':'Not found Parcel with this Id','content':{'application/problem+json':{}}}
    },response_model=Parcel)
    def get_parcel(parcel_id:str):
        if parcel_id in store:
            return store[parcel_id]

        raise APIError('Not Found',404,f"Not found parcel with id {parcel_id}")



    # 3
    @app.get('/v1/parcels',status_code=200,operation_id='listParcels',
          responses={
              400: {"description": "bad cursor", "content": {"application/problem+json": {}}},
              422: {"description": "bad state or limit", "content": {"application/problem+json": {}}},
          })
    def list_parcels(request: Request):
        nonlocal issued
        q = request.query_params
        errors = []

        limit = 20
        if "limit" in q:
            try:
                limit = int(q["limit"])
                if not 1 <= limit <= 100:
                    raise ValueError
            except ValueError:
                errors.append({"loc": ["query", "limit"],
                            "msg": "limit must be an integer between 1 and 100"})

        state = None
        if "state" in q:
            try:
                state = ParcelState(q["state"])
            except ValueError:
                errors.append({"loc": ["query", "state"],
                            "msg": "state must be one of: " + ", ".join(s.value for s in ParcelState)})

        if errors:
            raise APIError('Value Error', 422, "bad state or limit", errors=errors)

        
        start = 0
        if "cursor" in q:
            if q["cursor"] not in issued:
                raise APIError('Bad Request', 400, "bad cursor")
            start = order.index(q["cursor"])+1


        parcels = []
        next_cursor=None
        for pid in order[start:]:
            item = store[pid]
            if (state is None or state == item.state):
                if(len(parcels)==limit):
                    next_cursor=parcels[-1].id
                    issued.add(next_cursor)
                    break
                parcels.append(item)

        return {'items':parcels,'next_cursor':next_cursor}




    # 4
    @app.post('/v1/parcels/{parcel_id}/events',status_code=200,operation_id='recordParcelEvent',
          responses={
              404:{'description':'Not found Parcel with this Id','content':{'application/problem+json':{}}},
              409:{"description": "Invalid transition (parcel unchanged)", "content": {"application/problem+json": {}}},
              422:{"description": "unknown or missing event type", "content": {"application/problem+json": {}}},
          })
    def record_parcel_event(parcel_id:str,body:EventIn):
        try:
            parcel=store.get(parcel_id)
            if parcel is not None:
                p = apply_event(parcel, body.type)
                store[parcel_id] = p
                return p
        except InvalidTransition:
                raise APIError('Value Error',409,f"Invalid transition (parcel unchanged)")

        raise APIError('Not Found',404,f"Not found parcel with id {parcel_id}")
        
    return app
    


# `uvicorn app.api:app` needs a module-level app. Once create_app() works,
# replace the line below with:  app = create_app()
app = create_app()
