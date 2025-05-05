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

# AWS Client com tratamento de erros
def get_aws_client(service):
    try:
        return boto3.client(
            service,
            aws_access_key_id=st.secrets["AWS"]["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=st.secrets["AWS"]["AWS_SECRET_ACCESS_KEY"],
            region_name='us-east-1'
        )
    except Exception as e:
        st.error(f"Erro ao conectar com AWS: {str(e)}")
        st.stop()

# Função para OCR com Textract
def extract_text_from_image(image_bytes):
    textract = get_aws_client('textract')
    try:
        response = textract.detect_document_text(Document={'Bytes': image_bytes})
        return " ".join([item["Text"] for item in response["Blocks"] if item["BlockType"] == "LINE"])
    except Exception as e:
        st.error(f"Erro no OCR: {str(e)}")
        return ""

# Função para comparar rostos
def compare_faces(source_bytes, target_bytes, threshold=90):
    rekognition = get_aws_client('rekognition')
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
    rekognition = get_aws_client('rekognition')
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
        
        # Verifica olhos abertos e ausência de sorriso forçado
        vital = eyes_open and not smile
        details = f"Olhos {'abertos' if eyes_open else 'fechados'}, {'sorrindo' if smile else 'neutro'}"
        return vital, details
    except Exception as e:
        st.error(f"Erro na detecção de vitalidade: {str(e)}")
        return False, "Erro na análise"

# Extrator de nome melhorado
def extract_name(text, doc_type):
    # Padrões para documentos
    if doc_type == "doc":
        patterns = [
            r'NOME[\s:]*([A-ZÀ-Ü][A-ZÀ-Ü\s]+?)(?=\n|$|CPF|RG|DOC|[\d])',
            r'NOME\s+COMPLETO[\s:]*([A-ZÀ-Ü][A-ZÀ-Ü\s]+)',
            r'([A-ZÀ-Ü]{3,}\s[A-ZÀ-Ü]{3,})(?=\n|$)'
        ]
    else:  # Padrões para boletos
        patterns = [
            r'(?:NOME|CLIENTE|TITULAR)[\s:]*([A-ZÀ-Ü][A-ZÀ-Üa-zà-ü\s]+?)(?=\n|$|\d)',
            r'Beneficiário[\s:]*([A-ZÀ-Ü][A-ZÀ-Ü\s]+)',
            r'Pagador[\s:]*([A-ZÀ-Ü][A-ZÀ-Ü\s]+)'
        ]
    
    blacklist = {
        "REPUBLICA", "FEDERATIVA", "BRASIL", "DOCUMENTO", "IDENTIDADE",
        "CPF", "RG", "CNH", "ORGAO", "EXPEDICAO", "VALIDADE", "NACIONAL"
    }
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            name = ' '.join([part for part in match.split() if part.upper() not in blacklist])
            if len(name.split()) >= 2:
                return name.strip()
    return None

# Interface principal
def main():
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
                    st.error("Nomes não encontrados em ambos os documentos")
                elif not doc_name:
                    st.error(f"Nome não encontrado no documento\nBoleto: {bill_name}")
                elif not bill_name:
                    st.error(f"Documento: {doc_name}\nNome não encontrado no boleto")
                elif doc_name.lower() == bill_name.lower():
                    st.success(f"✅ Nomes coincidem\n\n{doc_name}")
                else:
                    st.error(f"❌ Nomes diferentes\nDocumento: {doc_name}\nBoleto: {bill_name}")

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
    st.caption("FIAP Cognitive Environments | © 2023 | Versão 2.0")

if __name__ == "__main__":
    main()
