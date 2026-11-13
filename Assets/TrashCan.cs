using UnityEngine;

public class TrashCan : MonoBehaviour
{
    // Start is called before the first frame update
    void Start()
    {
     GetComponent<TriggerZone>().OnEnterEvent.AddListener(InsideTrash);  
    }

   public void InsideTrash(GameObject go)
    {
        go.SetActive(false);
    }
}
