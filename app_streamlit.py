import streamlit as st
import boto3
import re
from PIL import Image

st.set_page_config(page_title="FIAP - Validador Biométrico", page_icon="🆔", layout="wide", initial_sidebar_state="expanded")
st.title("🆔 Validador de Identidade FIAP")
st.markdown("""
**Validação em 3 etapas:**
1. 👀 Comparação facial (Selfie vs Documento)
2. ✍️ Verificação de nome (Documento vs Boleto)
3. 💡 Análise de Liveness (É uma pessoa real?)
""")
st.markdown("---")

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
        raise KeyError("Credenciais AWS não encontradas")
    except Exception as e:
        st.error(f"Erro de conexão com AWS: {str(e)}")
        st.stop()

rekognition = get_aws_client('rekognition')
textract = get_aws_client('textract')

def extract_text_from_image(image_bytes):
    try:
        response = textract.detect_document_text(Document={'Bytes': image_bytes})
        return " ".join([item["Text"] for item in response["Blocks"] if item["BlockType"] == "LINE"])
    except Exception as e:
        st.error(f"Erro no OCR: {str(e)}")
        return ""


def compare_faces(source_bytes, target_bytes, threshold=90):
    try:
        response = rekognition.compare_faces(
            SourceImage={'Bytes': source_bytes},
            TargetImage={'Bytes': target_bytes},
            SimilarityThreshold=threshold
        )
        if response['FaceMatches']:
            similarity = response['FaceMatches'][0]['Similarity']
            return {'status': True, 'similarity': similarity}
        return {'status': False, 'similarity': 0}
    except Exception as e:
        st.error(f"Erro na comparação facial: {str(e)}")
        return {'status': False, 'similarity': 0}


def detect_liveness(image_bytes):
    try:
        response = rekognition.detect_faces(
            Image={'Bytes': image_bytes},
            Attributes=['ALL']
        )
        if response['FaceDetails']:
            face = response['FaceDetails'][0]
            eyes_open = face['EyesOpen']['Value']
            smile = face['Smile']['Value']
            return eyes_open, smile
        return False, False
    except Exception as e:
        st.error(f"Erro na detecção de Liveness: {str(e)}")
        return False, False


def extract_name(text):
    patterns = [
        r'(?:Nome|Name)[:\s]+([A-ZÀ-Üa-zà-ü\s]+)',  # Nome padrão
        r'\bNOME[:\s]+([A-ZÀ-Üa-zà-ü\s]+)',          # CNH padrão
        r'\bNome Completo[:\s]+([A-ZÀ-Üa-zà-ü\s]+)'  # Formato alternativo
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return "Nome não encontrado"

selfie = st.file_uploader("Selfie", type=["jpg", "png"])
doc_id = st.file_uploader("Documento (RG/CNH)", type=["jpg", "png"])
bill = st.file_uploader("Boleto", type=["jpg", "png"])

if st.button("Validar"):
    if not all([selfie, doc_id, bill]):
        st.error("Envie todos os arquivos!")
        st.stop()

    selfie_bytes = selfie.getvalue()
    doc_id_bytes = doc_id.getvalue()
    bill_bytes = bill.getvalue()

    face_result = compare_faces(doc_id_bytes, selfie_bytes)
    doc_text = extract_text_from_image(doc_id_bytes)
    bill_text = extract_text_from_image(bill_bytes)
    liveness, smile = detect_liveness(selfie_bytes)

    doc_name = extract_name(doc_text)
    bill_name = extract_name(bill_text)

    st.write("**Comparação Facial**")
    st.write(f"Válido: {face_result['status']}, Similaridade: {face_result['similarity']}%")

    st.write("**Validação de Nome**")
    if doc_name != "Nome não encontrado" and bill_name != "Nome não encontrado":
        if doc_name.lower() == bill_name.lower():
            st.success("Nomes coincidem!")
        else:
            st.warning("Diferença nos nomes!")
        st.write(f"Documento: {doc_name}")
        st.write(f"Boleto: {bill_name}")
    else:
        st.error("Nome não encontrado em um dos arquivos!")

    st.write("**Liveness**")
    if liveness:
        st.success("Pessoa real detectada!")
    else:
        st.error("Falha na detecção de liveness!")
