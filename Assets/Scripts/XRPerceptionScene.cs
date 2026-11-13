using System;
using System.Text;
using System.Collections.Generic;
using UnityEngine;
using System.Net;
using System.Net.Sockets;
using System.Collections.Concurrent;
using System.Threading;

public class XRPerceptionScene : MonoBehaviour
{
    public string pythonIP = "127.0.0.1";
    public int pythonPort = 5067;   // Python 接收场景状态和语音的端口
    public int unityListenPort = 5066; // Unity 接收 Python 指令的端口

    private UdpClient udpSender;    // 用于发送
    private UdpClient udpReceiver;  // 用于接收
    private Thread receiveThread;

    public float sendInterval = 1.0f;
    private float timer = 0f;

    private ConcurrentQueue<string> messageQueue = new ConcurrentQueue<string>();

    // --- 用于序列化场景状态的数据结构 ---
    [Serializable]
    public class SceneObject
    {
        public string name;
        public float x;
        public float y;
        public float z;
        public string color;
    }

    [Serializable]
    public class SceneState
    {
        public string msg_type = "scene_state";
        public List<SceneObject> objects = new List<SceneObject>();
    }

    // --- 用于接收 Python 指令的数据结构 ---
    [Serializable]
    public class CommandData
    {
        public string action;
        public string target;
        public string value;
        public float x;
        public float y;
        public float z;
    }

    // --- 用于发送语音测试的数据结构 ---
    [Serializable]
    public class UserVoiceInput
    {
        public string text;
    }

    void Start()
    {
        // 1. 初始化发送端
        udpSender = new UdpClient();

        // 2. 初始化接收端并开启后台线程
        udpReceiver = new UdpClient(unityListenPort);
        receiveThread = new Thread(new ThreadStart(ReceiveData));
        receiveThread.IsBackground = true;
        receiveThread.Start();
        Debug.Log($"🎧 Unity 已启动，正在监听端口 {unityListenPort} 接收 Python 指令。");
    }

    void Update()
    {
        // 定时发送场景状态
        timer += Time.deltaTime;
        if (timer >= sendInterval)
        {
            timer = 0f;
            SendSceneState();
        }

        // 在主线程处理接收到的指令
        while (messageQueue.TryDequeue(out string message))
        {
            Debug.Log($"收到 Python 消息: {message}");
            ProcessCommand(message);
        }

        // 模拟语音输入测试 (按空格键)
        if (Input.GetKeyDown(KeyCode.Space))
        {
            // string userVoice = "帮我把灯光调亮到 8.0"; 
            string userVoice = "帮我把坐标为 1,1.4,-1 的那个红色的 Cube 改成蓝色, 再移到 -1.5,1.354,-1.5。最后帮我把灯光调亮到 5.0";
           // string userVoice = "帮我把坐标为 1,1,-1 的那个红色的 Cube 移到 -1.5,1.354,-1.5。";
            SendToPython(userVoice);
        }
    }

    // ================= 接收逻辑 =================
    private void ReceiveData()
    {
        while (true)
        {
            try
            {
                IPEndPoint anyIP = new IPEndPoint(IPAddress.Any, 0);
                byte[] data = udpReceiver.Receive(ref anyIP);
                string text = Encoding.UTF8.GetString(data);
                messageQueue.Enqueue(text); // 塞入队列让主线程处理
            }
            catch (Exception e)
            {
                Debug.LogError("UDP 接收异常: " + e.Message);
            }
        }
    }

    // ================= 发送逻辑 =================
    void SendSceneState()
    {
        SceneState state = new SceneState();
        GameObject[] interactables = GameObject.FindGameObjectsWithTag("Interactable");

        foreach (var obj in interactables)
        {
            SceneObject so = new SceneObject();
            so.name = obj.name;
            so.x = obj.transform.position.x;
            so.y = obj.transform.position.y;
            so.z = obj.transform.position.z;

            Renderer r = obj.GetComponent<Renderer>();
            if (r != null && r.material.HasProperty("_BaseColor"))
            {
                so.color = ColorUtility.ToHtmlStringRGB(r.material.color);
            }
            state.objects.Add(so);
        }

        string json = JsonUtility.ToJson(state);
        byte[] data = Encoding.UTF8.GetBytes(json);
        udpSender.Send(data, data.Length, pythonIP, pythonPort);
    }

