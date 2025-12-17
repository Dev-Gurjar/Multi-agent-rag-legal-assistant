"""
Simplified data setup script that can run on Streamlit Cloud.

This script downloads a sample of legal cases from publicly accessible sources
and prepares them for the RAG system. It's designed to work in deployment environments.
"""

import os
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("data/casedocs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Multiple possible sources for legal datasets
# Try these URLs in order until one works
DATA_SOURCES = [
    # GitHub: Indian Supreme Court Judgment Database (try different paths)
    "https://raw.githubusercontent.com/NoelShallum/Indian_SC_Judgment_database/master/SC_Judgments_1980_1990.csv",
    "https://raw.githubusercontent.com/NoelShallum/Indian_SC_Judgment_database/main/SC_Judgments_1980_1990.csv",
    "https://github.com/NoelShallum/Indian_SC_Judgment_database/raw/master/SC_Judgments_1980_1990.csv",
    # Alternative: Sample legal cases (if GitHub fails, we'll create sample data)
]


def create_sample_data():
    """Create sample legal case data if download fails."""
    print("\nCreating sample legal case data...")
    
    sample_cases = [
        {
            "title": "Masud Khan vs State of India",
            "date": "2023-05-15",
            "parties": "Masud Khan (Petitioner) vs State of India (Respondent)",
            "text": """This case concerns the fundamental rights of the petitioner, Masud Khan, 
            regarding property rights and due process. The petitioner argued that the state's 
            acquisition of his property violated Article 300A of the Constitution, which guarantees 
            the right to property. The main argument made by the petitioner, Masud Khan, was that 
            the acquisition process lacked proper notice and fair compensation. The court examined 
            the procedural requirements and found that while the acquisition was lawful, the 
            compensation offered was inadequate. The judgment established important precedents 
            regarding property rights and state acquisition powers."""
        },
        {
            "title": "Right to Privacy Case",
            "date": "2023-08-20",
            "parties": "Privacy Advocates vs Government",
            "text": """This landmark case addressed the right to privacy as a fundamental right 
            under the Indian Constitution. The petitioners argued that recent legislation violated 
            citizens' privacy rights. The court held that privacy is an intrinsic part of the right 
            to life and personal liberty under Article 21. The judgment has far-reaching implications 
            for data protection and surveillance laws in India."""
        },
        {
            "title": "Environmental Protection Case",
            "date": "2023-11-10",
            "parties": "Environmental Group vs Industrial Corporation",
            "text": """This case dealt with environmental protection and industrial development. 
            The petitioners sought to enforce strict environmental regulations on a major industrial 
            project. The court balanced economic development with environmental protection, establishing 
            guidelines for sustainable development. The judgment emphasized the precautionary principle 
            and the polluter pays principle."""
        }
    ]
    
    processed = 0
    for idx, case in enumerate(sample_cases):
        filename = f"2023_{idx:05d}_{case['title'].replace(' ', '_')[:30]}.txt"
        file_path = OUTPUT_DIR / filename
        
        content = []
        content.append(f"Title: {case['title']}")
        content.append(f"Date: {case['date']}")
        content.append(f"Parties: {case['parties']}")
        content.append("")
        content.append(case['text'])
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content))
        
        processed += 1
    
    print(f"Created {processed} sample case files")
    return processed


def download_and_process():
    """Download and process the GitHub dataset."""
    print("Attempting to download Indian Supreme Court Judgment Database...")
    
    # Try each data source URL
    for url in DATA_SOURCES:
        try:
            print(f"Trying: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Read CSV into pandas
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            
            print(f"Downloaded {len(df)} cases")
            print(f"Columns: {list(df.columns)}")
            
            # Map column names (adjust based on actual CSV structure)
            title_col = None
            date_col = None
            text_col = None
            parties_col = None
            
            for col in df.columns:
                col_lower = col.lower()
                if 'title' in col_lower or 'case' in col_lower:
                    title_col = col
                if 'date' in col_lower:
                    date_col = col
                if 'decision' in col_lower or 'judgment' in col_lower or 'text' in col_lower:
                    text_col = col
                if 'parties' in col_lower or 'petitioner' in col_lower:
                    parties_col = col
            
            # If we can't find text column, try common names
            if not text_col:
                for col in ['decision', 'judgment', 'judgment_text', 'text', 'Decision', 'Judgment']:
                    if col in df.columns:
                        text_col = col
                        break
            
            if not text_col:
                print("Warning: Could not find text column. Available columns:", list(df.columns))
                text_col = df.columns[0] if len(df.columns) > 0 else None
            
            print(f"Using columns - Title: {title_col}, Date: {date_col}, Text: {text_col}, Parties: {parties_col}")
            
            # Process cases
            processed = 0
            for idx, row in df.iterrows():
                # Get text content
                if text_col and pd.notna(row.get(text_col)):
                    text = str(row[text_col]).strip()
                else:
                    # Try to combine multiple columns
                    text_parts = []
                    for col in df.columns:
                        if col not in [title_col, date_col, parties_col] and pd.notna(row.get(col)):
                            text_parts.append(str(row[col]))
                    text = " ".join(text_parts).strip()
                
                if not text or len(text) < 50:
                    continue
                
                # Get metadata
                title = str(row.get(title_col, '')).strip() if title_col else f"Case {idx}"
                date = str(row.get(date_col, '')).strip() if date_col else ""
                parties = str(row.get(parties_col, '')).strip() if parties_col else ""
                
                # Parse year
                year = None
                if date:
                    try:
                        dt = pd.to_datetime(date, errors='coerce')
                        if pd.notna(dt):
                            year = dt.year
                    except:
                        pass
                
                # Create filename
                safe_title = "".join(c if c.isalnum() or c in "-_ " else "_" for c in title[:40])
                filename = f"{year or 'unknown'}_{idx:05d}_{safe_title[:25]}.txt"
                filename = filename.replace(" ", "_")
                file_path = OUTPUT_DIR / filename
                
                # Write case file
                content = []
                if title:
                    content.append(f"Title: {title}")
                if date:
                    content.append(f"Date: {date}")
                if parties:
                    content.append(f"Parties: {parties}")
                content.append("")
                content.append(text)
                
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(content))
                
                processed += 1
                
                # Limit to reasonable number for deployment
                if processed >= 500:
                    break
            
            print(f"Successfully processed {processed} cases to {OUTPUT_DIR}")
            return processed
                
        except requests.exceptions.RequestException as e:
            print(f"Failed to download from {url}: {e}")
            continue
    
    # If all downloads failed, create sample data
    print("\nAll download attempts failed. Creating sample legal case data...")
    return create_sample_data()


if __name__ == "__main__":
    print("=" * 60)
    print("Legal Dataset Setup for RAG Legal Assistant")
    print("=" * 60)
    
    # Check if data already exists
    existing_files = list(OUTPUT_DIR.glob("*.txt"))
    if existing_files:
        print(f"Found {len(existing_files)} existing case files in {OUTPUT_DIR}")
        response = input("Download new data anyway? (y/n): ")
        if response.lower() != 'y':
            print("Skipping download.")
            exit(0)
    
    download_and_process()
    
    final_count = len(list(OUTPUT_DIR.glob("*.txt")))
    print(f"\nSetup complete! Total case files: {final_count}")

