"""
Fetch and prepare legal datasets for the RAG Legal Assistant.

This script downloads legal case data from publicly available sources
and converts them to the format expected by the RAG system (text files in data/casedocs/).

Supported sources:
1. GitHub: Indian Supreme Court Judgment Database (1980-1990)
2. AWS Open Data Registry: Indian Supreme Court Judgments (1950-2025)
3. Direct CSV/JSON files from URLs
"""

import os
import sys
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
import json
from urllib.parse import urlparse

# Add parent directory to path to import project modules if needed
sys.path.insert(0, str(Path(__file__).parent.parent))

OUTPUT_DIR = Path("data/casedocs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# GitHub dataset URL (Indian Supreme Court Judgment Database)
GITHUB_CSV_URL = "https://raw.githubusercontent.com/NoelShallum/Indian_SC_Judgment_database/main/SC_Judgments_1980_1990.csv"

# AWS Open Data Registry base URL (if accessible)
AWS_BASE_URL = "https://registry.opendata.aws/indian-supreme-court-judgments/"


def download_file(url: str, output_path: Path, chunk_size: int = 8192) -> bool:
    """Download a file from URL to local path."""
    try:
        print(f"Downloading {url}...")
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\rProgress: {percent:.1f}%", end='', flush=True)
        
        print(f"\nDownloaded to {output_path}")
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False


def parse_year(date_str):
    """Parse year from various date formats."""
    if pd.isna(date_str) or not date_str:
        return None
    try:
        dt = pd.to_datetime(str(date_str), errors="coerce")
        if pd.isna(dt):
            return None
        return dt.year
    except Exception:
        return None


def process_github_dataset(csv_path: Path, max_cases: int = None, min_year: int = None):
    """
    Process the GitHub Indian SC Judgment Database CSV.
    
    Expected columns based on the dataset:
    - case_title, case_date, bench, issues, decision, cited_cases
    """
    print(f"\nProcessing GitHub dataset: {csv_path}")
    
    try:
        df = pd.read_csv(csv_path)
        print(f"Loaded {len(df)} cases from CSV")
        
        # Display column names to help debug
        print(f"Columns found: {list(df.columns)}")
        
        # Map common column name variations
        col_mapping = {
            'case_title': ['case_title', 'title', 'Case Title', 'case name'],
            'case_date': ['case_date', 'date', 'Case Date', 'judgment_date'],
            'decision': ['decision', 'judgment', 'judgment_text', 'Decision', 'text'],
            'parties': ['parties', 'petitioner', 'respondent', 'Parties'],
            'bench': ['bench', 'judges', 'Bench'],
            'issues': ['issues', 'Issues'],
            'cited_cases': ['cited_cases', 'Cited Cases']
        }
        
        # Find actual column names
        actual_cols = {}
        for key, possible_names in col_mapping.items():
            for col in df.columns:
                if col.lower() in [name.lower() for name in possible_names]:
                    actual_cols[key] = col
                    break
        
        print(f"Mapped columns: {actual_cols}")
        
        # Filter by year if specified
        if 'case_date' in actual_cols and min_year:
            df['year'] = df[actual_cols['case_date']].apply(parse_year)
            df = df[df['year'].notna()]
            df = df[df['year'] >= min_year]
            print(f"Filtered to {len(df)} cases from year {min_year} onwards")
        
        # Limit number of cases if specified
        if max_cases:
            df = df.head(max_cases)
            print(f"Limited to {max_cases} cases")
        
        # Process each case
        processed = 0
        for idx, row in df.iterrows():
            # Get text content (decision/judgment is primary, fallback to combining fields)
            text_parts = []
            
            if 'decision' in actual_cols and pd.notna(row.get(actual_cols['decision'])):
                text_parts.append(str(row[actual_cols['decision']]))
            elif 'issues' in actual_cols and pd.notna(row.get(actual_cols['issues'])):
                text_parts.append(str(row[actual_cols['issues']]))
            
            if not text_parts:
                continue
            
            text = "\n\n".join(text_parts)
            if len(text.strip()) < 50:  # Skip very short entries
                continue
            
            # Get metadata
            title = str(row.get(actual_cols.get('case_title', ''), '')).strip() if 'case_title' in actual_cols else ""
            date = str(row.get(actual_cols.get('case_date', ''), '')).strip() if 'case_date' in actual_cols else ""
            parties = str(row.get(actual_cols.get('parties', ''), '')).strip() if 'parties' in actual_cols else ""
            bench = str(row.get(actual_cols.get('bench', ''), '')).strip() if 'bench' in actual_cols else ""
            issues = str(row.get(actual_cols.get('issues', ''), '')).strip() if 'issues' in actual_cols else ""
            
            # Build filename
            year = parse_year(date) if date else None
            safe_title = "".join(c if c.isalnum() or c in "-_ " else "_" for c in title[:50]) if title else f"case_{idx}"
            filename = f"{year or 'unknown'}_{idx:05d}_{safe_title[:30]}.txt"
            filename = filename.replace(" ", "_")
            file_path = OUTPUT_DIR / filename
            
            # Write case file
            content_lines = []
            if title:
                content_lines.append(f"Title: {title}")
            if date:
                content_lines.append(f"Date: {date}")
            if parties:
                content_lines.append(f"Parties: {parties}")
            if bench:
                content_lines.append(f"Bench: {bench}")
            if issues:
                content_lines.append(f"Issues: {issues}")
            content_lines.append("")  # Blank line before judgment text
            content_lines.append(text)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(content_lines))
            
            processed += 1
        
        print(f"Successfully processed {processed} cases to {OUTPUT_DIR}")
        return processed
        
    except Exception as e:
        print(f"Error processing GitHub dataset: {e}")
        import traceback
        traceback.print_exc()
        return 0


