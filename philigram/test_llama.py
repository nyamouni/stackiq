from langchain_community.document_loaders import PyPDFLoader
from langchain_huggingface import HuggingFaceEndpoint
from langchain_core.prompts import PromptTemplate
import os
# 1. Charger le PDF
loader = PyPDFLoader("Profile.pdf")
documents = loader.load()
text = "\n".join([doc.page_content for doc in documents])

# 2. Hugging Face Endpoint - modèle compatible text-generation
llm = HuggingFaceEndpoint(
    repo_id="HuggingFaceH4/zephyr-7b-beta",  
    huggingfacehub_api_token=os.getenv("huggingfacehub_api_token"),
    temperature=0.1,
    max_new_tokens=512
)

# 3. Prompt
prompt = PromptTemplate.from_template(
    "Voici un profil LinkedIn :\n\n{text}\n\nQuelles sont les compétences et les expériences de ce candidat ?"
)

# 4. Chaine moderne
chain = prompt | llm

# 5. Inference
response = chain.invoke({"text": text})

# 6. Affichage
print(response)
