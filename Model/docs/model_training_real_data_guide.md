# Model Training on Real Data (Google Colab & Local Sync)

To train your recommendation model on the **real data** from your friend's database, we have set up a complete Colab-to-Local pipeline. This ensures you can leverage Colab's fast GPUs to process all 36k+ descriptions in minutes, then sync the data locally for your FastAPI backend.

## Step 1: Run the Training on Google Colab

Since there are thousands of records, using your CPU locally could take over an hour. We created a Colab Notebook that uses a GPU and connects directly to your friend's Neon DB.

1. Go to Google Colab: https://colab.research.google.com/
2. Click **File -> Upload notebook** and upload this file from your project:
   `notebooks/02_model_training_colab.ipynb`
3. Once open, make sure to enable the GPU:
   - Click **Runtime -> Change runtime type**
   - Under Hardware accelerator, select **T4 GPU**
   - Click Save.
4. Run all the cells sequentially. 
5. The notebook will automatically download a file named `job_embeddings.parquet` to your computer at the end. **Move this file into your project's `scripts/` folder**.

## Step 2: Sync Real Data and Embeddings to Local Database

Your FastAPI application points to your local database (`jobs_dw`), so you need the real data locally.

1. Ensure your local database is running (e.g. `docker-compose up -d`).
2. Make sure you placed the `job_embeddings.parquet` inside the `scripts/` folder.
3. Open a terminal and run the synchronization script:

```bash
cd scripts
pip install pandas sqlalchemy psycopg2-binary fastparquet
python sync_real_data_and_load_embeddings.py
```

**What this script does:**
- It connects to your friend's Neon DB (read-only) and pulls all the clean data.
- It overwrites your local `jobs_dw` dummy data with the real data.
- It parses the `job_embeddings.parquet` you downloaded from Colab and loads the computed semantic vectors into the local `fact_job_offer.embedding` column.

## Result

Your `fact_job_offer` table in your local PostgreSQL now contains the real job offers **and** their corresponding NLP embeddings. Your `api/routers/recommend.py` and `frontend` will now work fully functionally with the real data!
