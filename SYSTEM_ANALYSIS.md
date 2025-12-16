# LegalRAG System Analysis & Local Setup Guide

## System Overview

This is a **Retrieval-Augmented Generation (RAG)**-based Legal Assistant system that provides:
- Legal Document Summarization
- Case Discovery
- Legal Drafting
- Query Resolution

### Architecture

1. **Core Components:**
   - `Assistant` class: Main orchestrator that routes queries to appropriate agents
   - `Decomposer`: Breaks down complex queries into sub-queries and identifies intent
   - **Agents:**
     - `CaseDiscoveryAgent`: Handles case discovery and document summarization
     - `LegalAidAgent`: Provides query resolution
     - `LegalDraftingAgent`: Drafts legal documents

2. **Technologies:**
   - **Embedding Model**: `all-mpnet-base-v2` (SentenceTransformers)
   - **LLM**: `microsoft/Phi-3-mini-4k-instruct` (for text generation)
   - **Legal BERT**: `nlpaueb/legal-bert-base-uncased` (for intent classification)
   - **Vector Store**: FAISS for similarity search
   - **NLP**: spaCy for text processing
   - **UI**: Streamlit web interface

3. **Data Requirements:**
   - Case documents should be placed in `data/casedocs/` directory
   - Supports PDF, TXT, and image files (JPG, PNG, etc.)

## Issues Found & Fixed

### 1. ✅ Hardcoded Colab Paths
**Issue**: Code used `/content/rag-legal-assistant/data/casedocs` (Google Colab path)
**Fixed**: Changed to relative path `data/casedocs`

**Files Modified:**
- `src/agents/case_discovery.py`
- `src/agents/legal_aid.py`

### 2. ✅ Bug in Image File Extension Check
**Issue**: Line 38 in `preprocess.py` had incorrect logic: `if file_extension == self.allowed_extensions`
**Fixed**: Changed to proper check: `if file_extension in [".jpg", ".jpeg", ".png", ".tiff", ".bmp"]`

**File Modified:**
- `src/query_decompose/preprocess.py`

### 3. ✅ Missing Dependencies
**Issue**: `requirements.txt` was missing `torch` and `numpy`
**Fixed**: Added missing dependencies

**File Modified:**
- `requirements.txt`

### 4. ✅ Missing Directory Structure
**Issue**: Required directories didn't exist
**Fixed**: Created `data/casedocs/` and `uploads/` directories

### 5. ✅ File Upload Handling
**Issue**: `app.py` passed Streamlit file uploader object directly instead of file path
**Fixed**: Added code to save uploaded file and pass path to assistant

**File Modified:**
- `app.py`

### 6. ✅ Error Handling
**Issue**: `Assistant.__call__` didn't handle errors from decomposer or agent failures
**Fixed**: Added comprehensive error handling

**File Modified:**
- `src/assistant.py`

## Local Setup Instructions

### Prerequisites
- Python 3.8+ (tested with Python 3.13.8)
- pip package manager
- Internet connection (for downloading models)

### Installation Steps

1. **Install Python Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install spaCy Language Model:**
   ```bash
   python -m spacy download en_core_web_md
   ```

3. **Install Tesseract OCR (for image processing):**
   - **Windows**: Download from https://github.com/UB-Mannheim/tesseract/wiki
   - **Linux**: `sudo apt-get install tesseract-ocr`
   - **Mac**: `brew install tesseract`

4. **Add Case Documents (Optional but Recommended):**
   - Place legal case documents (PDF, TXT) in `data/casedocs/` directory
   - The system will build a FAISS index on first run

### Running the Application

**Option 1: Streamlit Web Interface**
```bash
streamlit run app.py
```
Then open http://localhost:8501 in your browser

**Option 2: Command Line**
```bash
python main.py
```

## Important Notes

### Model Downloads
The system will automatically download these models on first run:
- `microsoft/Phi-3-mini-4k-instruct` (~7GB)
- `all-mpnet-base-v2` (~420MB)
- `nlpaueb/legal-bert-base-uncased` (~440MB)

**Total download size**: ~8GB

### Performance Considerations
- First run will be slow due to model downloads
- Model loading happens at import time (in `src/assistant.py`)
- FAISS index building happens on first query if no index exists
- GPU recommended but not required (CPU will work, slower)

### Data Requirements
- The system expects case documents in `data/casedocs/`
- If the directory is empty, the system will still run but won't find relevant cases
- You can add sample legal documents to test the system

## Testing Status

✅ **Code Structure**: All files are properly structured
✅ **Path Issues**: Fixed all hardcoded paths
✅ **Bug Fixes**: Fixed image extension check bug
✅ **Dependencies**: Updated requirements.txt
✅ **Directory Structure**: Created required directories
✅ **Error Handling**: Improved error handling

⚠️ **Not Yet Tested** (requires full installation):
- Model downloads and loading
- FAISS index creation
- End-to-end query processing
- Streamlit interface

## Next Steps for Full Testing

1. Install all dependencies: `pip install -r requirements.txt`
2. Install spaCy model: `python -m spacy download en_core_web_md`
3. Install Tesseract OCR
4. Add sample case documents to `data/casedocs/`
5. Run `streamlit run app.py` and test with a sample query

## Known Limitations

1. **Model Size**: Large models require significant disk space (~8GB)
2. **Memory**: Phi-3 model requires substantial RAM (recommended 16GB+)
3. **First Run**: Slow due to model downloads and index building
4. **Empty Data**: System works but won't retrieve relevant cases without documents
5. **GPU**: Not required but significantly improves performance

## File Structure

```
LegalRAG/
├── app.py                 # Streamlit web interface
├── main.py                # CLI entry point
├── requirements.txt       # Python dependencies
├── README.md              # Project documentation
├── data/
│   ├── casedocs/         # Place case documents here
│   └── README.md
├── uploads/               # Temporary file uploads
└── src/
    ├── assistant.py       # Main orchestrator
    ├── agents/
    │   ├── case_discovery.py
    │   ├── legal_aid.py
    │   └── legal_draft.py
    └── query_decompose/
        ├── decompose.py
        └── preprocess.py
```

