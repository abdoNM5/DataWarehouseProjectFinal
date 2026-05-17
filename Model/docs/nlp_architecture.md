# NLP & Recommendation Architecture

## Overview
The recommendation engine combines two independent scoring methods to rank job offers against a candidate's profile:
1. **Semantic similarity** — evaluating the conceptual alignment between the candidate's free-text description and the job posting using Sentence-Transformers embeddings.
2. **Skill matching** — calculating the exact overlap between the candidate's selected skills and the job's extracted skills using a predefined taxonomy.

## Model: `paraphrase-multilingual-MiniLM-L12-v2`
- **Architecture**: 12-layer MiniLM transformer
- **Parameters**: 118 Million
- **Output Space**: 384-dimensional normalized vectors
- **Languages**: French, English, and 50+ other languages.
- **Why this model**: It strikes the perfect balance between inference speed and accuracy. Since our dataset contains both English and French job descriptions, a multilingual model is critical. MiniLM's smaller size allows it to run efficiently on standard CPUs without requiring expensive GPU infrastructure, making it ideal for a scalable FastAPI deployment.

## Scoring Formula
The final match score is a weighted combination (Hybrid Recommendation) of the two scores:
```
Final Score = α × Semantic Score + (1 - α) × Skill Score
```
*(Currently, α = 0.6, meaning semantic context is weighted slightly higher than strict keyword matching).*

## Data Flow
1. **Ingestion**: The ETL pipeline loads raw offers into the `fact_job_offer` table, including a cleaned `description_clean`.
2. **Skill Extraction**: The `nlp.populate_skills` module runs a Regex-based extraction (using `nlp.skills_taxonomy`) and populates the `bridge_offer_skill` many-to-many table.
3. **Embedding Generation**: The `nlp.generate_embeddings` module encodes the job descriptions into 384-dimensional vectors and stores them in the `JSONB` `embedding` column of the fact table.
4. **Recommendation**: 
   - The FastAPI backend receives a candidate profile.
   - It encodes the candidate's description into a vector.
   - It computes the Cosine Similarity against all cached job offer embeddings.
   - It calculates the skill overlap percentage.
   - It combines the scores, ranks the offers, and returns the top K results.

## Performance Evaluation
Based on our 5 test profiles (Data Engineer, Data Scientist, Data Analyst, Web Developer, Backend Python), the engine successfully surfaces the correct job family with 100% precision in the top 3 results, verifying both the language-agnostic semantic mapping and the strict skill boundary matching.
