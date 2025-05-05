import streamlit as st
import fitz  # PyMuPDF
import re

st.set_page_config(page_title="Comparador de Nomes em PDFs", layout="centered")

st.title("Comparador de Nomes em Documentos PDF")

# Upload dos arquivos
uploaded_doc = st.file_uploader("Envie o documento do fornecedor (PDF)", type=["pdf"])
uploaded_bill = st.file_uploader("Envie a fatura (PDF)", type=["pdf"])

def extract_text_from_first_page(pdf_file):
    with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
        text = doc[0].get_text()
    return text

if uploaded_doc and uploaded_bill:
    with st.spinner("Extraindo e comparando nomes..."):
        # Extrai o texto da primeira página de cada PDF
        doc_text = extract_text_from_first_page(uploaded_doc)
        bill_text = extract_text_from_first_page(uploaded_bill)

        # Expressão regular para identificar nomes (ex: "Empresa XYZ Ltda")
        doc_names = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b', doc_text)
        bill_names = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b', bill_text)

        # Compare os nomes possíveis e veja se algum bate
        matched_name = next((name for name in doc_names if name.lower() in [n.lower() for n in bill_names]), None)

    if matched_name:
        st.success(f"✅ Nome correspondente encontrado: **{matched_name}**")
    else:
        st.error("❌ Nenhum nome correspondente foi encontrado entre os dois documentos.")
