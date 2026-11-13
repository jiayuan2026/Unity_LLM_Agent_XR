import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI, AuthenticationError, APIStatusError
from pydantic import BaseModel, Field, ValidationError

# 1. 加载环境变量
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)
client = OpenAI(api_key=os.environ.get("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
MODEL = "deepseek-chat"


# 2. 定义严格的数据模型（这就是给 Unity 用的）
class Vec3(BaseModel):
    x: float = Field(description="X坐标(左右)")
    y: float = Field(description="Y坐标(上下)")
    z: float = Field(description="Z坐标(前后)")


class XRCommand(BaseModel):
    action: str = Field(description="动作类型，例如: create, delete, move, change_color")
    object_type: str = Field(description="物体类型，例如: cube, panel, light")
    position: Vec3 = Field(description="物体的 3D 坐标")
    color: str = Field(default="white", description="物体的颜色")


# 3. 系统提示词：极度强调 JSON 格式
SYSTEM_PROMPT = """
You are an XR Spatial Assistant. You translate user requests into JSON commands to control a 3D environment.

You MUST respond with a valid JSON object ONLY. Do not include markdown code blocks, explanations, or any other text.

The JSON must strictly follow this schema:
{
  "action": "string (e.g., create, delete, move, change_color)",
  "object_type": "string (e.g., cube, sphere, panel, light)",
  "position": {"x": float, "y": float, "z": float},
  "color": "string"
}
"""

conversation_history = []


def chat():
    print("=" * 50)
    print("       XR Command Generator (JSON Mode)")
    print("=" * 50)

    while True:
        user_input = input("\nYou (指令): ").strip()
        if user_input.lower() in ["/exit", "exit"]: break
        if not user_input: continue

        conversation_history.append({"role": "user", "content": user_input})

        try:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history

            # 💡 开启 JSON Mode，强制模型返回 JSON 对象
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                response_format={"type": "json_object"},  # 这是 DeepSeek 支持的 JSON 模式
                temperature=0.0  # 调到 0，保证生成的坐标和结构最稳定
            )

            raw_json_str = response.choices[0].message.content
            print(f"\n[LLM 原始输出]: {raw_json_str}")

            # 💡 核心：使用 Pydantic 进行严格校验
            try:
                # 把字符串解析为 Python 字典，并验证格式
                validated_command = XRCommand.model_validate_json(raw_json_str)
                print("\n✅ 校验通过！准备发送给 Unity：")
                # .model_dump() 可以转回字典，方便你后面通过 Socket 发给 Unity
                print(json.dumps(validated_command.model_dump(), indent=2, ensure_ascii=False))

                # 把这句合法的 JSON 存进历史，保持对话连贯
                conversation_history.append({"role": "assistant", "content": raw_json_str})

            except ValidationError as e:
                # 如果 LLM 少给了字段或者类型不对，这里会精准报错
                print("\n❌ 数据结构校验失败，拦截了这条脏数据！")
                print(e.json())
                conversation_history.pop()  # 失败则撤回

        except Exception as error:
            conversation_history.pop()
            print("\nAPI 请求错误:", error)


if __name__ == "__main__":
    chat()