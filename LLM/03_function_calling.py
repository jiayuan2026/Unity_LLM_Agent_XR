import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# 1. 加载环境变量
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)
client = OpenAI(api_key=os.environ.get("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
MODEL = "deepseek-chat"


# ==========================================
# 2. 定义你的 Python 工具 (真实的执行逻辑)
# ==========================================
# 注意：这些函数在真实项目中，就是通过 Socket 发送指令给 Unity 的地方

def spawn_cube(x: float, y: float, z: float, color: str) -> str:
    """在 XR 空间中生成一个立方体"""
    # 模拟实际执行
    print(f"\n[系统执行] 🎯 在坐标 ({x}, {y}, {z}) 生成了一个 {color} 的立方体！")
    return f"Success: Cube created at {x},{y},{z} with color {color}."


def change_light_intensity(intensity: float) -> str:
    """改变 XR 空间的环境光亮度"""
    print(f"\n[系统执行] 💡 环境光亮度已调整为 {intensity}")
    return f"Success: Light intensity set to {intensity}."


def play_sound_effect(name: str) -> str:
    """播放音效"""
    print(f"\n[系统执行] 🔊 正在播放音效: {name}")
    return f"Success: Playing sound {name}."


# ==========================================
# 3. 定义工具清单 (给 LLM 看的说明书)
# ==========================================
tools = [
    {
        "type": "function",
        "function": {
            "name": "spawn_cube",
            "description": "在 3D 空间中生成一个立方体",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "number", "description": "X坐标"},
                    "y": {"type": "number", "description": "Y坐标"},
                    "z": {"type": "number", "description": "Z坐标"},
                    "color": {"type": "string", "description": "颜色名称，例如 red, blue"}
                },
                "required": ["x", "y", "z", "color"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "change_light_intensity",
            "description": "改变环境光的亮度",
            "parameters": {
                "type": "object",
                "properties": {
                    "intensity": {"type": "number", "description": "亮度值，0到10之间"}
                },
                "required": ["intensity"]
            }
        }
    }
]

# ==========================================
# 4. 绑定工具名称到真实的 Python 函数
# ==========================================
available_functions = {
    "spawn_cube": spawn_cube,
    "change_light_intensity": change_light_intensity,
}

conversation_history = []


def chat():
    print("=" * 50)
    print("       XR Function Calling Agent")
    print("=" * 50)

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ["/exit", "exit"]: break
        if not user_input: continue

        conversation_history.append({"role": "user", "content": user_input})

        # --- 第一轮请求：让 LLM 决定要不要调用工具 ---
        response = client.chat.completions.create(
            model=MODEL,
            messages=conversation_history,
            tools=tools,  # 把工具清单传给模型
            tool_choice="auto"  # 让模型自己决定是否调用
        )

        response_message = response.choices[0].message

        # 把 LLM 的思考（包括它想调用的工具）存入历史
        conversation_history.append(response_message)

        # --- 检查模型是否要求调用工具 ---
        if response_message.tool_calls:
            print("\n[Agent 思考] 我需要执行一些操作...")

            # 遍历模型请求的所有工具调用
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                print(f"[Agent 决定] 调用函数: {function_name} | 参数: {function_args}")

                # 从字典中找到对应的 Python 函数并执行
                if function_name in available_functions:
                    function_to_call = available_functions[function_name]
                    function_response = function_to_call(**function_args)
                else:
                    function_response = "Error: Function not found."

                # 💡 关键步骤：把函数的执行结果包装成特殊消息，发给 LLM
                conversation_history.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                })

            # --- 第二轮请求：把执行结果给 LLM，让它总结给用户 ---
            second_response = client.chat.completions.create(
                model=MODEL,
                messages=conversation_history
            )

            final_answer = second_response.choices[0].message.content
            print("\nAssistant:", final_answer)
            conversation_history.append({"role": "assistant", "content": final_answer})

        else:
            # 模型没调用工具，直接聊天
            print("\nAssistant:", response_message.content)
            # 已经在上面 append 过 message 了，这里不需要再 append


if __name__ == "__main__":
    chat()