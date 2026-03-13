from openai import OpenAI
from dotenv import load_dotenv
import json
import streamlit as st

load_dotenv()

client = OpenAI()

def inspect_dataset(columns, head):
        
    prompt = f"""
    You are a dataset structure inspector.

    Analyze the dataset structure using:
    - column names
    - sample rows

    Column names:
    {columns}

    Sample rows:
    {head}

    Return only valid JSON in this exact format:

    {{
    "combined_metadata_column": false,
    "metadata_column_index": null,
    "dataset_format": ""
    }}

    Rules:
    - "combined_metadata_column" must be true if one column appears to contain multiple metadata dimensions combined in a single string.
    - "dataset_format" must be one of:
    "tidy", "wide_time_series", "combined_dimension_wide", "unknown"
    - "metadata_column_index" must be the integer index of that column (0-based), otherwise null
    - Return JSON only.
    """

    try:
        response = client.responses.create(
            model="gpt-5",
            input=prompt
        )

        result = response.output_text.strip()

        return json.loads(result)

    except Exception:
        return {
            "combined_metadata_column": False,
            "dataset_format": "unknown"
        }

def create_analysis_plan(data, query):
    
    columns = ", ".join(data.columns)

    category_columns = data.select_dtypes(include=["object", "category"]).columns

    unique_columns = {}

    for col in category_columns:
        uniques = data[col].dropna().unique()[:10].tolist()
        unique_columns[col] = uniques

    prompt = f"""

    You are the data analyst planer.
    
    Your tasks is to translate user question into a structured analysis plan
    that can be executed using pandas.

    User question:{query}

    Dataset columns:
    {columns}
    
    Unique column values:
    {unique_columns}

    Return very short analysis plan strictly as JSON. 
    Return explenations strictly inside JSON..

    {{
    "plan": {{
        "filters": {{}},
        "group_by": [],
        "metric": "",
        "operation": ""
    }}
    "ui_description": {{
        "filters": "- ",
        "group_by": "- ",
        "metric": "- ",
        "operation": "- "
        }}
    }}


    Rules:
    - Use only columns which exists in dataset.
    - "filters" should contain only filtering conditions according to question.
    - "group_by" should contain columns used for aggregation or comparison.
    - "metric" should describe what value should be measured(f.e. price, amount, ...)
    - "operation" should describe analytical action. (Allowed agg functions: mean, sum, count, min, max, median, std) 
    - Do not invent anything, stick to the dataset columns.
    - Description field should be short bullets strings.
    - Make output usable for both backend and frontend.
    - The response must start with {{ and end with }}
    """

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    response_data = json.loads(response.output_text)
    plan = response_data.get("plan", {})
    description = response_data.get("ui_description", {})

    return plan, description