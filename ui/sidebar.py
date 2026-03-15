import streamlit as st

def data_upload():
   return st.sidebar.file_uploader("📁 Upload CSV/TSV file", 
                                   type=["csv","tsv"])

def data_info(data, info: dict, structure: dict):
    st.sidebar.subheader("Dataset Info:")

    st.sidebar.write(f"Rows: {info["rows"]}")
    st.sidebar.write(f"Columns: {info["columns"]}")
    st.sidebar.write(f"Missing: {info["missing"]:.2f} %")
    st.sidebar.write(f"Numeric Columns: {info["numeric_columns"]}")
    
    st.sidebar.divider()

    st.sidebar.subheader("Structure")

    st.sidebar.write("Format:", structure["dataset_format"])
    st.sidebar.write("Combined metadata:", structure["combined_metadata_column"])
    if structure["combined_metadata_column"]:
        index = structure["metadata_column_index"]
        column_name = data.columns[index]
        
        st.sidebar.write("Metadata column index:", index)
        st.sidebar.write("Metadata column name:", column_name)
