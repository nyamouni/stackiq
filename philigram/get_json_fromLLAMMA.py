from groq import Groq
import re
import json
import os 

def extraire_json_depuis_texte(texte):
    try:
        match = re.search(r"\{[\s\S]*\}", texte)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)
    except json.JSONDecodeError:
        return None
    return None

def get_instructions_llamma4():
    client_groq = os.getenv("client_groq")
    client = Groq(api_key=client_groq)


    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {
                "role": "system",
                "content": """Tu es un assistant IA expert en automatisation LinkedIn. Tu dois générer un plan d’actions pour un agent Python dans le but d’obtenir des contrats de prestation.
        Réponds TOUJOURS en JSON avec une clé 'actions'. Chaque action doit correspondre à une fonction Python parmi : 
        - ajouter_profils_cibles
        - ajouter_relations
        - actions_humaines_et_telecharger_profile
        - envoyer_un_message

        Le plan doit suivre une stratégie logique :
        1. Identifier les profils cibles
        2. Ajouter les profils
        3. Télécharger et analyser leurs profils
        4. Générer un message personnalisé
        5. Envoyer le message

        Inclue pour chaque action les paramètres nécessaires (ex: cible, localisation, contenu du message, etc.).

        Si une étape dépend d'une précédente (comme envoyer un message après téléchargement), respecte cet ordre logique."""
            },
            {
                "role": "user",
                "content": "Ajoute des CTO DATA SCIENCE à Lyon et envoie-leur un message personnalisé pour leur proposer un audit. Fais aussi un post public pour montrer ce service."
            }
        ],
        temperature=0.3,
    )

    content = response.choices[0].message.content
    plan = extraire_json_depuis_texte(content)

    if plan:
        print("\n PLAN EXTRACTED :")
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return plan
    else:
        print(" Impossible d'extraire un JSON valide.")
        return None

get_instructions_llamma4()