def process_json_dataset(json_path: Path, max_cases: int = None, min_year: int = None):
    """Process a JSON dataset (e.g., from AWS Open Data Registry)."""
    print(f"\nProcessing JSON dataset: {json_path}")
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle both list and dict formats
        if isinstance(data, dict):
            cases = data.get('cases', data.get('judgments', [data]))
        elif isinstance(data, list):
            cases = data
        else:
            print("Unknown JSON format")
            return 0
        
        print(f"Loaded {len(cases)} cases from JSON")
        
        processed = 0
        for idx, case in enumerate(cases):
            if max_cases and idx >= max_cases:
                break
            
            # Extract fields (adjust based on actual JSON structure)
            text = case.get('judgment_text', case.get('text', case.get('decision', '')))
            if not text or len(text.strip()) < 50:
                continue
            
            title = case.get('case_title', case.get('title', ''))
            date = case.get('date', case.get('judgment_date', ''))
            parties = case.get('parties', case.get('petitioner', ''))
            
            year = parse_year(date) if date else None
            if min_year and year and year < min_year:
                continue
            
            # Build filename
            safe_title = "".join(c if c.isalnum() or c in "-_ " else "_" for c in str(title)[:50]) if title else f"case_{idx}"
            filename = f"{year or 'unknown'}_{idx:05d}_{safe_title[:30]}.txt"
            filename = filename.replace(" ", "_")
            file_path = OUTPUT_DIR / filename
            
            # Write case file
            content_lines = []
            if title:
                content_lines.append(f"Title: {title}")
            if date:
                content_lines.append(f"Date: {date}")
            if parties:
                content_lines.append(f"Parties: {parties}")
            content_lines.append("")
            content_lines.append(text)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(content_lines))
            
            processed += 1
        
        print(f"Successfully processed {processed} cases to {OUTPUT_DIR}")
        return processed
        
    except Exception as e:
        print(f"Error processing JSON dataset: {e}")
        import traceback
        traceback.print_exc()
        return 0


def main():
    """Main function to fetch and process legal datasets."""
    print("=" * 60)
    print("Legal Dataset Fetcher for RAG Legal Assistant")
    print("=" * 60)
    
    # Option 1: Download from GitHub (easiest, most reliable)
    print("\n[Option 1] Fetching from GitHub: Indian SC Judgment Database")
    temp_csv = Path("data/temp_sc_judgments.csv")
    
    if download_file(GITHUB_CSV_URL, temp_csv):
        processed = process_github_dataset(
            temp_csv,
            max_cases=1000,  # Limit to 1000 cases for initial testing
            min_year=2020   # Get recent cases (adjust as needed)
        )
        if processed > 0:
            print(f"✅ Successfully processed {processed} cases!")
        # Clean up temp file
        if temp_csv.exists():
            temp_csv.unlink()
    else:
        print("⚠️  GitHub download failed, trying alternative sources...")
    
    # Option 2: If user provides a local CSV/JSON file
    print("\n[Option 2] To process a local file, run:")
    print("  python scripts/fetch_legal_data.py --file path/to/your/file.csv")
    print("  python scripts/fetch_legal_data.py --file path/to/your/file.json")
    
    print(f"\n✅ Done! Case files are in: {OUTPUT_DIR}")
    print(f"   Total files: {len(list(OUTPUT_DIR.glob('*.txt')))}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch and prepare legal datasets")
    parser.add_argument("--file", type=str, help="Path to local CSV or JSON file to process")
    parser.add_argument("--max-cases", type=int, default=1000, help="Maximum number of cases to process")
    parser.add_argument("--min-year", type=int, default=2020, help="Minimum year to include")
    parser.add_argument("--url", type=str, help="URL to download dataset from")
    
    args = parser.parse_args()
    
    if args.file:
        file_path = Path(args.file)
        if file_path.suffix.lower() == '.csv':
            process_github_dataset(file_path, max_cases=args.max_cases, min_year=args.min_year)
        elif file_path.suffix.lower() == '.json':
            process_json_dataset(file_path, max_cases=args.max_cases, min_year=args.min_year)
        else:
            print(f"Unsupported file format: {file_path.suffix}")
    elif args.url:
        temp_file = Path("data/temp_download")
        if download_file(args.url, temp_file):
            if temp_file.suffix == '.csv' or 'csv' in args.url.lower():
                process_github_dataset(temp_file, max_cases=args.max_cases, min_year=args.min_year)
            else:
                process_json_dataset(temp_file, max_cases=args.max_cases, min_year=args.min_year)
            temp_file.unlink()
    else:
        main()

