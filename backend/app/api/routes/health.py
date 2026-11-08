from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request):
    key = request.app.state.settings.openai_api_key
    ready = await request.app.state.store.ready()
    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "status": "ok" if ready else "degraded",
            "persistence": request.app.state.store.persistence,
            "llm_configured": bool(key and key.get_secret_value().strip()),
            "rag_available": bool(
                request.app.state.rag is not None and request.app.state.settings.rag_enabled and key
            ),
            "mcp_available": (await request.app.state.tools.status()).available,
        },
    )
