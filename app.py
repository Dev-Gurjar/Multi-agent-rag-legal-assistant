import streamlit as st
import os
from src.assistant import Assistant

legal_assistant = Assistant()

def main():
    st.title("Legal Assistant")
    query = st.text_area("Enter your query:", placeholder="Type your legal question here...")
    
    attachment = st.file_uploader("Upload a file (optional):", type=["pdf", "jpg", "png", "txt"])

    if st.button("Submit"):
        if not query and not attachment:
            st.warning("Please enter a query or upload a file.")
        else:
            with st.spinner("Processing your request..."):
                try:
                    attachment_path = None
                    if attachment is not None:
                        # Save uploaded file to uploads directory
                        uploads_dir = "uploads"
                        os.makedirs(uploads_dir, exist_ok=True)
                        file_path = os.path.join(uploads_dir, attachment.name)
                        with open(file_path, "wb") as f:
                            f.write(attachment.getbuffer())
                        attachment_path = file_path
                    
                    result = legal_assistant(text_query=query, attachment=attachment_path)
                    st.success("Query processed successfully!")
                    st.text_area("Response:", value=result, height=300)
                except Exception as e:
                    st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
