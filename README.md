# Introduction

- This project demonstrates how to extract, structure, and store **MRI imaging metadata** (from `.ima` files) into a **Neo4j graph database**.  
- It uses the **Lumbar Spine MRI Dataset** from Mendeley and integrates radiologists’ clinical notes for a rich, queryable medical graph.

# Project Structure

```
neo4j_demo/
├── 01_MRI_Data/
├── Radiologists Notes for Lumbar Spine MRI Dataset/
├── mri_export/
├── mri_export_pg/
├── Postgres/
├── MriExporter/
└── .venv/
```

## Notable folders and files 
### Data
- `01_MRI_Data` Raw MRI dataset (unzipped from `k57fr854j2-2.zip`)
- `Radiologists Notes for Lumbar Spine MRI Dataset` Radiologists Notes for Lumbar Spine MRI Dataset/
- `mri_export` Output folder for generated CSV files
- `ml-latest` MovieLens dataset for TA submission
	- `cleaned` (optional) cleaned csv files of MovieLens dataset in case of encoding failure

### Source code
- `/MriExporter` Python module for processing the dataset. To use it run the following command. The module will automatically process the dataset in `./01_MRI_Data` into csv files in `./mri_export`

```bash
python ./MriExporter/main.py
```

- `./Postgres` contain all scripts for works on PostgreSQL

### Others

- `req.txt` list of python libraries. Get all dependencies by activating a python virtual environment and run
```bash
pip install -r ./req.txt
```
- Or update it with your dependencies
```bash
pip freeze > ./req.txt
```

# Image Storage

- The image is stored in Neo4j as a URL, which can be used to get the file via a **Simple HTTP Server** 
- To set up the server, in the `01_MRI_Data` directory, run
```sh
python -m http.server
```
- This command to initialize a minimal HTTP server to serve the `.ima` file via said URL.