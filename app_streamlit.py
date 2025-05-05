'''
🪄 FIAP - Validador Biométrico Mágico 🪄

Este é um programa que usa magia da computação para verificar se:
1. A pessoa na foto é a mesma do documento
2. O nome no documento combina com o do boleto
3. É uma pessoa real (não uma foto de foto)
'''

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
**Validação em 3 etapas:**
1. 👀 Comparação facial (Selfie vs Documento)
2. ✍️ Verificação de nome (Documento vs Boleto)
3. 💡 Análise de vitalidade (É uma pessoa real?)
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
        st.stop()  # Para o programa se não tiver conexão

# Conecta os serviços mágicos da AWS
rekognition = get_aws_client('rekognition')  # Serviço de reconhecimento facial
textract = get_aws_client('textract')  # Serviço de leitura de texto em imagens

# 🔍 Função para ler texto em fotos (OCR)
def extract_text_from_image(image_bytes):
    try:
        # Pede para a nuvem ler o texto na imagem
        response = textract.detect_document_text(Document={'Bytes': image_bytes})
        # Junta todas as linhas de texto encontradas
        return " ".join([item["Text"] for item in response["Blocks"] if item["BlockType"] == "LINE"])
    except Exception as e:
        st.error(f"Erro no OCR: {str(e)}")  # Se não conseguir ler
        return ""

# 👥 Função para comparar rostos
def compare_faces(source_bytes, target_bytes, threshold=90):
    try:
        # Pede para a nuvem comparar as duas fotos
        response = rekognition.compare_faces(
            SourceImage={'Bytes': source_bytes},  # Foto do documento
            TargetImage={'Bytes': target_bytes},  # Selfie
            SimilarityThreshold=threshold  # % de similaridade necessário
        )
        if not response['FaceMatches']:
            return {'status': False, 'similarity': 0}  # Se não achou rostos iguais
        return {
            'status': True,  # Achou um rosto parecido
            'similarity': response['FaceMatches'][0]['Similarity'],  # % de similaridade
            'face': response['FaceMatches'][0]['Face']  # Informações do rosto
        }
    except Exception as e:
        st.error(f"Erro na comparação facial: {str(e)}")
        return {'status': False, 'error': str(e)}

# 💡 Função para verificar se é uma pessoa real
def detect_liveness(image_bytes):
    try:
        # Pede para a nuvem analisar a selfie
        response = rekognition.detect_faces(
            Image={'Bytes': image_bytes},
            Attributes=['ALL']  # Pede todos os detalhes possíveis
        )
        if not response['FaceDetails']:
            return False, "Nenhum rosto detectado"  # Se não achou rosto
        
        face = response['FaceDetails'][0]
        eyes_open = face['EyesOpen']['Value']  # Se os olhos estão abertos
        smile = face['Smile']['Value']  # Se está sorrindo
        
        # Considera "vivo" se estiver com olhos abertos e não sorrindo
        vital = eyes_open and not smile
        details = f"Olhos {'abertos' if eyes_open else 'fechados'}, {'sorrindo' if smile else 'neutro'}"
        return vital, details
    except Exception as e:
        st.error(f"Erro na detecção de vitalidade: {str(e)}")
        return False, "Erro na análise"

# ✍️ Função para extrair nomes dos documentos
def extract_name(text, doc_type):
    # Padrões diferentes para documento ou boleto
    if doc_type == "doc":
        patterns = [
            r'(?:Nome\s*[/]?\s*Name)[\s:]*([A-ZÀ-Ü][A-ZÀ-Üa-zà-ü\s]+?)(?=\n|$|\d|CPF|Sexo|Nome Social)',
            r'Nome\s*[/]?\s*Name[\s:]*([A-ZÀ-Ü][A-ZÀ-Üa-zà-ü\s]+)',
            r'Nome[\s:]*([A-ZÀ-Ü][A-ZÀ-Üa-zà-ü\s]+)(?=\s*Nome Social)'
        ]
    else:
        patterns = [
            r'^([A-ZÀ-Ü][A-ZÀ-Üa-zà-ü\s]+?)(?=\n|\d|Código|Vencimento)',
            r'(?:Cliente|Titular|Beneficiário)[\s:]*([A-ZÀ-Ü][A-ZÀ-Üa-zà-ü\s]+)'
        ]
    
    # Palavras que não são nomes (para ignorar)
    blacklist = {
        "REPUBLICA", "FEDERATIVA", "BRASIL", "DOCUMENTO", "IDENTIDADE",
        "CPF", "RG", "CNH", "ORGAO", "EXPEDICAO", "VALIDADE", "GOVERNO"
    }
    
    # Procura o nome usando os padrões
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            name = match.group(1).strip()
            # Remove partes desnecessárias
            name = re.sub(r'\s*Nome Social.*', '', name, flags=re.IGNORECASE)
            # Filtra palavras da blacklist
            filtered_name = ' '.join([part for part in name.split() 
                                    if part.upper() not in blacklist and len(part) > 2])
            if len(filtered_name.split()) >= 2:  # Precisa ter pelo menos 2 palavras
                return filtered_name.title()  # Retorna o nome bonitinho
    
    return None  # Se não achou nome

# ================== PARTE PRINCIPAL ==================

# 📌 Cria duas abas (telas)
tab1, tab2 = st.tabs(["Validação Completa", "Configurações"])

