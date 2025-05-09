import streamlit as st
import boto3
import re
from PIL import Image

st.set_page_config(
    page_title="FIAP - Validador Biométrico",
    page_icon="🆔",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🆔 Validador de Identidade FIAP")
st.markdown("""
**Validação em 3 etapas:**
1. 👀 Comparação facial (Selfie vs Documento)
2. ✍️ Verificação de nome (Documento vs Boleto)
3. 💡 Análise de Liveness (É uma pessoa real?)
""")
st.markdown("---")

def get_aws_client(service):
    return boto3.client(
        service,
        aws_access_key_id=st.secrets["AWS"]["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS"]["AWS_SECRET_ACCESS_KEY"],
        region_name='us-east-1'
    )

rekognition = get_aws_client('rekognition')
textract = get_aws_client('textract')

def extract_text_from_image(image_bytes):
    response = textract.detect_document_text(Document={'Bytes': image_bytes})
    return " ".join([item["Text"] for item in response["Blocks"] if item["BlockType"] == "LINE"])

def extract_name(text, doc_type):
    patterns = []
    if doc_type == "doc":
        patterns = [r'(?:Nome\s*/?\s*Name)[\s:]*([A-ZÀ-Ü][A-ZÀ-Üa-zà-ü\s]+)']
    elif doc_type == "cnh":
        patterns = [r'2\.\s*Nome\s*/?\s*Sobrenome[\s:]*([A-ZÀ-Ü][A-ZÀ-Üa-zà-ü\s]+)']
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            name = match.group(1).strip()
            return name.title()
    return None

tab1, tab2 = st.tabs(["Validação Completa", "Configurações"])

with tab1:
    st.header("1. Upload dos Documentos")
    col1, col2 = st.columns(2)
    with col1:
        selfie = st.file_uploader("📷 Selfie", type=["jpg", "png"])
    with col2:
        doc_id = st.file_uploader("🆔 Documento (RG/CNH)", type=["jpg", "png"])

    doc_type = st.selectbox("Tipo de Documento", ["RG", "CNH"])

    if st.button("Validar"):
        selfie_bytes = selfie.getvalue()
        doc_id_bytes = doc_id.getvalue()
        doc_text = extract_text_from_image(doc_id_bytes)
        doc_name = extract_name(doc_text, "cnh" if doc_type == "CNH" else "doc")

        if doc_name:
            st.success(f"Nome extraído: {doc_name}")
        else:
            st.error("Nome não encontrado no documento")
