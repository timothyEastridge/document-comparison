# streamlit run Document_Comparison_20240715.py

import streamlit as st
import openai
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from docx import Document
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import smtplib
from datetime import datetime
import pytz

# Set up the page
st.set_page_config(layout="wide", page_title="Compare Document Differences")

# Title
st.markdown("<h1 style='text-align: center;'>Compare Document Differences</h1>", unsafe_allow_html=True)

# Function to read docx file
def read_docx(file):
    doc = Document(file)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

# Function to generate responses using GPT
def generate_responses(doc1_text, doc2_text):
    try:
        openai_api_key = st.secrets["openai"]["api_key"]
        chat_llm = ChatOpenAI(temperature=0.8, api_key=openai_api_key, model="gpt-4")

        prompt_template = PromptTemplate(
            template="""Compare the following two documents and provide a detailed analysis of their differences:

Document 1:
{doc1_text}

Document 2:
{doc2_text}

Please format your response in markdown. After the comparison, provide a separate section assessing the risks added in the second document for the recipient compared to the original document. Use appropriate markdown headers and formatting.""",
            input_variables=["doc1_text", "doc2_text"]
        )

        chat_chain = LLMChain(llm=chat_llm, prompt=prompt_template)
        input_data = {"doc1_text": doc1_text, "doc2_text": doc2_text}
        response = chat_chain.generate([input_data])
        comparison_result = response.generations[0][0].text if response.generations else "No response generated"

        return comparison_result
    except Exception as e:
        st.error(f"Error generating responses: {str(e)}")
        return None

def get_timestamp():
    est = pytz.timezone('America/New_York')
    return datetime.now(est).strftime("%Y%m%d_%H%M%S")

def send_email(to_address, subject, body, attachment_paths, uploaded_file_name):
    try:
        from_address = st.secrets["email"]["address"]
        password = st.secrets["email"]["password"]

        timestamped_subject = f"{subject} - {uploaded_file_name} - {get_timestamp()}"

        message = MIMEMultipart()
        message['From'] = from_address
        message['To'] = to_address
        message['Subject'] = timestamped_subject

        message.attach(MIMEText(body, 'plain'))
        
        for attachment_path in attachment_paths:
            if os.path.exists(attachment_path):
                with open(attachment_path, 'rb') as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(attachment_path)}")
                message.attach(part)
            else:
                st.error(f"Debug: Attachment file not found: {attachment_path}")

        with smtplib.SMTP('smtp.gmail.com', 587) as session:
            session.starttls()
            session.login(from_address, password)
            text = message.as_string()
            session.sendmail(from_address, to_address, text)

        return "Email sent successfully!"
    except Exception as e:
        st.error(f"Error sending email: {str(e)}")
        return None

# Create two columns for file upload
col1, col2 = st.columns(2)

with col1:
    st.subheader("Document #1")
    doc1 = st.file_uploader("Upload first document", type="docx", key="doc1")
    st.info("Upload the first document you want to compare. This document will be used as the base for comparison.", icon="ℹ️")

with col2:
    st.subheader("Document #2")
    doc2 = st.file_uploader("Upload second document", type="docx", key="doc2")
    st.info("Upload the second document you want to compare. This document will be compared against Document #1.", icon="ℹ️")

# Function to handle file upload and email sending
def handle_file_upload(doc, doc_number):
    if doc:
        txt_file_name = f"document_{doc_number}_{get_timestamp()}.txt"
        txt_file_path = os.path.join(os.getcwd(), txt_file_name)
        
        with open(txt_file_path, 'w', encoding='utf-8') as f:
            f.write(read_docx(doc))
        
        email_result = send_email(
            "info@eastridge-analytics.com",
            f"New File Upload - Document #{doc_number}",
            f"A new document (#{doc_number}) has been uploaded for comparison. Please find the content attached.",
            [txt_file_path],
            doc.name
        )
        
        if email_result:
            st.success(f"Document #{doc_number} uploaded.")
        else:
            st.error(f"Failed to send email for Document #{doc_number}. Please try again.")
        
        os.remove(txt_file_path)

# Handle file uploads
if doc1:
    handle_file_upload(doc1, 1)
if doc2:
    handle_file_upload(doc2, 2)

# Compare documents when both are uploaded
if doc1 and doc2:
    doc1_text = read_docx(doc1)
    doc2_text = read_docx(doc2)
    
    with st.spinner("Analyzing documents..."):
        comparison_result = generate_responses(doc1_text, doc2_text)
    
    st.subheader("Comparison Analysis and Risk Assessment")
    
    # Display comparison result in markdown format
    st.markdown(comparison_result)

else:
    st.warning("Please upload both documents to see the comparison.")
