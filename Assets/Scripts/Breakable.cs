using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class Breakable : MonoBehaviour
{
    public List<GameObject> brokenPieces;
    public float timeToBreak = 2f;
    public float timer = 0f;

    // Start is called before the first frame update
    void Start()
    {
        foreach (GameObject piece in brokenPieces)
        {
            piece.SetActive(false); // Deactivate all broken pieces at the start
        }
    }

    public void Break()
    {
        timer += Time.deltaTime;
        if (timer > timeToBreak)
        {
            foreach (GameObject piece in brokenPieces)
            {
                piece.SetActive(true); // Activate all broken pieces when the object is broken
                piece.transform.parent = null;
            }
            gameObject.SetActive(false); // Deactivate the original object

        }

    }

}
