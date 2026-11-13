import os
import json
import socket
import threading
import queue
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# 1. 加载环境变量
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)
client = OpenAI(api_key=os.environ.get("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
MODEL = "deepseek-chat"

# --- 初始化 UDP 发送端 ---
UNITY_IP = "127.0.0.1"
UNITY_PORT = 5066
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

UNITY_INPUT_PORT = 5067
llm_task_queue = queue.Queue()

# 💡 修复 1：全局初始化场景状态
current_scene_state = {}


def listen_from_unity():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", UNITY_INPUT_PORT))
    print(f"👂 Python 端已开启监听，等待 Unity 发来数据 (端口 {UNITY_INPUT_PORT})...")

    global current_scene_state  # 声明使用全局变量

    while True:
        try:
            data, addr = sock.recvfrom(65535)
            message = json.loads(data.decode('utf-8'))

            # 路由：如果收到的是场景状态
            if message.get("msg_type") == "scene_state":
                current_scene_state = message
                print(f"📸 收到场景更新，当前有 {len(message.get('objects', []))} 个可交互物体。")

            # 否则认为是用户指令
            elif "text" in message:
                user_text = message["text"]
                print(f"\n🎤 收到来自 Unity 的指令: {user_text}")
                llm_task_queue.put(user_text)

        except json.JSONDecodeError:
            print("收到无法解析的数据 (非 JSON 格式):", data)
        except Exception as e:
            print(f"Socket 监听发生异常: {e}")


# ==========================================
# 2. 模拟 Agent 的工具库 (Tools)
# ==========================================
def query_spatial_memory(query: str) -> str:
    """查询 XR 空间历史记忆 (模拟 RAG)"""
    print(f"   [⚙️ 工具执行] 正在检索空间记忆: '{query}'")
    if "画笔" in query:
        return "记忆显示：用户早上9点把红色的虚拟画笔放在了办公桌上。"
    return "记忆里没有相关记录。"


def control_xr_environment(action_type: str, target: str, value: str) -> str:
    """控制 XR 环境（将指令发送给 Unity）"""
    command_data = {
        "action": action_type,
        "target": target,
        "value": value
    }
    json_str = json.dumps(command_data)
    payload = json_str.encode('utf-8')

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
                "properties": {"query": {"type": "string", "description": "检索关键词"}},
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

available_functions = {
    "query_spatial_memory": query_spatial_memory,
    "control_xr_environment": control_xr_environment,
}


# ==========================================
# 3. Agent 的大脑循环 (Agent Loop)
# ==========================================
def run_agent(user_input: str):
    print(f"\n👤 用户: {user_input}")

    # 提取当前场景状态
    obj_list = []
    for o in current_scene_state.get("objects", []):
        # 增加防止 KeyError 的容错
        name = o.get('name', 'Unknown')
        x, y, z = o.get('x', 0), o.get('y', 0), o.get('z', 0)
        color = o.get('color', 'N/A')
        obj_list.append(f"[{name}] 颜色:{color} 坐标:({x:.1f},{y:.1f},{z:.1f})")

    scene_desc = "当前场景包含以下物体: " + "; ".join(obj_list) if obj_list else "当前场景为空。"

    dynamic_prompt = f"""
    你是一个高级 XR 空间管家 Agent。你有权使用提供的工具。
    请结合以下【当前环境状态】进行思考：
    {scene_desc}

    如果指令涉及现有物体，请参考它们的名称和坐标进行准确操作。
    """

    messages = [
        {"role": "system", "content": dynamic_prompt},
        {"role": "user", "content": user_input}
    ]

    # 💡 修复 2：补全缺失的 Agent 循环逻辑
    for step in range(5):  # 最多思考 5 步防止死循环
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
        except Exception as e:
            print(f"❌ 请求 LLM 失败: {e}")
            break

        response_message = response.choices[0].message
        messages.append(response_message)

        # 如果没有调用工具，说明任务完成，输出最终回答
        if not response_message.tool_calls:
            print(f"🤖 Agent: {response_message.content}")
            break

        # 如果调用了工具，执行它
        print(f"🧠 Agent 决定调用 {len(response_message.tool_calls)} 个工具...")
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            print(f"   -> 调用: {function_name} | 参数: {function_args}")

            function_to_call = available_functions.get(function_name)
            if function_to_call:
                function_response = function_to_call(**function_args)
            else:
                function_response = "Error: 找不到该函数。"

            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": function_response,
            })


def main():
    # 启动网络监听线程
    threading.Thread(target=listen_from_unity, daemon=True).start()

    print("=" * 50)
    print("       XR 具身智能 Agent (场景感知版)")
    print("=" * 50)
    print("💡 提示：在 Unity 界面中按下空格键，发送指令给 Agent。")

    while True:
        try:
            user_input = llm_task_queue.get(timeout=0.1)
        except queue.Empty:
            continue

        # 收到指令后，运行 Agent
        run_agent(user_input)


if __name__ == "__main__":
    main()