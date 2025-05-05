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
                    emotions = sorted(face['Emotions'], key=lambda x: x['Confidence'], reverse=True)
                    st.subheader("Análise Emocional")
                    for emotion in emotions[:3]:
                        st.progress(int(emotion['Confidence']), 
                                  f"{emotion['Type']}: {emotion['Confidence']:.1f}%")
            else:
                st.error("Nenhum rosto detectado no documento. Por favor, tente novamente.")

with tab2:
    st.header("2. Verificação com Selfie")
    
    if 'doc_bytes' not in st.session_state:
        st.warning("Por favor, carregue um documento válido na aba 'Documento' primeiro.")
    else:
        verification_method = st.radio("Método de verificação:", 
                                     ["Tirar foto", "Carregar arquivo"])
        
        if verification_method == "Tirar foto":
            selfie = st.camera_input("Tire uma selfie para verificação")
            if selfie:
                st.session_state.selfie_bytes = selfie.getvalue()
        else:
            selfie_file = st.file_uploader("Carregue sua selfie", type=["jpg", "jpeg", "png"])
            if selfie_file:
                st.session_state.selfie_bytes = selfie_file.getvalue()
                st.image(Image.open(selfie_file), caption="Selfie carregada", use_column_width=True)
        
        if 'selfie_bytes' in st.session_state:
            confidence = st.slider("Limiar de confiança", 70, 100, 85)
            
            if st.button("Verificar Identidade"):
                with st.spinner("Comparando rostos..."):
                    match, details = compare_faces(
                        st.session_state.doc_bytes,
                        st.session_state.selfie_bytes,
                        confidence
                    )
                
                if match:
                    similarity = details[0]['Similarity']
                    st.balloons()
                    st.success(f"✅ Identidade verificada! Similaridade: {similarity:.2f}%")
                    
                    # Análise adicional da selfie
                    selfie_analysis = analyze_document_face(st.session_state.selfie_bytes)
                    if selfie_analysis:
                        st.subheader("Análise da Selfie")
                        face = selfie_analysis[0]
                        st.write(f"**Olhos abertos:** {'Sim' if face['EyesOpen']['Value'] else 'Não'} ({face['EyesOpen']['Confidence']:.1f}%)")
                        st.write(f"**Sorriso:** {'Sim' if face['Smile']['Value'] else 'Não'} ({face['Smile']['Confidence']:.1f}%)")
                else:
                    st.error("❌ Identidade não verificada. Por favor, tente novamente.")

with tab3:
    st.header("3. Busca em Multidão")
    
    if 'doc_bytes' not in st.session_state:
        st.warning("Por favor, carregue um documento válido na aba 'Documento' primeiro.")
    else:
        crowd_file = st.file_uploader("Carregue foto com múltiplas pessoas", type=["jpg", "jpeg", "png"])
        
        if crowd_file:
            col1, col2 = st.columns(2)
            with col1:
                crowd_img = Image.open(crowd_file)
                st.image(crowd_img, caption="Imagem da multidão", use_column_width=True)
            
            confidence = st.slider("Limiar de confiança para busca", 70, 100, 80)
            
            if st.button("Procurar na Multidão"):
                with st.spinner("Analisando imagem..."):
                    crowd_bytes = crowd_file.getvalue()
                    faces = detect_faces_in_image(crowd_bytes)
                    draw = ImageDraw.Draw(crowd_img)
                    found = False
                    
                    for face in faces:
                        box = face['BoundingBox']
                        width, height = crowd_img.size
                        left = int(box['Left'] * width)
                        top = int(box['Top'] * height)
                        right = left + int(box['Width'] * width)
                        bottom = top + int(box['Height'] * height)
                        
                        # Recortar e comparar cada rosto
                        face_crop = crowd_img.crop((left, top, right, bottom))
                        with io.BytesIO() as buffer:
                            face_crop.save(buffer, format="JPEG")
                            face_bytes = buffer.getvalue()
                        
                        match, details = compare_faces(st.session_state.doc_bytes, face_bytes, confidence)
                        
                        if match:
                            draw.rectangle([left, top, right, bottom], outline="green", width=5)
                            draw.text((left, top-30), f"Match: {details[0]['Similarity']:.1f}%", fill="green")
                            found = True
                        else:
                            draw.rectangle([left, top, right, bottom], outline="red", width=2)
                    
                    with col2:
                        st.image(crowd_img, caption="Resultado da busca", use_column_width=True)
                        if found:
                            st.success("Pessoa encontrada na multidão!")
                        else:
                            st.warning("Pessoa não encontrada na multidão.")

# Rodapé
st.markdown("---")
st.caption("FIAP Cognitive Environments | © 2023 | Versão 2.0")
