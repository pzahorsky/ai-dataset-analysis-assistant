import streamlit as st

# ---> TABS Handler

def init_layout(
        has_data: bool,
):
    view = None

    tab_names = []

    if has_data:
        tab_names.append("📑 Data Viewer")
        tab_names.append("🧠 Analysis")
        tab_names.append("💡 Insights")

    if not tab_names:
        return None, None, view, None
    
    created_tabs = st.tabs(tab_names)

    if not has_data:
        viewer, analysis, insights = None, None, None

    tab_num = 0
    if has_data:
        viewer = created_tabs[tab_num]
        tab_num += 1

    if has_data:
        analysis = created_tabs[tab_num]
        tab_num += 1

    if has_data:
        insights = created_tabs[tab_num]
        tab_num += 1

    return viewer, analysis, view, insights

# ---> Data Viewer
 
def data_viewer(viewer, data_raw, data_cleaned):
    
    if data_raw is None and data_cleaned is None:
        return
    
    with viewer:

        view = st.radio(
            "Choose View Option",
            ["Raw data", "Cleaned data"],
            index=0,
            horizontal=True
        )

        data = data_raw

        if view == "Cleaned data" and data_cleaned is not None:
            data = data_cleaned

        n = len(data)
        height = min(40 + n * 35, 700)

        st.dataframe(
            data,
            width="stretch",
            height=height
        )
        
# ---> Analysis

def analysis_tab(analysis):
    
    with analysis:
        st.subheader("Describe the analysis you want to perform.")
        query = st.text_area("Place for Analysis Plan"
                             , label_visibility="collapsed")

        run = st.button("Run Analysis")

        st.markdown("---")

        plan, result = st.columns([1,2])

        with plan:
            st.subheader("Analysis Plan")
            plan_placeholder = st.empty()
        with result:
            st.subheader("Result")
            result_placeholder = st.empty()

        return run, query.strip(), plan_placeholder, result_placeholder
    
def insights_tab(insights):

    with insights:

        plot, insight= st.columns([1,1])

        with plot:
            st.subheader("Plot header")
            plot_placeholder = st.empty()

        with insight:
            st.subheader("Insights header")
            insight_placeholder = st.empty()

        return plot_placeholder, insight_placeholder

    

