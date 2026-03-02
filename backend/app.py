from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from resolver import Resolver
from dns_message import TYPE_A, TYPE_AAAA, TYPE_MX, TYPE_NS, TYPE_CNAME
from typing import List, Dict, Any, Optional

app = FastAPI(title="DNS Resolver API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TYPE_MAP = {
    'A': TYPE_A,
    'AAAA': TYPE_AAAA,
    'MX': TYPE_MX,
    'NS': TYPE_NS,
    'CNAME': TYPE_CNAME
}

class ResolutionResponse(BaseModel):
    domain: str
    record_type: str
    records: List[Dict[str, Any]]
    trace: List[str]

@app.get("/api/resolve", response_model=ResolutionResponse)
def resolve_domain(
    domain: str = Query(..., description="The domain to resolve"),
    type: str = Query("A", description="The DNS record type (A, AAAA, MX, NS, CNAME)")
):
    record_type = type.upper()
    if record_type not in TYPE_MAP:
        return {"error": "Unsupported record type"}

    resolver = Resolver()
    
    # Run resolution synchronously, FastAPI handles concurrent requests in worker threads
    records = resolver.resolve(domain, TYPE_MAP[record_type])
    
    return ResolutionResponse(
        domain=domain,
        record_type=record_type,
        records=records if records else [],
        trace=resolver.logs
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
