using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;


public class MeteorPistol : MonoBehaviour
{
    public ParticleSystem particles;
    public LayerMask layerMask;
    public Transform shootSource;
    public float shootDistance = 10f;

    private bool rayActive = false;
    // Start is called before the first frame update
    void Start()
    {
        XRGrabInteractable grabInteractable = GetComponent<XRGrabInteractable>();
        grabInteractable.activated.AddListener(x=>StartShoot());
        grabInteractable.deactivated.AddListener(x=>StopShoot());
      
    }

    public void StartShoot()
    {
       particles.Play();
       rayActive = true;
    }
    public void StopShoot()
    {
        particles.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
        rayActive = false;
    }
    // Update is called once per frame
    void Update()
    {
        if (rayActive)
        {
            RayCastCheck();
        }
    }

    private void RayCastCheck()
    {
        RaycastHit hit;
        if (Physics.Raycast(shootSource.position, shootSource.forward, out hit, shootDistance, layerMask))
        {
            // Handle hit
            hit.transform.gameObject.SendMessage("Break", SendMessageOptions.DontRequireReceiver);
        }
    }
}
