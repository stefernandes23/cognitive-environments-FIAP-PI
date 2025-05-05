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

# Função segura para obter clientes AWS
def get_aws_client(service):
    try:
        # Tenta primeiro com namespace AWS
        if "AWS" in st.secrets:
            return boto3.client(
                service,
                aws_access_key_id=st.secrets["AWS"]["AWS_ACCESS_KEY_ID"],
                aws_secret_access_key=st.secrets["AWS"]["AWS_SECRET_ACCESS_KEY"],
                region_name='us-east-1'
            )
        # Fallback para estrutura alternativa
        elif "aws_access_key_id" in st.secrets:
            return boto3.client(
                service,
                aws_access_key_id=st.secrets["aws_access_key_id"],
                aws_secret_access_key=st.secrets["aws_secret_access_key"],
                region_name='us-east-1'
            )
        else:
            raise KeyError("Credenciais AWS não encontradas")
    except Exception as e:
        st.error(f"""
        🚨 Erro de conexão com AWS: {str(e)}
        
        Por favor configure suas credenciais:
        1. Local: crie `.streamlit/secrets.toml`
        2. Cloud: vá em Settings → Secrets
        
        Formato requerido:
        ```toml
        [AWS]
        AWS_ACCESS_KEY_ID = "sua_chave"
        AWS_SECRET_ACCESS_KEY = "seu_segredo"
        ```
        """)
        st.stop()

# Inicializa os clientes AWS
rekognition = get_aws_client('rekognition')
textract = get_aws_client('textract')

# Função para OCR com Textract
def extract_text_from_image(image_bytes):
    try:
        response = textract.detect_document_text(Document={'Bytes': image_bytes})
        return " ".join([item["Text"] for item in response["Blocks"] if item["BlockType"] == "LINE"])
    except Exception as e:
        st.error(f"Erro no OCR: {str(e)}")
        return ""

# Função para comparar rostos
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

# Detecção de vitalidade melhorada
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
        st.error(f"Erro na detecção de vitalidade: {str(e)}")
        return False, "Erro na análise"

# Extrator de nome robusto para documentos brasileiros
def extract_name(text, doc_type):
    def extract_name(text, doc_type):
    # Padrões otimizados para documentos brasileiros
    if doc_type == "doc":
        patterns = [
            r'(?:Nome\s*[/]?\s*Name)[\s:]*([A-ZÀ-Ü][A-ZÀ-Üa-zà-ü\s]+?)(?=\n|$|\d|CPF|Sexo|Nome Social)',
            r'Nome\s*[/]?\s*Name[\s:]*([A-ZÀ-Ü][A-ZÀ-Üa-zà-ü\s]+)',
            r'Nome[\s:]*([A-ZÀ-Ü][A-ZÀ-Üa-zà-ü\s]+)(?=\s*Nome Social)'
        ]
    else:  # Padrões para boletos/faturas
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
            # Remove "Nome Social" e informações similares
            name = re.sub(r'\s*Nome Social.*', '', name, flags=re.IGNORECASE)
            # Filtra palavras da blacklist
            filtered_name = ' '.join([part for part in name.split() 
                                    if part.upper() not in blacklist and len(part) > 2])
            if len(filtered_name.split()) >= 2:
                return filtered_name.title()  # Padroniza capitalização
    
    return None

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

        with st.spinner("Processando..."):
            selfie_bytes = selfie.getvalue()
            doc_id_bytes = doc_id.getvalue()
            bill_bytes = bill.getvalue()

            # Etapa 1: Comparação facial
            face_result = compare_faces(doc_id_bytes, selfie_bytes)

            # Etapa 2: OCR e nomes
            doc_text = extract_text_from_image(doc_id_bytes)
            bill_text = extract_text_from_image(bill_bytes)

            doc_name = extract_name(doc_text, "doc")
            bill_name = extract_name(bill_text, "bill")

            # Etapa 3: Vitalidade
            liveness, liveness_details = detect_liveness(selfie_bytes)

        # Debug: Mostrar textos extraídos
        with st.expander("🔍 Textos extraídos (diagnóstico)"):
            col1, col2 = st.columns(2)
            with col1:
                st.text_area("Texto do Documento", doc_text, height=150)
            with col2:
                st.text_area("Texto do Boleto", bill_text, height=150)

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
            if not doc_name and not bill_name:
                st.error("Nomes não encontrados. Verifique a qualidade das imagens.")
            elif doc_name and bill_name:
                # Remove espaços extras e compara versões normalizadas
                clean_doc_name = ' '.join(doc_name.split())
                clean_bill_name = ' '.join(bill_name.split())
                
                if clean_doc_name.lower() == clean_bill_name.lower():
                    st.success(f"✅ Nomes coincidem\n\n{clean_doc_name}")
                else:
                    st.warning(f"⚠️ Pequena diferença detectada (provavelmente normal):")
                    st.write(f"• Documento: {clean_doc_name}")
                    st.write(f"• Boleto: {clean_bill_name}")
                    st.info("Diferença pode ser devido a abreviações ou ordem dos nomes")
                    
                    # Verifica se os nomes são essencialmente iguais
                    if (clean_doc_name.split()[0] == clean_bill_name.split()[0] and 
                        clean_doc_name.split()[-1] == clean_bill_name.split()[-1]):
                        st.success("✅ Nomes essencialmente iguais (primeiro e último nome coincidem)")
            else:
                st.error("Nomes não puderam ser comparados")


        with colr3:
            st.subheader("💡 Vitalidade")
            if liveness:
                st.success(f"✅ Pessoa real detectada\n{liveness_details}")
            else:
                st.warning(f"⚠️ {liveness_details}")

        # Conclusão
        if (face_result['status'] and doc_name and bill_name and 
            doc_name.lower() == bill_name.lower() and liveness):
            st.balloons()
            st.success("🎉 Identidade validada com sucesso!")
        else:
            st.error("❌ Falha na validação. Verifique os dados enviados.")

with tab2:
    st.header("Configurações")
    confidence_threshold = st.slider("Limiar de confiança facial", 70, 100, 90)
    st.info("Ajuste o limiar de similaridade conforme necessário.")

st.markdown("---")
st.caption("FIAP Cognitive Environments | © 2023 | Versão 3.0")
