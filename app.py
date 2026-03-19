import streamlit as st
st.set_page_config(layout="wide")
import sys
sys.path.append("src")

import ai_dataset_assistant.data_engine as data_engine
import ai_dataset_assistant.llm_interface as llm
import ui.sidebar as sidebar
import ui.layout as layout

analysis_engine = data_engine.AnalysisEngine()
insights_engine = data_engine.InsightsEngine()

# --- DATA ---> UPLOAD & LOAD
data = None
data_raw = None
data_uploaded = sidebar.data_upload()

if data_uploaded:
    try:
      data_raw = data_engine.data_load(data_uploaded)
    except ValueError as e:
       st.error(str(e))

viewer, analysis, view, insights = layout.init_layout(
                         has_data = data_raw is not None

)

data_cleaned = None
chart = None

if "llm_feedback" not in st.session_state:
        st.session_state.llm_feedback = None

if data_uploaded is None:
   st.session_state.llm_feedback = None


if viewer is not None:

   data_clean_nan = data_engine.data_clean_nan(data_raw)
   info = data_engine.data_info(data_clean_nan)
   input_for_llm = data_engine.identify_data(data_clean_nan)

   if st.session_state.llm_feedback is None:
      with st.sidebar.spinner("Inspecting dataset structure..."):
         st.session_state.llm_feedback = llm.inspect_dataset(
            columns = input_for_llm["columns"],
            head = input_for_llm["head"]
         )
   
   llm_feedback = st.session_state.llm_feedback

   if info:
      sidebar.data_info(data_raw, info, llm_feedback)

      if llm_feedback.get("combined_metadata_column"):
         combined_index = llm_feedback["metadata_column_index"]
         multicol = data_raw.columns[combined_index]
         data_cleaned = data_engine.multicol_separator(data_clean_nan, multicol)

         if llm_feedback["dataset_format"] in ["wide_time_series", "combined_dimension_wide"]:
            time_colls = data_engine.time_cols_detector(data_cleaned.columns)
            data_cleaned = data_engine.reshape_from_wide(data_cleaned, time_colls)

      layout.data_viewer(viewer, data_raw, data_cleaned)

if analysis is not None:
   
   run, query, plan_box, result_box = layout.analysis_tab(analysis)
   if run and query:
      plan, description, chart, question = data_engine.run_analysis(data_cleaned, query)
      
      description_text = "\n".join(description.values())
      data = analysis_engine.run_analysis(data_cleaned, plan)
      
      with plan_box:
         st.markdown(description_text)

      with result_box:
         st.write(data)

if insights is not None:

   if data is not None:
   
      plot_box, insights_box, export = layout.insights_tab(insights, question)

      charted, fig, insights = insights_engine.run_insights(data, chart, question, plan,)

      with plot_box:
         st.pyplot(fig)

      with insights_box:
         st.markdown(insights)

