import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from metaforge_api.api.routers import admin, ai_chat, ai_conversations, ai_settings, approvals, auth, clearing, data, document_flow, financial_reports, gl, modules, notifications, number_series, oauth, periodic_runs, price_lists, reports, saved_views, search, stock, telegram_link, tokens, uploads, webhooks
from metaforge_api.infrastructure import depreciation  # noqa: F401 - side effect: registers the "asset_depreciation" periodic run
from metaforge_api.infrastructure import telegram_poller


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Long-polls Telegram for the AI assistant integration — a no-op loop
    # (cheap idle sleep) whenever Telegram isn't configured/enabled; see
    # telegram_poller.py for why this lives here rather than on ARQ.
    stop_event = asyncio.Event()
    poller_task = asyncio.create_task(telegram_poller.run_poller_forever(stop_event=stop_event))
    yield
    stop_event.set()
    poller_task.cancel()
    with suppress(asyncio.CancelledError):
        await poller_task


app = FastAPI(title="MetaForge API", lifespan=lifespan)

app.include_router(modules.router)
app.include_router(data.router)
app.include_router(auth.router)
app.include_router(oauth.router)
app.include_router(uploads.router)
app.include_router(admin.router)
app.include_router(notifications.router)
app.include_router(number_series.router)
app.include_router(search.router)
app.include_router(webhooks.router)
app.include_router(approvals.router)
app.include_router(saved_views.router)
app.include_router(tokens.router)
app.include_router(gl.router)
app.include_router(clearing.router)
app.include_router(stock.router)
app.include_router(document_flow.router)
app.include_router(reports.router)
app.include_router(financial_reports.router)
app.include_router(periodic_runs.router)
app.include_router(price_lists.router)
app.include_router(ai_settings.router)
app.include_router(ai_chat.router)
app.include_router(ai_conversations.router)
app.include_router(telegram_link.router)


@app.exception_handler(KeyError)
async def unknown_module_handler(request: Request, exc: KeyError):
    # ModuleRegistry.get() raises KeyError for an unregistered module name —
    # surface it as a clean 404 instead of an unhandled-exception 500.
    return JSONResponse(status_code=404, content={"detail": str(exc).strip("'\"")})


@app.get("/health")
async def health():
    return {"status": "ok"}
