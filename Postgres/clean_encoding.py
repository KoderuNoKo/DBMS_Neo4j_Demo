import os
import csv
import re

# Folder containing your unzipped ml-latest dataset
INPUT_DIR = "C:\\Users\\acer\\Downloads\\Documents\\HK_251\\DBMS\\Neo4j\\neo4j_demo\\ml-latest"
OUTPUT_DIR = os.path.join(INPUT_DIR, "cleaned")

# Ensure output folder exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def clean_ascii(text):
    """Remove all non-ASCII characters from a string"""
    if text is None:
        return ""
    # Keep only ASCII characters (code points 0–127)
    return re.sub(r'[^\x00-\x7F]+', '', text)

def clean_csv_file(input_path, output_path):
    """Read a CSV, remove non-ASCII chars, write cleaned version"""
    with open(input_path, "r", encoding="utf-8", errors="ignore") as infile, \
         open(output_path, "w", encoding="utf-8", newline="") as outfile:

        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        for row in reader:
            cleaned_row = [clean_ascii(cell) for cell in row]
            writer.writerow(cleaned_row)

    print(f"Cleaned: {os.path.basename(input_path)}")

def clean_all_csvs(input_dir, output_dir):
    for filename in os.listdir(input_dir):
        if filename.lower().endswith(".csv"):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename)
            clean_csv_file(input_path, output_path)

if __name__ == "__main__":
    print(f"Cleaning CSV files in: {INPUT_DIR}")
    clean_all_csvs(INPUT_DIR, OUTPUT_DIR)
    print(f"\n✨ Done! Cleaned files are in: {OUTPUT_DIR}")
