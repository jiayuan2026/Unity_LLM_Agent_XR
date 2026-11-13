import os
from pathlib import Path
from dotenv import load_dotenv
# 💡 关键修改 1：把异常类导入进来
from openai import OpenAI, AuthenticationError, RateLimitError, APIConnectionError, APIStatusError

# 显式加载脚本同目录的 .env
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

api_key = os.environ.get("DEEPSEEK_API_KEY")
if not api_key:
    raise RuntimeError(f"未找到 DEEPSEEK_API_KEY，检查 {env_path}")

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com",
)

# 💡 关键修改 2：定义模型变量
MODEL = "deepseek-chat"  # 或者用 "deepseek-flash"

SYSTEM_PROMPT = """
You are a helpful AI assistant.

Your responsibilities:
1. Explain technical concepts clearly.
2. Help users learn Python and LLM development.
3. Provide practical coding examples.
4. Remember the context of the current conversation.
5. If you are uncertain, say so instead of guessing.

Keep your answers clear and educational.
"""

conversation_history = []


def chat():
    print("=" * 50)
    print("       Welcome to LLM Chatbot")
    print("=" * 50)
    print("Model:", MODEL)
    print("Commands: /reset, /exit")
    print("-" * 50)

    while True:
        user_input = input("\nYou: ").strip()

        if user_input.lower() == "/exit":
            print("\nChatbot: Goodbye!")
            break

        if user_input.lower() == "/reset":
            conversation_history.clear()
            print("\nChatbot: Conversation history cleared.")
            continue

        if not user_input:
            continue

        # 把用户的话加入历史
        conversation_history.append({
            "role": "user",
            "content": user_input
        })

        try:
            # 💡 关键修改 3：改回经典的 chat.completions 接口
            # 需要把 System Prompt 放在 messages 的最前面
            messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history

            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.7
            )

            # 💡 关键修改 4：获取回答的方式变了
            answer = response.choices[0].message.content
            print("\nAssistant:", answer)

            # 💡 关键修改 5：把 AI 的回答手动添加到历史中
            conversation_history.append({
                "role": "assistant",
                "content": answer
            })

        except AuthenticationError:
            conversation_history.pop()  # 失败时撤回刚加入的用户消息
            print("\nError: Invalid API Key.")
        except RateLimitError:
            conversation_history.pop()
            print("\nError: API quota or rate limit exceeded.")
        except APIConnectionError:
            conversation_history.pop()
            print("\nError: Unable to connect to API.")
        except APIStatusError as error:
            conversation_history.pop()
            print(f"\nAPI Error: {error.status_code}")
            print(error.message)
        except Exception as error:
            conversation_history.pop()
            print("\nUnexpected error:", error)


if __name__ == "__main__":
    chat()