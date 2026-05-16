# NYC Rodent Inspection Pipeline

End-to-end data pipeline built on AWS using Medallion Architecture.

## Architecture
- **Bronze Layer** ✅ — Scheduled ingestion via AWS Lambda + EventBridge
- **Silver Layer** 🔲 — In progress
- **Gold Layer** 🔲 — Planned

## Stack
- Python, AWS Lambda, AWS S3, AWS DynamoDB, AWS EventBridge

## Data Source
NYC Open Data — Rodent Inspection Dataset

## Status
Active. Ingesting daily since Feb 2025 where data ingested started from July 2023.