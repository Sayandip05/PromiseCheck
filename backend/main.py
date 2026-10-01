import os
import sys
from pathlib import Path

src_dir = str(Path(__file__).parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8001"))
    uvicorn.run("main:app", app_dir=src_dir, host="0.0.0.0", port=port, reload=True)
