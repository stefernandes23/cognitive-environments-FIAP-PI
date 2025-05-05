import streamlit as st
import boto3
from PIL import Image
import os
import io
import tempfile
import matplotlib.pyplot as plt
import sys
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="FIAP - Validador Biométrico",
    page_icon="🆔",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título do aplicativo
st.title("🆔 Validador de Identidade FIAP")
st.markdown("""
**Validação em 3 etapas:**
1. Confronto facial (Selfie vs Documento)
2. Verificação de nome (Documento vs Boleto)
3. Análise de vitalidade
""")
st.markdown("---")

# Configuração AWS (usando secrets do Streamlit)
def get_aws_client():
    return boto3.client(
        'rekognition',
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
        region_name='us-east-1'
    )

# Funções
def extract_text_from_image(image_bytes):
    textract = boto3.client(
        'textract',
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
        region_name='us-east-1'
    )
    try:
        response = textract.detect_document_text(Document={'Bytes': image_bytes})
        return " ".join([item["Text"] for item in response["Blocks"] if item["BlockType"] == "LINE"])
    except Exception as e:
        st.error(f"Erro no OCR: {str(e)}")
        return ""

def compare_faces(source_bytes, target_bytes, threshold=90):
    rekognition = get_aws_client()
    try:
        response = rekognition.compare_faces(
            SourceImage={'Bytes': source_bytes},
            TargetImage={'Bytes': target_bytes},
            SimilarityThreshold=threshold
        )
        if not response['FaceMatches']:
            return {'status': False, 'similarity': response['UnmatchedFaces'][0]['Similarity'] if response['UnmatchedFaces'] else 0}
        return {
            'status': True,
            'similarity': response['FaceMatches'][0]['Similarity'],
            'face': response['FaceMatches'][0]['Face']
        }
    except Exception as e:
        st.error(f"Erro na comparação facial: {str(e)}")
        return {'status': False, 'error': str(e)}

def detect_liveness(image_bytes):
    rekognition = get_aws_client()
    try:
        response = rekognition.detect_faces(
            Image={'Bytes': image_bytes},
            Attributes=['ALL']
        )
        if not response['FaceDetails']:
            return False

        face = response['FaceDetails'][0]
        return (
            face.get("Smile", {}).get("Value") and
            face.get("EyesOpen", {}).get("Value")
        )
    except Exception as e:
        st.error(f"Erro na detecção de vitalidade: {str(e)}")
        return False


def extract_name(text):
    import re
    matches = re.findall(r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)', text)
    return matches[0] if matches else None

# Interface principal
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
        
        with st.spinner("Processando validação..."):
            # Etapa 1: Comparação facial
            selfie_bytes = selfie.getvalue()
            doc_id_bytes = doc_id.getvalue()
            
            face_result = compare_faces(doc_id_bytes, selfie_bytes)
            
            # Etapa 2: Extração de texto
            doc_text = extract_text_from_image(doc_id_bytes)
            bill_text = extract_text_from_image(bill.getvalue())
            
            doc_name = extract_name(doc_text)
            bill_name = extract_name(bill_text)

            st.write("Texto do documento extraído:", doc_text)
            st.write("Texto do boleto extraído:", bill_text)

            
            # Etapa 3: Detecção de vitalidade
            liveness = detect_liveness(selfie_bytes)
            
            # Resultados
            st.markdown("---")
            st.header("Resultados da Validação")
            
            cols = st.columns(3)
            
            with cols[0]:
                st.subheader("👤 Confronto Facial")
                if face_result['status']:
                    st.success(f"✅ Correspondência válida ({face_result['similarity']:.2f}%)")
                else:
                    st.error(f"❌ Falha na correspondência ({face_result.get('similarity', 0):.2f}%)")
            
            with cols[1]:
                st.subheader("📝 Confronto de Nome")
                if doc_name and bill_name and doc_name.lower() == bill_name.lower():
                    st.success(f"✅ Nomes coincidem\n\nDocumento: {doc_name}\nBoleto: {bill_name}")
                else:
                    st.error(f"❌ Nomes diferentes\n\nDocumento: {doc_name or 'Não encontrado'}\nBoleto: {bill_name or 'Não encontrado'}")
            
            with cols[2]:
                st.subheader("💡 Detecção de Vitalidade")
                if liveness:
                    st.success("✅ Pessoa real detectada")
                else:
                    st.warning("⚠️ Não foi possível confirmar vitalidade")
            
            # Verificação final
            if face_result['status'] and (doc_name and bill_name and doc_name.lower() == bill_name.lower()) and liveness:
                st.balloons()
                st.success("🎉 Identidade validada com sucesso!")
            else:
                st.error("Falha na validação. Por favor, verifique os documentos.")

with tab2:
    st.header("Configurações")
    confidence_threshold = st.slider("Limiar de confiança para comparação facial", 70, 100, 90)
    st.info("Ajuste os parâmetros de validação conforme necessário")

# Rodapé
st.markdown("---")
st.caption("FIAP Cognitive Environments | © 2023 | Versão 1.0")

# Para executar local:
# streamlit run app_streamlit.py
