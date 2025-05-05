import streamlit as st
import boto3
import re
from PIL import Image

# Page configuration
st.set_page_config(
    page_title="FIAP - Validador Biométrico",
    page_icon="🆔",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🆔 Validador de Identidade FIAP")
st.markdown("""
**Validação em 3 etapas:**
1. Confronto facial (Selfie vs Documento)
2. Verificação de nome (Documento vs Boleto)
3. Análise de vitalidade
""")
st.markdown("---")

# Secure AWS client function
def get_aws_client(service):
    try:
        if "AWS" in st.secrets:
            return boto3.client(
                service,
                aws_access_key_id=st.secrets["AWS"]["AWS_ACCESS_KEY_ID"],
                aws_secret_access_key=st.secrets["AWS"]["AWS_SECRET_ACCESS_KEY"],
                region_name='us-east-1'
            )
        elif "aws_access_key_id" in st.secrets:
            return boto3.client(
                service,
                aws_access_key_id=st.secrets["aws_access_key_id"],
                aws_secret_access_key=st.secrets["aws_secret_access_key"],
                region_name='us-east-1'
            )
        raise KeyError("AWS credentials not found")
    except Exception as e:
        st.error(f"""
        🚨 AWS Connection Error: {str(e)}
        
        Please configure your credentials:
        1. Locally: create `.streamlit/secrets.toml`
        2. Cloud: Go to Settings → Secrets
        
        Required format:
        ```toml
        [AWS]
        AWS_ACCESS_KEY_ID = "your_key"
        AWS_SECRET_ACCESS_KEY = "your_secret"
        ```
        """)
        st.stop()

# Initialize AWS clients
rekognition = get_aws_client('rekognition')
textract = get_aws_client('textract')

def extract_text_from_image(image_bytes):
    try:
        response = textract.detect_document_text(Document={'Bytes': image_bytes})
        return " ".join([item["Text"] for item in response["Blocks"] if item["BlockType"] == "LINE"])
    except Exception as e:
        st.error(f"OCR Error: {str(e)}")
        return ""

def compare_faces(source_bytes, target_bytes, threshold=90):
    try:
        response = rekognition.compare_faces(
            SourceImage={'Bytes': source_bytes},
            TargetImage={'Bytes': target_bytes},
            SimilarityThreshold=threshold
        )
        if not response['FaceMatches']:
            return {'status': False, 'similarity': 0}
        return {
            'status': True,
            'similarity': response['FaceMatches'][0]['Similarity'],
            'face': response['FaceMatches'][0]['Face']
        }
    except Exception as e:
        st.error(f"Face comparison error: {str(e)}")
        return {'status': False, 'error': str(e)}

def detect_liveness(image_bytes):
    try:
        response = rekognition.detect_faces(
            Image={'Bytes': image_bytes},
            Attributes=['ALL']
        )
        if not response['FaceDetails']:
            return False, "No face detected"
        
        face = response['FaceDetails'][0]
        eyes_open = face['EyesOpen']['Value']
        smile = face['Smile']['Value']
        
        vital = eyes_open and not smile
        details = f"Eyes {'open' if eyes_open else 'closed'}, {'smiling' if smile else 'neutral'}"
        return vital, details
    except Exception as e:
        st.error(f"Liveness detection error: {str(e)}")
        return False, "Analysis error"

def extract_name(text, doc_type):
    if doc_type == "doc":
        patterns = [
            r'(?:Nome\s*[/]?\s*Name)[\s:]*([A-ZÀ-Ü][A-ZÀ-Üa-zà-ü\s]+?)(?=\n|$|\d|CPF|Sexo|Nome Social)',
            r'Nome\s*[/]?\s*Name[\s:]*([A-ZÀ-Ü][A-ZÀ-Üa-zà-ü\s]+)',
            r'Nome[\s:]*([A-ZÀ-Ü][A-ZÀ-Üa-zà-ü\s]+)(?=\s*Nome Social)'
        ]
    else:
        patterns = [
            r'^([A-ZÀ-Ü][A-ZÀ-Üa-zà-ü\s]+?)(?=\n|\d|Código|Vencimento)',
            r'(?:Cliente|Titular|Beneficiário)[\s:]*([A-ZÀ-Ü][A-ZÀ-Üa-zà-ü\s]+)'
        ]
    
    blacklist = {
        "REPUBLICA", "FEDERATIVA", "BRASIL", "DOCUMENTO", "IDENTIDADE",
        "CPF", "RG", "CNH", "ORGAO", "EXPEDICAO", "VALIDADE", "GOVERNO",
        "ESTADO", "SEGURANÇA", "PÚBLICA", "DISTRITO", "FEDERAL", "SECRETARIA",
        "CARTEIRA", "NACIONAL", "VALOR", "VENCIMENTO", "CLARO", "FATURA"
    }
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            name = match.group(1).strip()
            name = re.sub(r'\s*Nome Social.*', '', name, flags=re.IGNORECASE)
            filtered_name = ' '.join([part for part in name.split() 
                                    if part.upper() not in blacklist and len(part) > 2])
            if len(filtered_name.split()) >= 2:
                return filtered_name.title()
    
    return None

# Main interface
tab1, tab2 = st.tabs(["Validação Completa", "Configurações"])

with tab1:
    st.header("1. Upload dos Documentos")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("📷 Selfie Atual")
        selfie = st.file_uploader("Sua foto atual (selfie)", type=["jpg", "png"])
        if selfie:
            st.image(selfie, use_container_width=True)

    with col2:
        st.subheader("🆔 Documento de Identidade")
        doc_id = st.file_uploader("Foto do seu documento (RG/CNH)", type=["jpg", "png"])
        if doc_id:
            st.image(doc_id, use_column_width=True)

    with col3:
        st.subheader("💳 Comprovante (Boleto/Conta)")
        bill = st.file_uploader("Comprovante com seu nome", type=["jpg", "png"])
        if bill:
            st.image(bill, use_column_width=True)

    if st.button("Validar Identidade", type="primary"):
        if not all([selfie, doc_id, bill]):
            st.error("Por favor, envie todos os documentos!")
            st.stop()

        with st.spinner("Process
