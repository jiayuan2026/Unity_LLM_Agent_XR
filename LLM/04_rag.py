import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import chromadb

# 1. 加载环境变量
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)
client = OpenAI(api_key=os.environ.get("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
MODEL = "deepseek-chat"

# 2. 初始化向量数据库 (使用内存模式，关闭遥测，程序关了就清空)
chroma_client = chromadb.EphemeralClient()
collection = chroma_client.create_collection(name="xr_memory")

# 3. 模拟 XR 空间日志并“灌入”知识库 (Indexing)
# 真实场景中，这些数据是 Unity 不断发给 Python 存下来的
print("正在初始化空间记忆库...")
xr_logs = [
    "早上9点，用户在办公桌上放下了红色的虚拟画笔。",
    "早上10点，用户把3D模型直升机移动到了房间左上角的悬空展示区。",
    "中午12点，用户在客厅的沙发旁边创建了一个绿色的控制面板。",
    "下午2点，用户把环境光照亮度调低到了 2.0，并设置了紫色的氛围灯。",
    "下午3点，用户把常用的手势文档固定在左侧手腕的快捷菜单里。"
]
# 给每条记录分配一个 ID
ids = [f"log_{i}" for i in range(len(xr_logs))]

# 将文本存入数据库，Chroma 会自动进行向量化处理
collection.add(
    documents=xr_logs,
    ids=ids
)
print("记忆库初始化完成！\n")

# 4. 定义 RAG 检索函数
def retrieve_context(query: str, top_k: int = 2) -> str:
    """根据用户提问，去向量库找最相关的 top_k 条记录"""
    results = collection.query(
        query_texts=[query],
        n_results=top_k
    )
    # results['documents'] 是一个二维列表，取出第一组的文本
    retrieved_docs = results['documents'][0]
    return "\n".join(retrieved_docs)

# 5. 聊天主循环
conversation_history = []

def chat():
    print("=" * 50)
    print("       XR 空间记忆助手 (RAG Mode)")
    print("=" * 50)

    while True:
        user_input = input("\nYou (提问): ").strip()
        if user_input.lower() in ["/exit", "exit"]: break
        if not user_input: continue

        # A. 检索 (Retrieve)
        context = retrieve_context(user_input)
        print(f"\n[🔍 后台检索到的日志]:\n{context}")

        # B. 增强 (Augment) - 把检索到的日志拼接到 System Prompt 里
        system_prompt = f"""
        你是一个 XR 空间管家。请根据以下用户历史空间操作日志来回答问题。
        如果你在日志中找不到答案，请诚实地回答“我找不到相关记录”，不要编造。

        【历史日志】:
        {context}
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]

        # C. 生成 (Generate)
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.1 # 降低温度，让模型严格根据日志回答
        )

        answer = response.choices[0].message.content
        print(f"\nAssistant: {answer}")

if __name__ == "__main__":
    chat()