import pandas as pd
import numpy as np
import re

from .llm_interface import inspect_dataset, create_analysis_plan 

# ---> DATA Loader

def data_load(up_data: pd.DataFrame) -> pd.DataFrame:
    
    if up_data is None:
        raise ValueError("No file uploaded")
    
    filename = up_data.name.lower()

    if filename.endswith(".csv"):
        separator = ","
    elif filename.endswith(".tsv"):
        separator = "\t"
    else:
        raise ValueError("Unsuported file type. Please upload CSV or TSV.")

    try:
        data = pd.read_csv(up_data, sep=separator)
    except pd.errors.EmptyDataError:
        raise ValueError("CSV file is empty")
    except pd.errors.ParserError:
        raise ValueError("CSV file is malformed")
    except UnicodeDecodeError:
        raise ValueError("Unsupported file encoding")
    except Exception as e:
        raise ValueError(f"Failed to load CSV file: {e}")
    
    if data.empty:
        raise ValueError("CSV contains no rows")
    
    return data

# ---> DATA NaN different format handling

def data_clean_nan(data: pd.DataFrame) -> pd.DataFrame:
    
    data = data.copy()

    obj_cols = data.select_dtypes(include="object").columns
    data[obj_cols] = data[obj_cols].apply(lambda col: col.str.strip())

    data = data.replace({":": np.nan, "NA": np.nan, "N/A": np.nan})

    for col in data.select_dtypes(include="object"):
        data[col] = pd.to_numeric(data[col], errors="ignore")

    return data

# ---> DATA Info for LLM

def identify_data(data: pd.DataFrame) -> dict:
        if data is None:
            return {}
        
        return {
            "columns": data.columns.tolist(),
            "head": data.head(3).to_json(orient="records")
        }

# ---> DATA Info

def data_info(data: pd.DataFrame) -> dict:
    
    if data is None:
        return {}
    
    return {
        "rows": data.shape[0],
        "columns": data.shape[1],
        "missing": int(data.isna().sum().sum()),
        "numeric_columns": int(data.select_dtypes(include="number").shape[1]),
    }

# ---> Combined metadata separator

def multicol_separator(data, multicol):

    data = data.copy()

    if multicol in data.columns:

        splitters = [",", ";", "|"]
    
        name_splitter = next((s for s in splitters if s in multicol), ",")
        first, last = multicol.rsplit(name_splitter, 1)
        multicols = first.split(name_splitter) + [last]

        value_splitter = next(
            (s for s in splitters if data[multicol].astype(str).str.contains(s).any()),
              ",")
        split_data = data[multicol].astype(str).str.split(
            value_splitter,
            n=len(multicols)-1,
            expand=True
        )

        split_data.columns = multicols

        data = pd.concat([data, split_data], axis=1)
        data = data.drop(columns=[multicol])

    return data

def time_cols_detector(columns):
    
    patterns = [
        r"^\d{4}$",           # 2019
        r"^\d{4}-S[1-2]$",    # 2023-S1
        r"^\d{4}-Q[1-4]$",    # 2023-Q1
        r"^\d{4}-M\d{2}$",    # 2023-M01
        r"^\d{4}-\d{2}$",     # 2023-01
    ]

    time_cols = []

    for col in columns:
        col = str(col).strip()
        if any(re.match(pattern, col) for pattern in patterns):
            time_cols.append(col)

    return time_cols

def reshape_from_wide(data, time_cols):

    data = data.copy()
    data.columns = data.columns.map(lambda col: str(col).strip())
    
    time_cols = [str(col).strip() for col in time_cols]
    id_cols = [col for col in data.columns if col not in time_cols]

    data = data.melt(
        id_vars = id_cols,
        value_vars = time_cols,
        var_name = "period",
        value_name = "value"
    )

    return data

def run_analysis(data: pd.DataFrame, query: str):

    plan = create_analysis_plan(data, query)

    #raw_result = execute_analysis(data, query)

    #explanation = explain_results(raw_result, query)

    return plan#, raw_result, explanation

def execute_analysis(data, query):
    
    query_lower = query.lower()

    if "average" in query_lower:
        return data.mean(numeric_only=True)

    if "max" in query_lower:
        return data.max(numeric_only=True)

    return None