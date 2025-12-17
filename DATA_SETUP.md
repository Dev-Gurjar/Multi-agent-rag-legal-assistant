# Legal Dataset Setup Guide

This guide explains how to set up the legal case dataset for the RAG Legal Assistant.

## Automatic Setup (Recommended)

The app will **automatically download** the dataset on first run if `data/casedocs/` is empty. This works on:
- ✅ Streamlit Cloud (automatic)
- ✅ Local development (automatic)

## Manual Setup

If you want to manually download and prepare the dataset:

### Option 1: Using the Setup Script

```bash
python scripts/setup_data.py
```

This will:
- Download the Indian Supreme Court Judgment Database from GitHub
- Convert it to text files in `data/casedocs/`
- Process up to 500 cases (configurable)

### Option 2: Using the Advanced Fetcher

```bash
# Download from GitHub (default)
python scripts/fetch_legal_data.py

# Process a local CSV file
python scripts/fetch_legal_data.py --file path/to/your/file.csv

# Process a local JSON file
python scripts/fetch_legal_data.py --file path/to/your/file.json

# Download from a URL
python scripts/fetch_legal_data.py --url https://example.com/dataset.csv

# Limit number of cases and filter by year
python scripts/fetch_legal_data.py --max-cases 1000 --min-year 2020
```

## Data Sources

### Primary Source: GitHub (Indian SC Judgment Database)

- **URL**: https://github.com/NoelShallum/Indian_SC_Judgment_database
- **Format**: CSV
- **Content**: 5,000+ Supreme Court judgments from 1980-1990
- **Columns**: case_title, case_date, bench, issues, decision, cited_cases
- **Access**: Public, no authentication required ✅

### Alternative Sources

1. **AWS Open Data Registry**: Indian Supreme Court Judgments (1950-2025)
   - Format: JSON/Parquet
   - URL: https://registry.opendata.aws/indian-supreme-court-judgments/
   - Note: May require different processing

2. **LawSum Dataset**: 10,000+ judgments with summaries
   - Format: Various
   - Note: May require academic access

3. **MILDSum Dataset**: 3,122 judgments with summaries
   - GitHub: https://github.com/Law-AI/MILDSum
   - Format: JSON/CSV

## Data Format

The system expects text files in `data/casedocs/` with the following structure:

```
Title: Case Title Here
Date: 2023-01-15
Parties: Petitioner vs Respondent

[Full judgment text here...]
```

Each `.txt` file represents one case judgment.

## For Streamlit Cloud Deployment

The app automatically handles dataset download on first run. However, for faster startup, you can:

1. **Pre-populate the repo** (recommended):
   ```bash
   # Run locally
   python scripts/setup_data.py
   
   # Commit the data files
   git add data/casedocs/
   git commit -m "Add legal case dataset"
   git push
   ```

2. **Let it auto-download** (works but slower first run):
   - Just deploy - the app will download on first user visit
   - Subsequent runs will use cached data

## Troubleshooting

### Dataset download fails

- Check internet connection
- Verify the GitHub URL is accessible
- Check Streamlit Cloud logs for errors

### No cases found

- Ensure `data/casedocs/` directory exists
- Check that `.txt` files are present
- Verify file permissions

### Wrong data format

- The script auto-detects column names
- Check console output for detected columns
- Adjust column mapping in `scripts/setup_data.py` if needed

## File Structure

```
LegalRAG/
├── data/
│   ├── casedocs/          # Case text files (auto-populated)
│   │   ├── 2020_00001_case_title.txt
│   │   ├── 2020_00002_another_case.txt
│   │   └── ...
│   └── README.md
├── scripts/
│   ├── setup_data.py       # Simple setup script
│   └── fetch_legal_data.py # Advanced fetcher
└── app.py                  # Main Streamlit app (auto-downloads data)
```

## Notes

- The dataset is downloaded from publicly available sources
- No API keys or authentication required
- Data is processed and stored locally in your repo
- For production, consider pre-processing and committing data files