with tab1:
    st.header("1. Upload dos Documentos")
    col1, col2, col3 = st.columns(3)  # Divide em 3 colunas

    # 📷 Coluna 1 - Selfie
    with col1:
        st.subheader("📷 Selfie Atual")
        selfie = st.file_uploader("Sua foto atual (selfie)", type=["jpg", "png"])
        if selfie:
            st.image(selfie, use_container_width=True)

    # 🆔 Coluna 2 - Documento
    with col2:
        st.subheader("🆔 Documento de Identidade")
        doc_id = st.file_uploader("Foto do seu documento (RG/CNH)", type=["jpg", "png"])
        if doc_id:
            st.image(doc_id, use_column_width=True)

    # 💳 Coluna 3 - Boleto
    with col3:
        st.subheader("💳 Comprovante (Boleto/Conta)")
        bill = st.file_uploader("Comprovante com seu nome", type=["jpg", "png"])
        if bill:
            st.image(bill, use_column_width=True)

    # 🚀 Botão para iniciar a validação
    if st.button("Validar Identidade", type="primary"):
        if not all([selfie, doc_id, bill]):
            st.error("Por favor, envie todos os documentos!")
            st.stop()

        with st.spinner("Processando..."):  # Mostra um loading
            # Pega os dados das imagens
            selfie_bytes = selfie.getvalue()
            doc_id_bytes = doc_id.getvalue()
            bill_bytes = bill.getvalue()

            # Faz todas as verificações
            face_result = compare_faces(doc_id_bytes, selfie_bytes)
            doc_text = extract_text_from_image(doc_id_bytes)
            bill_text = extract_text_from_image(bill_bytes)
            doc_name = extract_name(doc_text, "doc")
            bill_name = extract_name(bill_text, "bill")
            liveness, liveness_details = detect_liveness(selfie_bytes)

        # Mostra os textos extraídos (para diagnóstico)
        with st.expander("🔍 Textos extraídos (diagnóstico)"):
            col1, col2 = st.columns(2)
            with col1:
                st.text_area("Texto do Documento", doc_text, height=150)
            with col2:
                st.text_area("Texto do Boleto", bill_text, height=150)

        st.markdown("---")
        st.header("Resultados da Validação")
        colr1, colr2, colr3 = st.columns(3)

        # 👤 Resultado da comparação facial
        with colr1:
            st.subheader("👤 Comparação Facial")
            if face_result['status']:
                st.success(f"✅ Válido ({face_result['similarity']:.2f}%)")
            else:
                st.error("❌ Falha no reconhecimento facial")

        # 📝 Resultado da comparação de nomes
        with colr2:
            st.subheader("📝 Nome")
            if not doc_name and not bill_name:
                st.error("Nomes não encontrados. Verifique a qualidade das imagens.")
            elif doc_name and bill_name:
                # Limpa os nomes para comparar
                clean_doc_name = ' '.join(doc_name.replace("Nome Social", "").split())
                clean_bill_name = ' '.join(bill_name.split())
                
                # Remove sufixos como "da Silva"
                for suffix in [" da", " de", " dos"]:
                    clean_doc_name = re.sub(fr'{suffix}\s+\w+$', '', clean_doc_name, flags=re.IGNORECASE)
                    clean_bill_name = re.sub(fr'{suffix}\s+\w+$', '', clean_bill_name, flags=re.IGNORECASE)
                
                # Compara os nomes
                if clean_doc_name.lower() == clean_bill_name.lower():
                    st.success(f"✅ Nomes coincidem\n\n{clean_doc_name}")
                else:
                    # Se não forem iguais, verifica se pelo menos o primeiro e último nome batem
                    doc_parts = clean_doc_name.split()
                    bill_parts = clean_bill_name.split()
                    
                    if (len(doc_parts) >= 2 and len(bill_parts) >= 2 and
                        doc_parts[0].lower() == bill_parts[0].lower() and
                        doc_parts[-1].lower() == bill_parts[-1].lower()):
                        
                        st.success("✅ Nomes essencialmente iguais")
                        st.write(f"• Documento: {clean_doc_name}")
                        st.write(f"• Boleto: {clean_bill_name}")
                    else:
                        st.warning("⚠️ Diferença encontrada nos nomes")
                        st.write(f"• Documento: {clean_doc_name}")
                        st.write(f"• Boleto: {clean_bill_name}")
            else:
                st.error("Nomes não puderam ser comparados")
                if not doc_name:
                    st.error("Nome não extraído do documento")
                if not bill_name:
                    st.error("Nome não extraído do boleto")

        # 💡 Resultado da vitalidade
        with colr3:
            st.subheader("💡 Vitalidade")
            if liveness:
                st.success(f"✅ Pessoa real detectada\n{liveness_details}")
            else:
                st.warning(f"⚠️ {liveness_details}")

        # 🎉 Resultado final
        if (face_result['status'] and doc_name and bill_name and 
            doc_name.lower() == bill_name.lower() and liveness):
            st.balloons()  # Animação de comemoração
            st.success("🎉 Identidade validada com sucesso!")
        else:
            st.error("❌ Falha na validação. Verifique os dados enviados.")

# ⚙️ Tela de configurações
with tab2:
    st.header("Configurações")
    confidence_threshold = st.slider("Limiar de confiança facial", 70, 100, 90)
    st.info("Ajuste o limiar de similaridade conforme necessário.")

# Rodapé
st.markdown("---")
st.caption("FIAP Cognitive Environments | © 2023 | Versão 3.0")
