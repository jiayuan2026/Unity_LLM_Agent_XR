import os
import json
import socket
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# 1. 加载环境变量
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)
client = OpenAI(api_key=os.environ.get("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
MODEL = "deepseek-chat"


# ==========================================
# 2. 模拟 Agent 的工具库 (Tools)
# ==========================================
# 这里的函数就是 Agent 可以调用的武器，真实项目中会通过 Socket 发给 Unity

def query_spatial_memory(query: str) -> str:
    """查询 XR 空间历史记忆 (模拟 RAG)"""
    print(f"   [⚙️ 工具执行] 正在检索空间记忆: '{query}'")
    # 模拟数据库返回
    if "画笔" in query:
        return "记忆显示：用户早上9点把红色的虚拟画笔放在了办公桌上。"
    return "记忆里没有相关记录。"

# --- 初始化 UDP 发送端 ---
# 假设 Unity 运行在同一台电脑上，IP 是 127.0.0.1
UNITY_IP = "127.0.0.1"
UNITY_PORT = 5066  # 随便定一个不冲突的端口

# 创建一个 UDP socket
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


# --- 修改你的 Agent 工具函数 ---
def control_xr_environment(action_type: str, target: str, value: str) -> str:
    """控制 XR 环境（将指令发送给 Unity）"""

    # 1. 构造要发给 Unity 的数据 (JSON格式)
    command_data = {
        "action": action_type,
        "target": target,
        "value": value
    }

    # 2. 转成 JSON 字符串并编码为字节
    json_str = json.dumps(command_data)
    payload = json_str.encode('utf-8')

    # 3. 发送给 Unity！
    try:
        udp_socket.sendto(payload, (UNITY_IP, UNITY_PORT))
        print(f"   [📡 网络发送] 已发送数据到 Unity: {json_str}")
        return f"成功：指令已发送给 Unity，执行 {action_type}。"
    except Exception as e:
        print(f"   [❌ 发送失败] {e}")
        return "失败：无法连接到 Unity。"


# 定义给 LLM 看的工具清单 (Schema)
tools = [
    {
        "type": "function",
        "function": {
            "name": "query_spatial_memory",
            "description": "当用户询问过去放置的物品位置、历史操作时使用此工具查询记忆。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索关键词"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "control_xr_environment",
            "description": "控制当前的 XR 环境，比如生成面板、改变光照亮度、改变颜色。",
            "parameters": {
                "type": "object",
                "properties": {
                    "action_type": {"type": "string", "description": "动作类型，如 create_panel, set_light"},
                    "target": {"type": "string", "description": "操作对象，如 main_light, ui_panel"},
                    "value": {"type": "string", "description": "具体参数，如 5.0, red"}
                },
                "required": ["action_type", "target", "value"]
            }
        }
    }
]

# 工具路由字典
available_functions = {
    "query_spatial_memory": query_spatial_memory,
    "control_xr_environment": control_xr_environment,
}

# ==========================================
# 3. Agent 的大脑循环 (Agent Loop)
# ==========================================
SYSTEM_PROMPT = """
你是一个高级 XR 空间管家 Agent。
你的目标是帮助用户解决空间任务。你有权使用提供的工具。
请一步步思考。如果用户的指令需要分多步完成，请先调用相应的工具，拿到结果后再继续。
"""


def run_agent(user_input: str):
    print(f"\n👤 用户: {user_input}")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input}
    ]

    # 开启 Agent 循环，最多允许思考 5 步，防止死循环
    for step in range(5):
        print(f"\n--- [Agent 思考轮次 {step + 1}] ---")

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        response_message = response.choices[0].message
        messages.append(response_message)  # 将助手的回复（可能是工具调用）加入历史

        # 如果模型没有调用工具，说明它任务完成了，输出了最终回答
        if not response_message.tool_calls:
            print(f"🤖 Agent 最终回复:\n{response_message.content}")
            break

        # 如果模型调用了工具
        print(f"🧠 Agent 决定调用 {len(response_message.tool_calls)} 个工具...")

        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            # 执行实际的 Python 函数
            function_to_call = available_functions[function_name]
            function_response = function_to_call(**function_args)

            # 把执行结果作为 Observation（观察结果）扔回给大模型
            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": function_response,
            })


# ==========================================
# 4. 运行测试
# ==========================================
if __name__ == "__main__":
    print("=" * 50)
    print("       XR Agent: 自主任务与工具编排")
    print("=" * 50)

    # 测试用例 1：单步任务（直接调环境）
    run_agent("帮我把当前房间的灯光亮度调低到 3.0。")

    # 测试用例 2：需要记忆检索的复杂任务（Agent 需自己判断先查记忆，再操作）
    run_agent("找到我早上放画笔的地方，并在那个位置上方生成一个红色的控制面板。")