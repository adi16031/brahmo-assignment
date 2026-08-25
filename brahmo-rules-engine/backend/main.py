from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routers.pipeline import router as pipeline_router

app = FastAPI(title="BRAHMO Rules Engine — BFS + 5-Check Filter Pipeline")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    # Config errors (e.g. Supabase credentials not filled in yet) — surface
    # a clear JSON message instead of a bare 500 that CORS strips from the
    # browser's view (fetch() would otherwise just report "Failed to fetch").
    return JSONResponse(status_code=503, content={"detail": str(exc)})


app.include_router(pipeline_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
