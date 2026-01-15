from starlette.responses import JSONResponse

from mcpserver.app import mcp


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    return JSONResponse({"status": 200, "message": "OK"})
