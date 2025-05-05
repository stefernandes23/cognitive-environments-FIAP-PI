import streamlit as st
from PIL import Image
import boto3
import os

st.set_page_config(
    page_title="Validador Biométrico FIAP",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

def configure_aws():
    return boto3.client(
        'rekognition',
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
        region_name='us-east-1'
    )

def analyze_face(image_bytes):
    rekognition = configure_aws()
    try:
        response = rekognition.detect_faces(
            Image={'Bytes': image_bytes},
            Attributes=['ALL']
        )
        return response['FaceDetails'][0] if response['FaceDetails'] else None
    except Exception as e:
        st.error(f"Erro na análise: {str(e)}")
        return None

def main():
    st.title("🔍 Validação Facial com AWS Rekognition")
    
    uploaded_file = st.file_uploader(
        "Selecione uma imagem (JPEG/PNG):",
        type=["jpg", "jpeg", "png"]
    )

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption='Imagem enviada', width=300)
        
        with st.spinner('Analisando...'):
            img_bytes = uploaded_file.getvalue()
            face_details = analyze_face(img_bytes)
        
        if face_details:
            st.success("Análise concluída!")
            
            tab1, tab2 = st.tabs(["Atributos", "Detalhes"])
            
            with tab1:
                st.subheader("Atributos Principais")
                cols = st.columns(2)
                cols[0].metric("Confiança", f"{face_details['Confidence']:.2f}%")
                cols[1].metric("Idade", f"{face_details['AgeRange']['Low']}-{face_details['AgeRange']['High']} anos")
                st.progress(face_details['Confidence']/100)
                
            with tab2:
                st.subheader("Detalhes Completos")
                st.json(face_details)

if __name__ == "__main__":
    main()