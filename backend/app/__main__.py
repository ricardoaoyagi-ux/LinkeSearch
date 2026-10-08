import asyncio
import sys

import uvicorn

if __name__ == "__main__":
    if sys.platform == "win32":
        # Playwright needs subprocess support, which only the Proactor loop has on Windows
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    # 127.0.0.1 only: the API (and the session it controls) is never exposed to the network
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, log_level="info")
