import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import re
from groq import Groq

api_key = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=api_key)

st.set_page_config(page_title="Sample Manager", layout="wide")

# --- INITIALIZATION ---
if 'master_data' not in st.session_state:
    # Added 'Include' column for selection/deselection
    st.session_state.master_data = pd.DataFrame(columns=[
        'Include', 'Sample ID', 'Datestamp', 'Sample Name', 'Run', 'Description'
    ])

if 'raw_metrics_df' not in st.session_state:
    st.session_state.raw_metrics_df = pd.DataFrame()

if 'processed_files' not in st.session_state:
    st.session_state.processed_files = set()

if 'show_plotting' not in st.session_state:
    st.session_state.show_plotting = False

if 'num_plots' not in st.session_state:
    st.session_state.num_plots = 1

st.title("MJFF Analysis Data Visualization")

# --- The Advanced Insight Engine ---
def get_detailed_insights(df, metric, lens_type):
    """Reinforced AI Engine: Explicitly links secondary parameters to outliers."""
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    except KeyError:
        return "Error: GROQ_API_KEY not found in Streamlit Secrets."
    
    summary_report = []
    other_params = ['Barcode av.', 'Barcode std.', 'NrDrops']
    
    for name in df['Sample Name'].unique():
        sub = df[df['Sample Name'] == name]
        mean = sub[metric].mean()
        std = sub[metric].std()
        cv = (std / mean * 100) if mean != 0 else 0
        
        # 1-Sigma Outlier Detection
        outliers = sub[(sub[metric] > mean + 1*std) | (sub[metric] < mean - 1*std)]
        
        group_head = f"GROUP: {name}\n- Primary Metric ({metric}) Mean: {mean:.2f} (±{std:.2f})\n- Group CV: {cv:.1f}%"
        
        outlier_notes = []
        if not outliers.empty:
            for _, row in outliers.iterrows():
                note = f"  * OUTLIER DETECTED: Run {row['Run']} value is {row[metric]:.2f}."
                
                # Force-check secondary parameters for THIS specific outlier
                evidence = []
                for p in other_params:
                    p_mean = sub[p].mean()
                    p_std = sub[p].std()
                    # If the secondary param is also > 1 sigma away, it's 'evidence'
                    if p_std > 0 and abs(row[p] - p_mean) > 1 * p_std:
                        evidence.append(f"{p} is abnormal at {row[p]:.2f} (Group Avg: {p_mean:.2f})")
                
                if evidence:
                    note += "\n    EVIDENCE FROM SECONDARY PARAMS: " + " | ".join(evidence)
                else:
                    note += "\n    EVIDENCE: Secondary parameters (Barcode/Drops) were stable for this specific run."
                outlier_notes.append(note)
        else:
            outlier_notes.append("  * No outliers detected for this group.")
        
        summary_report.append(group_head + "\n" + "\n".join(outlier_notes))

    full_data_summary = "\n\n".join(summary_report)

    # --- REINFORCED PROMPTS ---
    prompts = {
        "General Analyst": "Summarize group performance and mention if outliers were explained by secondary data.",
        "Quality Control Specialist": "Critique the stability. Use the 'EVIDENCE' lines to determine if a run should be discarded.",
        "Root Cause Investigator": "You are a forensic scientist. For every outlier, you MUST explain the correlation with Barcode or Drops data provided in the 'EVIDENCE' section."
    }

    system_msg = f"You are an expert {lens_type}. " + prompts[lens_type]
    
    user_msg = f"""
    LAB DATA ANALYSIS REQUEST:
    PRIMARY METRIC: {metric}
    
    DETAILED DATA SUMMARY:
    {full_data_summary}
    
    STRICT COMPLIANCE RULES:
    1. You MUST acknowledge the Mean and SD for each group.
    2. For EVERY outlier listed, you MUST quote the 'EVIDENCE' section provided in the text.
    3. If the evidence says secondary parameters were 'stable', state that the cause is likely internal to the {metric} process itself.
    4. Never state 'data not provided'—all necessary evidence is included in the summary above.
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
            temperature=0.1
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"AI Error: {str(e)}"

# --- FILE UPLOADER ---
uploaded_file = st.file_uploader("Upload CSV", type="csv")

if uploaded_file:
    if uploaded_file.name not in st.session_state.processed_files:
        df = pd.read_csv(uploaded_file)
        if 'Sample' in df.columns:
            st.session_state.raw_metrics_df = pd.concat(
                [st.session_state.raw_metrics_df, df], ignore_index=True
            ).drop_duplicates(subset=['Sample'])
            
            new_ids = df['Sample'].unique()
            existing_ids = st.session_state.master_data['Sample ID'].tolist()
            new_rows = []

            for s_id in new_ids:
                if s_id not in existing_ids:
                    s_id_str = str(s_id)
                    
                    # 1. Look for 8 digits anywhere in the string
                    date_match = re.search(r'(\d{8})[-_]', s_id_str)
                    
                    if date_match:
                        ds = date_match.group(1)
                        rest = s_id_str.split(ds, 1)[1].lstrip('-_')
                    else:
                        ds = "Unknown"
                        rest = s_id_str
                    
                    # 2. Extract Run from the very end
                    sample_name = rest
                    run_val = 1
                    
                    if "_" in rest:
                        parts = rest.rsplit("_", 1)
                        if parts[1].isdigit():
                            sample_name = parts[0]
                            run_val = int(parts[1])
                    
                    new_rows.append({
                        'Include': True,
                        'Sample ID': s_id, 
                        'Datestamp': ds, 
                        'Sample Name': sample_name, 
                        'Run': str(run_val),  # Convert to string here
                        'Description': ""
                    })
            
            if new_rows:
                new_df = pd.DataFrame(new_rows)
                st.session_state.master_data = pd.concat([st.session_state.master_data, new_df], ignore_index=True)
            
            st.session_state.processed_files.add(uploaded_file.name)
            st.rerun()

if not st.session_state.master_data.empty:
    st.subheader("1. Sample ID List Table")

    with st.expander("🛠️ Bulk Rename & Selection Tools"):
        b_col1, b_col2, b_col3, b_col4 = st.columns(4)
        
        with b_col1:
            st.markdown("**Find & Replace**")
            find_text = st.text_input("Text to find", key="f_txt")
            replace_text = st.text_input("Replace with", key="r_txt")
            if st.button("Replace in Names"):
                st.session_state.master_data['Sample Name'] = st.session_state.master_data['Sample Name'].str.replace(find_text, replace_text)
                st.rerun()

        with b_col2:
            st.markdown("**Add Text**")
            prefix = st.text_input("Add Prefix", key="pre_txt")
            suffix = st.text_input("Add Suffix", key="suf_txt")
            if st.button("Apply Text"):
                if prefix:
                    st.session_state.master_data['Sample Name'] = prefix + st.session_state.master_data['Sample Name']
                if suffix:
                    st.session_state.master_data['Sample Name'] = st.session_state.master_data['Sample Name'] + suffix
                st.rerun()

        with b_col3:
            st.markdown("**Batch Run Update**")
            mode = st.radio("Run Logic", ["Set Constant", "Sequential (1,2,3...)"])
            val = st.number_input("Start/Constant Value", min_value=0, step=1)
            if st.button("Update Runs"):
                if mode == "Set Constant":
                    st.session_state.master_data['Run'] = val
                else:
                    st.session_state.master_data['Run'] = range(val, val + len(st.session_state.master_data))
                st.rerun()
        
        with b_col4:
            st.markdown("**Selection Control**")
            if st.button("✅ Select All"):
                st.session_state.master_data['Include'] = True
                st.rerun()
            if st.button("❌ Deselect All"):
                st.session_state.master_data['Include'] = False
                st.rerun()

    # --- THE DATA EDITOR ---
    edited_df = st.data_editor(
        st.session_state.master_data,
        key="editor_widget",
        column_config={
            "Include": st.column_config.CheckboxColumn("Plot?", default=True),
            "Sample ID": st.column_config.TextColumn("Original ID", disabled=True),
            "Datestamp": st.column_config.TextColumn("Date", disabled=True),
            "Sample Name": st.column_config.TextColumn("Sample Name"),
            "Run": st.column_config.TextColumn("Run"), # Changed from NumberColumn to TextColumn
            "Description": st.column_config.TextColumn("Description"),
        },
        hide_index=True,
        use_container_width=True,
    )

    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("Commit Changes"):
            st.session_state.master_data = edited_df
            st.success("Changes saved!")
    
    with col2:
        if st.button("Proceed to Plotting 📊"):
            st.session_state.master_data = edited_df 
            st.session_state.show_plotting = True

# --- PLOTTING PROTOCOL ---
if st.session_state.show_plotting:
    st.divider()
    st.subheader("2. Comparison Plotting")

    # Filter only samples marked as 'Include'
    filtered_master = st.session_state.master_data[st.session_state.master_data['Include'] == True]

    if filtered_master.empty:
        st.warning("No samples selected. Please check at least one sample in the table above.")
    else:
        # Prepare Base Data using only filtered samples
        plot_df = pd.merge(
            filtered_master, 
            st.session_state.raw_metrics_df, 
            left_on='Sample ID', 
            right_on='Sample'
        )
        
        core_metrics = ['PP-Gauss', 'PP-750', 'Barcode av.', 'Barcode std.', 'NrDrops']
        available_metrics = [m for m in core_metrics if m in plot_df.columns]

        view_mode = st.radio(
            "Select Visualization Mode:",
            ["Detailed (Show Every Run)", "Global (Mean & Std Dev)"],
            horizontal=True
        )

        for i in range(st.session_state.num_plots):
            st.markdown(f"### Plot Window {i+1}")
            c1, c2 = st.columns(2)
            
            with c1:
                selected_metric = st.selectbox(
                    f"Select Metric", 
                    available_metrics, 
                    key=f"metric_select_{i}",
                    index=i % len(available_metrics)
                )
            with c2:
                sort_order = st.selectbox(
                    "Sort Order",
                    ["Default (Name)", "Ascending (by Mean)", "Descending (by Mean)"],
                    key=f"sort_select_{i}"
                )

            if view_mode == "Detailed (Show Every Run)":
                temp_df = plot_df.copy()
                
                if sort_order != "Default (Name)":
                    group_means = temp_df.groupby('Sample Name')[selected_metric].mean()
                    ascending = True if "Ascending" in sort_order else False
                    sorted_names = group_means.sort_values(ascending=ascending).index
                    temp_df['Sample Name'] = pd.Categorical(temp_df['Sample Name'], categories=sorted_names, ordered=True)
                    temp_df = temp_df.sort_values(['Sample Name', 'Datestamp', 'Run'])
                else:
                    temp_df = temp_df.sort_values(by=['Sample Name', 'Datestamp', 'Run'])

                temp_df['Plot_X'] = (
                    "<span style='color:teal; font-weight:bold'>" + temp_df['Sample Name'].astype(str) + "</span><br>" + 
                    "<span style='color:gray'>" + temp_df['Datestamp'].astype(str) + "</span><br>" + 
                    "<span style='color:tomato'>Run: " + temp_df['Run'].astype(str) + "</span>" # .astype(str) ensures it works
                )
                
                y_val = temp_df[selected_metric]
                error_val = None
                custom_data = temp_df[['Description']]
                htemp = "<b>%{x}</b><br>Value: %{y}<br>Description: %{customdata[0]}<extra></extra>"
                display_df = temp_df

            else:
                agg_results = plot_df.groupby('Sample Name')[available_metrics].agg(['mean', 'std']).reset_index()
                agg_results.columns = [f"{col[0]}_{col[1]}" if col[1] else col[0] for col in agg_results.columns]
                
                if sort_order != "Default (Name)":
                    ascending = True if "Ascending" in sort_order else False
                    agg_results = agg_results.sort_values(by=f"{selected_metric}_mean", ascending=ascending)
                
                agg_results['Plot_X'] = "<span style='color:teal; font-weight:bold'>" + agg_results['Sample Name'] + "</span>"
                
                y_val = agg_results[f"{selected_metric}_mean"]
                error_val = agg_results[f"{selected_metric}_std"]
                custom_data = error_val
                htemp = "<b>%{x}</b><br>Mean: %{y:.2f}<br>Std Dev: %{customdata:.2f}<extra></extra>"
                display_df = agg_results

            unique_names = plot_df['Sample Name'].unique()
            color_palette = px.colors.qualitative.Plotly 
            name_to_color = {name: color_palette[idx % len(color_palette)] for idx, name in enumerate(unique_names)}
            display_df['BarColor'] = display_df['Sample Name'].map(name_to_color)

            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    x=display_df['Plot_X'], 
                    y=y_val, 
                    marker_color=display_df['BarColor'],
                    text=y_val.round(2),
                    textposition='auto',
                    error_y=dict(type='data', array=error_val, visible=True) if view_mode == "Global (Mean & Std Dev)" else None,
                    customdata=custom_data,
                    hovertemplate=htemp
                )
            )

            fig.update_layout(
                height=500, 
                yaxis_title=selected_metric, 
                template="plotly_white", 
                showlegend=False,
                yaxis=dict(range=[0, y_val.max() * 1.2] if not y_val.empty else None)
            )
            fig.update_xaxes(tickangle=0)
            st.plotly_chart(fig, use_container_width=True, key=f"chart_{i}")

        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            if st.button("➕ Add Plot"):
                st.session_state.num_plots += 1
                st.rerun()
        with col_btn2:
            if st.session_state.num_plots > 1:
                if st.button("Reset Plots"):
                    st.session_state.num_plots = 1
                    st.rerun()

        st.write("---")
        st.subheader("3. Plotted Data Reference Table")
        table_df = plot_df.copy()
        table_df['SAMPLE ID'] = table_df['Datestamp'] + "_" + table_df['Sample Name'] + "_" + table_df['Run'].astype(str)
        
        st.dataframe(
            table_df[['Datestamp', 'Sample Name', 'Run', 'SAMPLE ID'] + available_metrics],
            column_config={
                "Datestamp": st.column_config.TextColumn("Date", width=100),
                "Run": st.column_config.TextColumn("Run"), # Update this to TextColumn
                "SAMPLE ID": st.column_config.TextColumn("Combined ID", width=300),
                **{m: st.column_config.NumberColumn(m, width=120, format="%.2f") for m in available_metrics}
            },
            hide_index=True,
            use_container_width=True
        )

    st.divider()
    st.write("---")
    st.subheader("🤖 Automated Data Insights")
    
    # 1. Configuration
    with st.expander("⚙️ AI Analysis Settings", expanded=True):
        i_col1, i_col2 = st.columns([2, 1])
        with i_col1:
            lens = st.selectbox(
                "Select Expert Lens",
                ["General Analyst", "Quality Control Specialist", "Root Cause Investigator"]
            )
        with i_col2:
            st.write(" ") # Padding for alignment
            generate_btn = st.button("Generate Insights 🪄", use_container_width=True)

    # 2. Execution
    if generate_btn:
        if not plot_df.empty:
            with st.spinner(f"Running {lens} Analysis..."):
                final_report = get_detailed_insights(plot_df, selected_metric, lens)
                st.markdown(f"### {lens} Report")
                st.info(final_report)
        else:
            st.warning("Please include at least one sample to analyze.")

# --- RESET FUNCTIONALITY ---
def reset_app():
    keys_to_reset = ['master_data', 'raw_metrics_df', 'processed_files', 'show_plotting', 'num_plots', 'editor_widget']
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

with st.sidebar:
    st.header("App Controls")
    if st.button("🔄 Restart & Clear All Data", type="primary"):
        reset_app()