import streamlit as st
import os
from pathlib import Path
from src.assistant import Assistant

# Auto-download legal dataset if not present (for Streamlit Cloud deployment)
def ensure_data_exists():
    """Ensure legal case data exists, download if missing."""
    data_dir = Path("data/casedocs")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if we have any case files
    existing_files = list(data_dir.glob("*.txt"))
    
    if not existing_files:
        # Download dataset on first run
        with st.spinner("Downloading legal case dataset (first time setup)..."):
            try:
                import sys
                scripts_path = Path(__file__).parent / "scripts"
                sys.path.insert(0, str(scripts_path))
                from setup_data import download_and_process
                count = download_and_process()
                if count > 0:
                    st.success(f"✅ Downloaded {count} legal cases!")
                else:
                    st.warning("⚠️ Could not download dataset. App will work but without case data.")
            except Exception as e:
                st.warning(f"⚠️ Dataset download failed: {e}. App will work but without case data.")
                import traceback
                traceback.print_exc()

# Lazy initialization - only create assistant when needed
@st.cache_resource
def get_assistant():
    """Get or create the assistant instance (cached)."""
    return Assistant()

# Ensure data exists
ensure_data_exists()

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
                    
                    legal_assistant = get_assistant()
                    result = legal_assistant(text_query=query, attachment=attachment_path)
                    st.success("Query processed successfully!")
                    st.text_area("Response:", value=result, height=300)
                except Exception as e:
                    st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
