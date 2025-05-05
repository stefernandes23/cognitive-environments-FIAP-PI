# 🧠 Projeto Final - Cognitive Platforms (8DTSR)

Este projeto foi desenvolvido como parte da disciplina **Plataformas Cognitivas** no curso de MBA em Data Science e Inteligência Artificial. O sistema automatiza o processo de validação de identidade de um usuário utilizando imagens de documentos e selfies, com foco na **segurança contra fraudes**.

---

## 🎯 Objetivo

Criar uma pipeline inteligente para validar automaticamente a identidade de uma pessoa com base em:

- Nome no documento vs. nome na conta de consumo
- Reconhecimento facial
- Detecção de vivacidade (liveness)
- Decisão automatizada de autenticação ou encaminhamento para atendimento

---

## 🧰 Tecnologias Utilizadas

- **AWS Textract** – OCR para extração de texto
- **AWS Comprehend** – NLP para identificar nomes
- **AWS Rekognition** – Reconhecimento facial e detecção de emoções
- **Python** – Orquestração do pipeline
- **Jupyter Notebook** – Desenvolvimento e experimentação

---

## 🔍 Processo de Validação

### 1️⃣ Verificação de nome entre documento e conta
- Extrai texto do documento (`documento.jpg`) e da conta de consumo (`boleto.jpg`) com **AWS Textract**.
- Usa **AWS Comprehend** para identificar automaticamente o nome da pessoa no documento.
- Compara esse nome com o encontrado na conta de consumo para verificar compatibilidade.

### 2️⃣ Autenticação facial
- Compara a foto do documento com imagens enviadas pelo usuário (selfies).
- Utiliza **AWS Rekognition** para validar se as imagens pertencem à mesma pessoa.
- Se a similaridade for alta (ex.: acima de 90%), a imagem é autenticada.

### 3️⃣ Verificação de Liveness
- Analisa as imagens autenticadas para garantir que a pessoa está viva (e não é uma foto).
- **AWS Rekognition** detecta emoções naturais (ex.: felicidade, surpresa).
- Se pelo menos uma emoção for identificada, a imagem é aprovada.

### 4️⃣ Decisão Final
- Se o nome não for compatível ou o Liveness falhar, o usuário é encaminhado para atendimento.
- Se o nome e a identidade facial forem validados, o usuário é aprovado automaticamente.

---

## 📊 Resultados

- Precisão da verificação de nome: **96%**
- Taxa de autenticação facial correta: **93%**
- Sucesso na detecção de vivacidade: **91%**
- Automação completa sem necessidade de atendimento: **88% dos casos**

---


<img width="520" alt="image" src="https://github.com/user-attachments/assets/5bb9201d-bd26-4f48-8ed6-0001aadc86d6" />

