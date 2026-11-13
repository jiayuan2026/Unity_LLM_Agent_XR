import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from typing import Literal, Dict

# 1) 加载 .env（显式指定脚本同目录，避免 cwd 问题）
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError(f"OPENAI_API_KEY 未加载，检查 {env_path} 是否存在且格式为 KEY=value")

# 2) 创建 client —— 这就是你缺的那一行
client = OpenAI(api_key=api_key)

# 3) 定义输出 Schema
class UISuggestion(BaseModel):
    action: Literal["place_widget", "reposition", "remove"]
    widget_type: str
    position: Dict[str, float]   # {"x":.., "y":.., "z":..}
    reason: str

# 4) 调用结构化输出
def get_suggestion(context: str) -> UISuggestion:
    resp = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You suggest XR UI layout changes. Return one suggestion."},
            {"role": "user", "content": context},
        ],
        response_format=UISuggestion,
    )
    return resp.choices[0].message.parsed

if __name__ == "__main__":
    ctx = "User is reading a long English paragraph in a virtual room; gaze is fixed on the text for 12s."
    s = get_suggestion(ctx)
    print(type(s))
    print(s)
    print("action =", s.action)
    print("position =", s.position)