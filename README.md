# 🧠 Projeto Final - Cognitive Environments (8DTSR)

Este projeto foi desenvolvido como parte da disciplina **Cognitive Environments** no curso de MBA em Data Science e Inteligência Artificial. O sistema automatiza o processo de validação de identidade de um usuário utilizando imagens de documentos e selfies, com foco na **segurança contra fraudes**.

---

## 🎯 Objetivo

Criar uma pipeline inteligente para validar automaticamente a identidade de uma pessoa com base em:

- Nome no documento vs. nome na conta de consumo
- Reconhecimento facial
- Detecção de vivacidade (liveness)


<img width="520" alt="image" src="https://github.com/user-attachments/assets/5bb9201d-bd26-4f48-8ed6-0001aadc86d6" />

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
  
---


# Analisador Facial com AWS Rekognition

O app desenvolvido usa AWS Rekognition para análise facial. Você pode acessá-lo através do seguinte link:


<img width="887" alt="image" src="https://github.com/user-attachments/assets/83031f69-df27-492e-a985-7477a2973b4a" />


# Alunos 👨‍🎓👩‍🎓

1. André Leone 
2. Igor Alves 
3. Latife Neamen 
4. Stephanie Fernandes 
