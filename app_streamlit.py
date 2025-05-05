import streamlit as st
import boto3
import re
from PIL import Image

# Configuração da página
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

# AWS Rekognition client
def get_aws_client():
    return boto3.client(
        'rekognition',
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
        region_name='us-east-1'
    )

# Função para OCR com Textract
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

# Função para comparar rostos
def compare_faces(source_bytes, target_bytes, threshold=90):
    rekognition = get_aws_client()
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
        st.error(f"Erro na comparação facial: {str(e)}")
        return {'status': False, 'error': str(e)}

# Detecção de vitalidade simples
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

# Extrator de nome com regex
def extract_name(text):
    nomes = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b', text)
    excluidos = {"Vencimento Valor", "Claro", "CPF", "CNPJ", "Pagamento", "Data", "Código"}
    for nome in nomes:
        if nome not in excluidos and len(nome.split()) >= 2:
            return nome.strip()
    return None

# Interface
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

        with st.spinner("Processando..."):
            selfie_bytes = selfie.getvalue()
            doc_id_bytes = doc_id.getvalue()
            bill_bytes = bill.getvalue()

            # Etapa 1: Comparação facial
            face_result = compare_faces(doc_id_bytes, selfie_bytes)

            # Etapa 2: OCR e nomes
            doc_text = extract_text_from_image(doc_id_bytes)
            bill_text = extract_text_from_image(bill_bytes)

            doc_name = extract_name(doc_text)
            bill_name = extract_name(bill_text)

            # Etapa 3: Vitalidade
            liveness = detect_liveness(selfie_bytes)

        # Resultados
        st.markdown("---")
        st.header("Resultados da Validação")
        colr1, colr2, colr3 = st.columns(3)

        with colr1:
            st.subheader("👤 Confronto Facial")
            if face_result['status']:
                st.success(f"✅ Válido ({face_result['similarity']:.2f}%)")
            else:
                st.error("❌ Falha no reconhecimento facial")

        with colr2:
            st.subheader("📝 Nome")
            if doc_name and bill_name and doc_name.lower() == bill_name.lower():
                st.success(f"✅ Nomes coincidem\n\n{doc_name}")
            else:
                st.error(f"❌ Nomes diferentes\nDocumento: {doc_name or 'N/A'}\nBoleto: {bill_name or 'N/A'}")

        with colr3:
            st.subheader("💡 Vitalidade")
            if liveness:
                st.success("✅ Pessoa real detectada")
            else:
                st.warning("⚠️ Vitalidade não confirmada")

        # Conclusão
        if face_result['status'] and doc_name and bill_name and doc_name.lower() == bill_name.lower() and liveness:
            st.balloons()
            st.success("🎉 Identidade validada com sucesso!")
        else:
            st.error("❌ Falha na validação. Verifique os dados enviados.")

with tab2:
    st.header("Configurações")
    confidence_threshold = st.slider("Limiar de confiança para o reconhecimento facial", 70, 100, 90)
    st.info("Ajuste o limiar de similaridade conforme necessário.")

st.markdown("---")
st.caption("FIAP Cognitive Environments | © 2023 | Versão 1.0")
