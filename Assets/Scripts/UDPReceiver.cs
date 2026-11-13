using UnityEngine;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Collections.Concurrent;

public class UDPReceiver : MonoBehaviour
{
    private UdpClient udpServer;
    private Thread receiveThread;
    // 用于主线程和后台网络线程之间安全传递数据的队列
    private ConcurrentQueue<string> messageQueue = new ConcurrentQueue<string>();

    public int port = 5066; //  Python -> Unity
    public string pythonIP = "127.0.0.1";
    public int pythonPort = 5067;  // Unity -> Python
    private UdpClient udpSender;   // 用于向 Python 发送消息

    void Start()
    {
        // receive mesage from python   
        udpServer = new UdpClient(port);
        receiveThread = new Thread(new ThreadStart(ReceiveData));
        receiveThread.IsBackground = true; // 后台运行，不阻塞 Unity 退出
        receiveThread.Start();
        Debug.Log($"UDP 监听已启动，端口: {port}");
        // send message to python
        udpSender = new UdpClient();
    }

    private void ReceiveData()
    {
        while (true)
        {
            try
            {
                // 阻塞等待接收数据
                IPEndPoint anyIP = new IPEndPoint(IPAddress.Any, 0);
                byte[] data = udpServer.Receive(ref anyIP);
                string text = Encoding.UTF8.GetString(data);

                // 收到后，塞进队列，等待主线程去处理
                messageQueue.Enqueue(text);
            }
            catch (System.Exception e)
            {
                Debug.LogError("UDP 接收异常: " + e.Message);
            }
        }
    }

    void Update()
    {
        // 在主线程 (Update) 中处理队列里的消息
        // Unity 规定：不能在后台线程直接操作 GameObject 或 Transform
        while (messageQueue.TryDequeue(out string message))
        {
            Debug.Log($"收到 Python 消息: {message}");
            ProcessCommand(message);
        }
        //
        if (Input.GetKeyDown(KeyCode.Space))
        {
            string userVoice = "帮我把灯光调暗一点。";
            SendToPython(userVoice);
        }
    }

    private void ProcessCommand(string json)
    {
        // 解析 JSON。为了简单，这里直接匹配关键字，实际项目中用 JsonUtility.FromJson
        if (json.Contains("create_panel"))
        {
            // 在 Unity 里生成一个红色的 Cube 模拟面板
            GameObject panel = GameObject.CreatePrimitive(PrimitiveType.Cube);
            panel.transform.position = new Vector3(0, 1.5f, 2); // 放在用户正前方
            panel.GetComponent<Renderer>().material.color = Color.red;
            panel.transform.localScale = new Vector3(1.0f, 0.5f, 0.05f); // 扁平的面板
        }
        else if (json.Contains("set_light"))
        {
            // 调节场景主灯光
            Light mainLight = FindObjectOfType<Light>();
            if (mainLight != null)
            {
                mainLight.intensity = 3.0f;
            }
        }
    }


    void SendToPython(string message)
    {
        byte[] data = Encoding.UTF8.GetBytes(message);
        udpSender.Send(data, data.Length, pythonIP, pythonPort);
        Debug.Log($"📡 已发送给 Python: {message}");
    }

    void OnApplicationQuit()
    {
        // 关闭时清理资源，防止端口占用
        if (receiveThread != null)
           receiveThread.Abort();
        if (udpServer != null)
            udpServer.Close();
        if (udpSender != null)
            udpSender.Close();
    }
}