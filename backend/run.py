"""后端服务启动入口。

用法：
    python run.py
等价于：
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)
