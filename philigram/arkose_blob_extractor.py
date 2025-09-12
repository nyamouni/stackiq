import time
import json

def get_blob_from_network(driver):
    print("🧪 Surveillance du trafic réseau pour détecter un blob Arkose...")

    driver.requests.clear()
    time.sleep(10)  # ou ajuste le délai en fonction du temps de chargement

    for request in driver.requests:
        if request.response:
            if 'arkose' in request.url or 'funcaptcha' in request.url:
                if request.method == 'POST':
                    try:
                        body = request.body.decode()
                        if 'blob' in body:
                            blob_data = json.loads(body)
                            blob = blob_data.get('blob')
                            if blob:
                                print("✅ Blob Arkose récupéré depuis le trafic réseau !")
                                return blob
                    except Exception as e:
                        print(f"⚠️ Erreur lors de l'analyse d'une requête : {e}")

    print("❌ Aucun blob détecté dans le trafic réseau.")
    return None
