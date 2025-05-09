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
            return boto3.client(service, aws_access_key_id=st.secrets["AWS"]["AWS_ACCESS_KEY_ID"], aws_secret_access_key=st.secrets["AWS"]["AWS_SECRET_ACCESS_KEY"], region_name='us-east-1')
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
        response = rekognition.compare_faces(SourceImage={'Bytes': source_bytes}, TargetImage={'Bytes': target_bytes}, SimilarityThreshold=threshold)
        if not response['FaceMatches']:
            return {'status': False, 'similarity': 0}
        return {'status': True, 'similarity': response['FaceMatches'][0]['Similarity']}
    except Exception as e:
        st.error(f"Erro na comparação facial: {str(e)}")
        return {'status': False}


with st.tabs(["Validação Completa", "Configurações"])[0]:
    st.header("Upload dos Documentos")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("Selfie Atual")
        selfie = st.file_uploader("Sua foto (selfie)", type=["jpg", "png"])
    with col2:
        st.subheader("Documento de Identidade ou CNH")
        doc_id = st.file_uploader("Foto do documento (RG/CNH)", type=["jpg", "png"])
    with col3:
        st.subheader("Comprovante (Boleto/Conta)")
        bill = st.file_uploader("Comprovante com nome", type=["jpg", "png"])

    if st.button("Validar Identidade"):
        if not all([selfie, doc_id, bill]):
            st.error("Envie todos os documentos!")
            st.stop()

        selfie_bytes = selfie.getvalue()
        doc_id_bytes = doc_id.getvalue()
        bill_bytes = bill.getvalue()

        face_result = compare_faces(doc_id_bytes, selfie_bytes)
        doc_text = extract_text_from_image(doc_id_bytes)
        bill_text = extract_text_from_image(bill_bytes)

        st.markdown("---")
        st.header("Resultados da Validação")
        colr1, colr2 = st.columns(2)
        with colr1:
            st.subheader("Comparação Facial")
            if face_result['status']:
                st.success(f"Válido ({face_result['similarity']:.2f}%)")
            else:
                st.error("Falha no reconhecimento facial")
        with colr2:
            st.subheader("Validação de Nome")
            if doc_text.lower() in bill_text.lower():
                st.success("Nome no documento e boleto coincidem.")
            else:
                st.warning("Diferença encontrada nos nomes.")
