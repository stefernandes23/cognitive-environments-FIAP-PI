import streamlit as st
import boto3
from PIL import Image
import os
import tempfile
import matplotlib.pyplot as plt
import sys

# Configuração da página
st.set_page_config(
    page_title="FIAP - Cognitive Environments",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título do aplicativo
st.title("🔍 Validação Biométrica com AWS Rekognition")
st.markdown("---")

# Funções do seu notebook adaptadas
def configure_aws():
    return boto3.client(
        'rekognition',
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
        region_name='us-east-1'
    )

def validar_imagem(image_bytes, extensoes_validas=('.jpg', '.jpeg', '.png'), 
                  tamanho_min=(100, 100), tamanho_max=(5000, 5000), 
                  tamanho_max_mb=5):
    try:
        # Verifica tamanho do arquivo
        if len(image_bytes) / (1024 ** 2) > tamanho_max_mb:
            return False, "Arquivo excede tamanho permitido"
        
        # Verifica extensão (assumindo que o upload já filtra)
        
        # Verifica dimensões
        with Image.open(io.BytesIO(image_bytes)) as img:
            width, height = img.size
            if not (tamanho_min[0] <= width <= tamanho_max[0]) or not (tamanho_min[1] <= height <= tamanho_max[1]):
                return False, "Dimensões fora dos limites"
            
            img.verify()
        
        return True, "Imagem válida"
    
    except Exception as e:
        return False, f"Erro na validação: {str(e)}"

def analyze_face(image_bytes):
    rekognition = configure_aws()
    try:
        response = rekognition.detect_faces(
            Image={'Bytes': image_bytes},
            Attributes=['ALL']
        )
        return response['FaceDetails'][0] if response['FaceDetails'] else None
    except Exception as e:
        st.error(f"Erro na análise facial: {str(e)}")
        return None

def compare_faces(source_bytes, target_bytes, similarity_threshold=90):
    rekognition = configure_aws()
    try:
        response = rekognition.compare_faces(
            SourceImage={'Bytes': source_bytes},
            TargetImage={'Bytes': target_bytes},
            SimilarityThreshold=similarity_threshold
        )
        
        if not response['FaceMatches']:
            return {'status': 'Não autenticada', 'similaridade': response['UnmatchedFaces'][0]['Similarity'] if response['UnmatchedFaces'] else 0}
        
        best_match = max(response['FaceMatches'], key=lambda x: x['Similarity'])
        return {
            'status': 'Autenticada',
            'similaridade': best_match['Similarity'],
            'detalhes': best_match['Face']
        }
    except Exception as e:
        st.error(f"Erro na comparação facial: {str(e)}")
        return {'status': 'Erro', 'detalhes': str(e)}

# Interface principal
tab1, tab2 = st.tabs(["Análise Facial", "Comparação de Imagens"])

with tab1:
    st.header("Análise de Atributos Faciais")
    uploaded_file = st.file_uploader("Envie uma foto para análise:", type=["jpg", "jpeg", "png"])
    
    if uploaded_file:
        image_bytes = uploaded_file.getvalue()
        
        # Validação da imagem
        is_valid, validation_msg = validar_imagem(image_bytes)
        if not is_valid:
            st.error(validation_msg)
            st.stop()
        
        col1, col2 = st.columns(2)
        with col1:
            st.image(image_bytes, caption="Imagem enviada", use_column_width=True)
        
        with st.spinner('Analisando atributos faciais...'):
            face_details = analyze_face(image_bytes)
        
        if face_details:
            with col2:
                st.success("Análise concluída!")
                
                # Mostrar atributos principais
                st.subheader("Atributos Detectados")
                st.metric("Confiança", f"{face_details['Confidence']:.2f}%")
                st.metric("Idade Estimada", f"{face_details['AgeRange']['Low']}-{face_details['AgeRange']['High']} anos")
                st.metric("Gênero", f"{face_details['Gender']['Value']} ({face_details['Gender']['Confidence']:.2f}%)")
                
                # Emoções
                emotions = sorted(face_details['Emotions'], key=lambda x: x['Confidence'], reverse=True)
                st.subheader("Emoções Detectadas")
                for emotion in emotions[:3]:  # Mostrar apenas as 3 principais
                    st.progress(emotion['Confidence']/100, text=f"{emotion['Type']}: {emotion['Confidence']:.2f}%")
                
                # Detalhes adicionais
                with st.expander("Ver detalhes técnicos"):
                    st.json(face_details)

with tab2:
    st.header("Comparação Facial")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Imagem de Referência")
        ref_image = st.file_uploader("Selecione a imagem de referência:", type=["jpg", "jpeg", "png"], key="ref")
    
    with col2:
        st.subheader("Imagem para Comparar")
        target_image = st.file_uploader("Selecione a imagem para comparar:", type=["jpg", "jpeg", "png"], key="target")
    
    if ref_image and target_image:
        similarity_threshold = st.slider("Limiar de Similaridade (%)", 70, 100, 90)
        
        if st.button("Comparar Imagens"):
            with st.spinner('Processando comparação...'):
                ref_bytes = ref_image.getvalue()
                target_bytes = target_image.getvalue()
                
                result = compare_faces(ref_bytes, target_bytes, similarity_threshold)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.image(ref_bytes, caption="Imagem de Referência", use_column_width=True)
                with col2:
                    st.image(target_bytes, caption="Imagem para Comparar", use_column_width=True)
                
                if result['status'] == 'Autenticada':
                    st.success(f"✅ Correspondência encontrada! Similaridade: {result['similaridade']:.2f}%")
                    st.balloons()
                else:
                    st.error(f"❌ Não autenticado. Similaridade: {result['similaridade']:.2f}%")

# Barra lateral com configurações
with st.sidebar:
    st.header("Configurações")
    st.info("Configure os parâmetros de análise")
    
    st.markdown("---")
    st.write("Desenvolvido por [Seu Nome]")
    st.write("FIAP - Cognitive Environments")

# Rodapé
st.markdown("---")
st.caption("© 2023 FIAP - Todos os direitos reservados")