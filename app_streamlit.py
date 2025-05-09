import streamlit as st  # Biblioteca para criar a tela bonitinha
import boto3  # Conexão com a nuvem mágica da Amazon
import re  # Para encontrar padrões em textos
from PIL import Image  # Para trabalhar com fotos

# ✨ Configuração da página ✨
st.set_page_config(
    page_title="FIAP - Validador Biométrico",
    page_icon="🆔",  # Ícone fofinho
    layout="wide",  # Página grande
    initial_sidebar_state="expanded"  # Menu lateral aberto
)

# Título principal com emojis
st.title("🆔 Validador de Identidade FIAP")
st.markdown("""
**Validação em 4 etapas:**
1. 👀 Comparação facial (Selfie vs Documento)
2. ✍️ Verificação de nome (Documento vs Boleto)
3. 🆔 Extração de dados de CNH
4. 💡 Análise de Liveness (É uma pessoa real?)
""")
st.markdown("---")  # Linha divisória

# 🗝️ Função para conectar com a nuvem mágica da AWS
def get_aws_client(service):
    try:
        # Procura as chaves secretas em dois lugares diferentes
        if "AWS" in st.secrets:
            return boto3.client(
                service,
                aws_access_key_id=st.secrets["AWS"]["AWS_ACCESS_KEY_ID"],
                aws_secret_access_key=st.secrets["AWS"]["AWS_SECRET_ACCESS_KEY"],
                region_name='us-east-1'  # Servidor nos EUA
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
        # Mensagem de erro amigável se não conseguir conectar
        st.error(f"🚨 Erro de conexão com AWS: {str(e)}")
        st.stop()  # Para o programa se não tiver conexão

# Conecta os serviços mágicos da AWS
rekognition = get_aws_client('rekognition')  # Serviço de reconhecimento facial
textract = get_aws_client('textract')  # Serviço de leitura de texto em imagens

# 🔍 Função para ler texto em fotos (OCR)
def extract_text_from_image(image_bytes):
    try:
        response = textract.detect_document_text(Document={'Bytes': image_bytes})
        return " ".join([item["Text"] for item in response["Blocks"] if item["BlockType"] == "LINE"])
    except Exception as e:
        st.error(f"Erro no OCR: {str(e)}")
        return ""

# 👥 Função para comparar rostos
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
        st.error(f"Erro na comparação facial: {str(e)}")
        return {'status': False, 'error': str(e)}

# 💡 Função para verificar se é uma pessoa real
def detect_liveness(image_bytes):
    try:
        response = rekognition.detect_faces(
            Image={'Bytes': image_bytes},
            Attributes=['ALL']
        )
        if not response['FaceDetails']:
            return False, "Nenhum rosto detectado"
        face = response['FaceDetails'][0]
        eyes_open = face['EyesOpen']['Value']
        smile = face['Smile']['Value']
        vital = eyes_open and not smile
        details = f"Olhos {'abertos' if eyes_open else 'fechados'}, {'sorrindo' if smile else 'neutro'}"
        return vital, details
    except Exception as e:
        st.error(f"Erro na detecção de Liveness: {str(e)}")
        return False, "Erro na análise"

# ✍️ Função para extrair nomes dos documentos
def extract_name(text, doc_type):
    # padrões anteriores...
    # (mesmo código de patterns para doc e bill)
    ...

# 🪪 Nova função para extrair dados de CNH
def extract_cnh_data(text):
    # padrões para CNH: número, categoria, validade e registro
    patterns = {
        'numero': r'(?:CNH|Registro)[\s:]*(\d{11})',
        'categoria': r'Categoria[:\s]*([A-Z])',
        'validade': r'Validade[:\s]*(\d{2}/\d{2}/\d{4})'
    }
    data = {}
    for field, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        data[field] = match.group(1) if match else None
    return data

# ================== PARTE PRINCIPAL ==================
# Seleção de tipo de documento
st.sidebar.header("Configuração de Documento")
doc_type = st.sidebar.selectbox(
    "Tipo de documento", ['RG/CNH', 'Passaporte', 'Outro'], index=0
)

# 📌 Cria duas abas (telas)
tab1, tab2 = st.tabs(["Validação Completa", "Configurações"])

with tab1:
    st.header("1. Upload dos Documentos")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("📷 Selfie Atual")
        selfie = st.file_uploader("Sua foto atual (selfie)", type=["jpg", "png"] )
        if selfie: st.image(selfie, use_container_width=True)
    with col2:
        st.subheader("🆔 Documento")
        doc_id = st.file_uploader(f"Foto do seu documento ({doc_type})", type=["jpg", "png"])  
        if doc_id: st.image(doc_id, use_column_width=True)
    with col3:
        st.subheader("💳 Comprovante (Boleto/Conta)")
        bill = st.file_uploader("Comprovante com seu nome", type=["jpg", "png"]) 
        if bill: st.image(bill, use_column_width=True)

    if st.button("Validar Identidade", type="primary"):
        if not all([selfie, doc_id, bill]): st.error("Por favor, envie todos os documentos!"); st.stop()
        with st.spinner("Processando..."):
            selfie_bytes = selfie.getvalue()
            doc_bytes = doc_id.getvalue()
            bill_bytes = bill.getvalue()

            face_result = compare_faces(doc_bytes, selfie_bytes, threshold=st.session_state.get('confidence_threshold', 90))
            doc_text = extract_text_from_image(doc_bytes)
            bill_text = extract_text_from_image(bill_bytes)
            doc_name = extract_name(doc_text, "doc")  # atualize extract_name conforme necessário
            bill_name = extract_name(bill_text, "bill")
            liveness, liveness_details = detect_liveness(selfie_bytes)
            cnh_data = extract_cnh_data(doc_text) if 'cnh' in doc_type.lower() else {}

        st.markdown("---")
        st.header("Resultados da Validação")
        colr1, colr2, colr3, colr4 = st.columns(4)
        with colr1:
            st.subheader("👤 Comparação Facial")
            if face_result['status']: st.success(f"✅ Válido ({face_result['similarity']:.2f}%)")
            else: st.error("❌ Falha no reconhecimento facial")
        with colr2:
            st.subheader("📝 Nome")
            # lógica de nome existente...
            ...
        with colr3:
            st.subheader("🪪 Dados CNH")
            if cnh_data:
                for k, v in cnh_data.items():
                    st.write(f"**{k.title()}:** {v if v else 'Não encontrado'}")
            else:
                st.info("CNH não selecionada ou dados não identificados")
        with colr4:
            st.subheader("💡 Liveness")
            if liveness: st.success(f"✅ Pessoa real\n{liveness_details}")
            else: st.warning(f"⚠️ {liveness_details}")

        if face_result['status'] and doc_name and bill_name and doc_name.lower()==bill_name.lower() and liveness:
            st.balloons(); st.success("🎉 Identidade validada com sucesso!")
        else:
            st.error("❌ Falha na validação. Verifique os dados enviados.")

with tab2:
    st.header("Configurações")
    confidence_threshold = st.slider("Limiar de confiança facial", 70, 100, 90)
    st.info("Ajuste o limiar de similaridade conforme necessário.")

st.markdown("---")
st.caption("FIAP Cognitive Environments")
