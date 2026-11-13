import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# 显式加载脚本同目录的 .env，避免 cwd 问题
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

api_key = os.environ.get("DEEPSEEK_API_KEY")
if not api_key:
    raise RuntimeError(f"未找到 DEEPSEEK_API_KEY，检查 {env_path}")

# 唯一的改动：base_url 指向 DeepSeek
client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com",
)

def chat(prompt: str, model: str = "deepseek-flash", temperature: float = 0.2) -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        stream=False,)
    return resp.choices[0].message.content

if __name__ == "__main__":
    print(chat("用一句话解释什么是 XR 中的空间锚定。"))