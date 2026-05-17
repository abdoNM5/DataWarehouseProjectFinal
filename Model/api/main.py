"""
FastAPI application entrypoint.
Wires routers, CORS policy, and health endpoint.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.routers import offers, recommend, skills


app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_URLS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recommend.router, prefix="/api", tags=["Recommendations"])
app.include_router(offers.router, prefix="/api", tags=["Offers"])
app.include_router(skills.router, prefix="/api", tags=["Metadata"])


@app.get("/api/health", tags=["Health"])
def health_check() -> dict:
    """Simple liveness probe for local/dev and Docker checks."""
    return {"status": "ok"}
