import pandas as pd
import numpy as np
import re
import matplotlib.pyplot as plt
import matplotx as mpx
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
import io

from .llm_interface import inspect_dataset, create_analysis_plan, conclude_insights

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
        try:
            data[col] = pd.to_numeric(data[col])
        except (ValueError, TypeError):
            pass

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
        "missing": ((int(data.isna().sum().sum())) / len(data)),
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

# ---> Time columns detector

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

# ---> DATA Fromat Transformation Wide ---> Tiny
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

class AnalysisEngine:

    def run_analysis(self, data: pd.DataFrame, plan: dict):

        data = data.copy()

        filters = plan.get("filters", {})
        group_by = plan.get("group_by", [])
        metric = plan.get("metric", "")
        operation = plan.get("operation", "")

        data = self.data_filter(data,filters)
        data = self.group_aggregate(data, group_by, metric, operation)

        debug_text = (
            f"filters: {filters}\n"
            f"group_by: {group_by}\n"
            f"metric: {metric}\n"
            f"operation: {operation}"
        )

        return data
    
    def data_filter(self, data: pd.DataFrame, filters: dict):

        for col, value in filters.items():

            if isinstance(value, list):
                data = data[data[col].isin(value)]
            else:
                data = data[data[col] == value]

        return data
    
    def group_aggregate(self, data: pd.DataFrame, group_by: list,
                         metric: str, operation: str):
        
        data[metric] = pd.to_numeric(data[metric], errors="coerce")

        data = (
            data.groupby(group_by)[metric]
            .agg(operation)
            .reset_index()
        )

        data = data.dropna(subset=[metric])

        return data
    
class InsightsEngine:

    def run_insights(self, data: pd.DataFrame, chart: dict, 
                     question: str, plan: dict):

        data = data.copy()

        chart_type = chart.get("chart_type", "")
        x = chart.get("x", "")
        y = chart.get("y", "")

        other_cols = [col for col in data.columns if col not in [x,y]]

        fig, group_col = self.plot(data, chart_type, x, y, other_cols)

        insights = conclude_insights(question, plan, chart, data, group_col)

        return fig, insights
    
    def plot(self, data, chart_type, x, y, other_cols):

        plt.style.use(mpx.styles.nord)
        fig,ax = plt.subplots()

        group_col = None
        for col in other_cols:
            if data[col].nunique() > 1 and data[col].dtype == "object":
                group_col = col
                break

        if chart_type == "line":
            if group_col:
                for unique in data[group_col].unique():
                    data_filt = data[data[group_col] == unique].sort_values(by=x)
                    ax.plot(data_filt[x], data_filt[y], label=str(unique))
                ax.legend()
            else:
                data = data.sort_values(by=x)
                ax.plot(data[x], data[y])

        ax.set_xlabel(x)
        ax.set_xticks(ax.get_xticks()[::2])
        ax.set_ylabel(y)
        ax.tick_params(axis="x", labelrotation=60)

        return fig, group_col

class ReportEngine:

    def build_pdf(self, fig, title, plan, conclusion):
        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        styles = getSampleStyleSheet()
        story = []

        plan_text = self.to_paragraph_text(plan)
        conclusion_text = self.to_paragraph_text(conclusion)

        story.append(Paragraph(str(title), styles["Title"]))

        story.append(Paragraph("Analysis Plan", styles["Heading2"]))
        story.append(Spacer(1, 2 * mm))

        plan_items = plan_text.split("-")
        plan_items = [item.strip() for item in plan_items if item.strip()]

        for item in plan_items:
            story.append(Paragraph(f"• {item}", styles["BodyText"]))
            story.append(Spacer(1, 1.5 * mm))
        story.append(Spacer(1, 8 * mm))

        img_buffer = self.fig_to_buffer(fig)
        story.append(Image(img_buffer, width=170 * mm, height=95 * mm))
        story.append(Spacer(1, 6 * mm))

        clean_text = " ".join(conclusion_text.split())
        story.append(Paragraph(clean_text, styles["BodyText"]))
        story.append(Spacer(1, 8 * mm))

        doc.build(story)
        buffer.seek(0)

        return buffer

    def fig_to_buffer(self, fig, dpi=300):
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", dpi=dpi, bbox_inches="tight", facecolor="white")
        buffer.seek(0)

        return buffer

    def to_paragraph_text(self, value):
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return "<br/>".join(str(item) for item in value)
        if isinstance(value, dict):
            return "<br/>".join(f"{k}: {v}" for k, v in value.items())
        
        return str(value)
