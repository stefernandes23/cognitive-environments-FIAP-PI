import streamlit as st
import boto3
from PIL import Image, ImageDraw
import io
import time

# Configuração da página
st.set_page_config(
    page_title="FIAP - Validador Biométrico Avançado",
    page_icon="🆔",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título e descrição
st.title("🆔 Validador Biométrico FIAP")
st.markdown("""
**Sistema de verificação de identidade em três etapas:**
1. Análise facial em documentos
2. Comparação com selfie
3. Detecção em multidões
""")
st.markdown("---")

# Inicialização do cliente Rekognition
@st.cache_resource
def get_rekognition_client():
    return boto3.client(
        'rekognition',
        aws_access_key_id=st.secrets["AWS"]["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS"]["AWS_SECRET_ACCESS_KEY"],
        region_name='us-east-1'
    )

rekognition_client = get_rekognition_client()

# Funções principais
def analyze_document_face(image_bytes):
    """Analisa o rosto em um documento de identidade"""
    try:
        response = rekognition_client.detect_faces(
            Image={'Bytes': image_bytes},
            Attributes=['ALL']
        )
        return response['FaceDetails'] if response['FaceDetails'] else None
    except Exception as e:
        st.error(f"Erro na análise do documento: {str(e)}")
        return None

def compare_faces(source_bytes, target_bytes, threshold=80):
    """Compara dois rostos e retorna similaridade"""
    try:
        response = rekognition_client.compare_faces(
            SourceImage={'Bytes': source_bytes},
            TargetImage={'Bytes': target_bytes},
            SimilarityThreshold=threshold
        )
        return (True, response['FaceMatches']) if response['FaceMatches'] else (False, None)
    except Exception as e:
        st.error(f"Erro na comparação facial: {str(e)}")
        return False, None

def detect_faces_in_image(image_bytes):
    """Detecta múltiplos rostos em uma imagem"""
    try:
        response = rekognition_client.detect_faces(
            Image={'Bytes': image_bytes},
            Attributes=['DEFAULT']
        )
        return response['FaceDetails']
    except Exception as e:
        st.error(f"Erro na detecção de rostos: {str(e)}")
        return []

# Interface principal
tab1, tab2, tab3 = st.tabs(["Documento", "Selfie", "Multidão"])

with tab1:
    st.header("1. Análise de Documento")
    doc_file = st.file_uploader("Carregue seu documento de identidade", type=["jpg", "jpeg", "png"])
    
    if doc_file:
        col1, col2 = st.columns(2)
        with col1:
            doc_img = Image.open(doc_file)
            st.image(doc_img, caption="Documento carregado", use_column_width=True)
        
        with st.spinner("Analisando documento..."):
            doc_bytes = doc_file.getvalue()
            face_details = analyze_document_face(doc_bytes)
            
            if face_details:
                st.session_state.doc_bytes = doc_bytes
                with col2:
                    st.success("✅ Rosto detectado no documento")
                    face = face_details[0]
                    
                    # Informações demográficas
                    st.subheader("Informações Demográficas")
                    gender = face['Gender']['Value']
                    gender_conf = face['Gender']['Confidence']
                    st.write(f"**Gênero:** {gender} ({gender_conf:.1f}% de confiança)")
                    
                    age_range = f"{face['AgeRange']['Low']}-{face['AgeRange']['High']}"
                    st.write(f"**Faixa etária:** {age_range} anos")
                    
                    # Emoções
                    emotions =
