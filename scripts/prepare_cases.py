import os
import argparse
import pdfplumber


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract plain text from a PDF using pdfplumber."""
    text = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text:
                    text.append(page_text)
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
    return "\n".join(text)


def prepare_cases(
    raw_root: str = "data/kaggle_sc_judgments/supreme_court_judgments",
    out_dir: str = "data/casedocs",
    start_year: int = 2023,
    end_year: int = 2024,
) -> None:
    """
    Convert Supreme Court PDF judgments from the Kaggle dataset into plain-text
    files under data/casedocs for use by the RAG system.

    Expected Kaggle structure after unzipping:
      data/kaggle_sc_judgments/
        supreme_court_judgments/
          1950/
            <case_name>.PDF
          1951/
            ...

    This script will:
      - Iterate over years in [start_year, end_year]
      - For each PDF, extract text and save as a .txt file in data/casedocs
    """
    if not os.path.isdir(raw_root):
        raise FileNotFoundError(
            f"Raw Kaggle directory not found at '{raw_root}'. "
            "Please unzip the Kaggle dataset into this path first."
        )

    os.makedirs(out_dir, exist_ok=True)

    for year in range(start_year, end_year + 1):
        year_dir = os.path.join(raw_root, str(year))
        if not os.path.isdir(year_dir):
            print(f"Skipping missing year directory: {year_dir}")
            continue

        print(f"Processing year {year} in {year_dir} ...")

        for file_name in os.listdir(year_dir):
            if not file_name.lower().endswith(".pdf"):
                continue

            pdf_path = os.path.join(year_dir, file_name)

            # Create a reasonable text file name: <year>_<original-name>.txt
            base_name = os.path.splitext(file_name)[0]
            safe_base = base_name.replace(" ", "_")
            out_name = f"{year}_{safe_base}.txt"
            out_path = os.path.join(out_dir, out_name)

            if os.path.exists(out_path):
                # Skip already-processed files
                continue

            print(f"  -> Converting {pdf_path} -> {out_path}")
            text = extract_text_from_pdf(pdf_path)
            if not text.strip():
                print(f"     Warning: no text extracted from {pdf_path}, skipping.")
                continue

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)

    print(f"Finished preparing cases. Text files are in: {out_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Prepare Kaggle Supreme Court judgments for the LegalRAG system."
    )
    parser.add_argument(
        "--raw-root",
        default="data/kaggle_sc_judgments/supreme_court_judgments",
        help="Path to the root of the unzipped Kaggle dataset (supreme_court_judgments folder).",
    )
    parser.add_argument(
        "--out-dir",
        default="data/casedocs",
        help="Output directory where plain-text case files will be written.",
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=2023,
        help="First year to include (e.g., 2023).",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=2024,
        help="Last year to include (e.g., 2024).",
    )

    args = parser.parse_args()
    prepare_cases(
        raw_root=args.raw_root,
        out_dir=args.out_dir,
        start_year=args.start_year,
        end_year=args.end_year,
    )


if __name__ == "__main__":
    main()

import argparse
import json
import os
from pathlib import Path
from typing import List, Dict, Any


def find_english_index_files(root: Path) -> List[Path]:
    """
    Recursively find all `english.index.json` files under the given root.
    The Kaggle / AWS Supreme Court judgments dataset typically stores one such
    file per year or per shard.
    """
    return list(root.rglob("english.index.json"))


def normalise_records(raw: Any) -> List[Dict[str, Any]]:
    """
    Try to normalise the loaded JSON into a list of record dicts.
    The concrete structure can vary slightly; this function handles a few
    common patterns (list of dicts, dict with 'records' / 'items' / 'data').
    """
    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]

    if isinstance(raw, dict):
        for key in ("records", "items", "data"):
            value = raw.get(key)
            if isinstance(value, list):
                return [r for r in value if isinstance(r, dict)]

    return []


def extract_text_from_record(rec: Dict[str, Any], base_dir: Path) -> str:
    """
    Try multiple reasonable keys / strategies to get the judgment text
    for a single record.
    """
    # Direct text fields commonly used in open-judgment datasets.
    for key in ("judgment_text", "judgment", "text", "content"):
        val = rec.get(key)
        if isinstance(val, str) and val.strip():
            return val

    # Some schemas store a relative path to the text file.
    for key in ("file_path", "filepath", "path"):
        rel = rec.get(key)
        if isinstance(rel, str) and rel:
            candidate = (base_dir / rel).resolve()
            if candidate.exists():
                try:
                    return candidate.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    pass

    return ""


def build_doc_text(rec: Dict[str, Any], text: str) -> str:
    """
    Build a single plain-text document that includes useful metadata
    followed by the full judgment text. This is what will be written
    into `data/casedocs/*.txt` for the RAG pipeline to consume.
    """
    title = rec.get("case_title") or rec.get("title") or "Untitled case"
    date = rec.get("date") or rec.get("judgment_date") or rec.get("decision_date") or "Unknown date"
    parties = rec.get("parties") or rec.get("petitioner_respondent") or rec.get("case_parties") or ""
    category = rec.get("category") or rec.get("category_name") or rec.get("bench") or ""
    citation = rec.get("citation") or rec.get("citations") or ""

    meta_lines = [
        f"Title: {title}",
        f"Date: {date}",
    ]
    if parties:
        meta_lines.append(f"Parties: {parties}")
    if category:
        meta_lines.append(f"Category: {category}")
    if citation:
        meta_lines.append(f"Citation: {citation}")

    header = "\n".join(meta_lines)
    return f"{header}\n\n{text.strip()}"


def prepare_kaggle_dataset(dataset_root: Path, output_dir: Path) -> None:
    """
    Convert the Kaggle Supreme Court judgments dataset into plain-text
    case documents under `data/casedocs/`, which the existing RAG
    pipeline expects.

    This script is conservative: if it cannot confidently extract text
    from a record, it simply skips that record.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    index_files = find_english_index_files(dataset_root)
    if not index_files:
        print(f"No english.index.json files found under {dataset_root}. "
              f"Please ensure the Kaggle dataset is fully downloaded and extracted.")
        return

    total_docs = 0
    for index_path in index_files:
        base_dir = index_path.parent
        print(f"Processing index: {index_path}")

        try:
            raw = json.loads(index_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  Skipping {index_path} (could not parse JSON): {e}")
            continue

        records = normalise_records(raw)
        if not records:
            print(f"  No records found in {index_path}")
            continue

        for i, rec in enumerate(records):
            text = extract_text_from_record(rec, base_dir)
            if not text.strip():
                continue

            case_id = (
                rec.get("id")
                or rec.get("case_id")
                or rec.get("diary_no")
                or rec.get("diary_number")
                or f"{index_path.stem}_{i}"
            )

            safe_id = "".join(c for c in str(case_id) if c.isalnum() or c in ("-", "_"))
            if not safe_id:
                safe_id = f"{index_path.stem}_{i}"

            doc_text = build_doc_text(rec, text)
            out_path = output_dir / f"{safe_id}.txt"
            try:
                out_path.write_text(doc_text, encoding="utf-8")
                total_docs += 1
            except Exception as e:
                print(f"  Failed to write {out_path}: {e}")

    print(f"Finished. Wrote {total_docs} case documents into {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Prepare the Kaggle Supreme Court judgments dataset for the LegalRAG app "
            "by converting judgments into plain-text case documents under data/casedocs/."
        )
    )
    parser.add_argument(
        "--dataset-root",
        type=str,
        required=True,
        help="Path to the root directory of the downloaded Kaggle dataset "
             "(e.g. ./legal-dataset-sc-judgments-india-19502024).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/casedocs",
        help="Output directory for generated case documents (default: data/casedocs).",
    )

    args = parser.parse_args()
    dataset_root = Path(args.dataset_root).resolve()
    output_dir = Path(args.output_dir).resolve()

    if not dataset_root.exists():
        raise SystemExit(f"Dataset root {dataset_root} does not exist. "
                         f"Please download and extract the Kaggle dataset first.")

    prepare_kaggle_dataset(dataset_root, output_dir)


if __name__ == "__main__":
    main()