    void SendToPython(string voiceText)
    {
        // 💡 修复：必须包装成 JSON，否则 Python 的 json.loads 会报错
        UserVoiceInput input = new UserVoiceInput { text = voiceText };
        string json = JsonUtility.ToJson(input);

        byte[] data = Encoding.UTF8.GetBytes(json);
        udpSender.Send(data, data.Length, pythonIP, pythonPort);
        Debug.Log($"📡 已发送语音给 Python: {json}");
    }

    // ================= 执行逻辑 =================
    private void ProcessCommand(string json)
    {
        try
        {
            // 把 JSON 解析成对象
            CommandData cmd = JsonUtility.FromJson<CommandData>(json);

            if (cmd.action == "create_panel")
            {
                GameObject panel = GameObject.CreatePrimitive(PrimitiveType.Cube);
                panel.transform.position = new Vector3(0, 1.5f, 2);
                panel.GetComponent<Renderer>().material.color = Color.red;
                panel.transform.localScale = new Vector3(1.0f, 0.5f, 0.05f);
                panel.tag = "Interactable"; // 💡 关键：生成后打个 Tag，下次感知就能抓取到它！
            }
            else if (cmd.action == "set_light")
            {
                Light mainLight = FindObjectOfType<Light>();
                if (mainLight != null)
                {
                    // 💡 修复：使用 Python 传来的真实 value
                    if (float.TryParse(cmd.value, out float intensity))
                    {
                        mainLight.intensity = intensity;
                    }
                    else
                    {
                        mainLight.intensity = 3.0f; // 解析失败时兜底
                    }
                }
            }
            else if (cmd.action == "move")
            {
                // 根据名字在场景中查找物体
                GameObject targetObj = GameObject.Find(cmd.target);
                if (targetObj != null)
                {
                    targetObj.transform.position = new Vector3(cmd.x, cmd.y, cmd.z);
                    Debug.Log($"✅ 成功将 {cmd.target} 移动到 ({cmd.x}, {cmd.y}, {cmd.z})");
                }
                else
                {
                    Debug.LogError($"❌ 找不到名为 {cmd.target} 的物体");
                }
            }
            else if (cmd.action == "change_color" || cmd.action == "set_color") 
            {
                GameObject targetObj = GameObject.Find(cmd.target);
                if (targetObj != null)
                {
                    Renderer r = targetObj.GetComponent<Renderer>();
                    if (r != null)
                    {
                        Color targetColor = Color.white; // 默认颜色兜底
                        bool isColorParsed = false;

                        // 1. 尝试解析 Hex 格式 (如 "#0000FF")
                        if (ColorUtility.TryParseHtmlString(cmd.value, out Color hexColor))
                        {
                            targetColor = hexColor;
                            isColorParsed = true;
                        }
                        // 2. 尝试解析英文/中文颜色名
                        else if (cmd.value.ToLower() == "blue" || cmd.value == "蓝色")
                        {
                            targetColor = Color.blue;
                            isColorParsed = true;
                        }
                        else if (cmd.value.ToLower() == "red" || cmd.value == "红色")
                        {
                            targetColor = Color.red;
                            isColorParsed = true;
                        }
                        else if (cmd.value.ToLower() == "green" || cmd.value == "绿色")
                        {
                            targetColor = Color.green;
                            isColorParsed = true;
                        }

                        if (isColorParsed)
                        {
                            // 💡 核心修复 2：完美兼容 URP 和标准管线
                            if (r.material.HasProperty("_BaseColor"))
                            {
                                r.material.SetColor("_BaseColor", targetColor);
                            }
                            if (r.material.HasProperty("_Color"))
                            {
                                r.material.SetColor("_Color", targetColor);
                            }
                            Debug.Log($"✅ 成功将 {cmd.target} 颜色修改为 {cmd.value}");
                        }
                        else
                        {
                            Debug.LogWarning($"⚠️ 无法识别的颜色值: {cmd.value}");
                        }
                    }
                    else
                    {
                        Debug.LogError($"❌ {cmd.target} 没有 Renderer 组件");
                    }
                }
                else
                {
                    Debug.LogError($"❌ 找不到名为 {cmd.target} 的物体");
                }
            }
            else
            {
                Debug.LogWarning($"⚠️ 未知的 Action: {cmd.action}"); // 💡 加上这句，以后没匹配上就能瞬间发现
            }
        

        }
        catch (Exception e)
        {
            Debug.LogError($"解析 Python 指令失败: {e.Message} \n原始数据: {json}");
        }
    }

    void OnApplicationQuit()
    {
        if (receiveThread != null) receiveThread.Abort();
        if (udpReceiver != null) udpReceiver.Close();
        if (udpSender != null) udpSender.Close();
    }
}