
# import streamlit as st
# import pandas as pd
# import plotly.graph_objects as go
# from plotly.subplots import make_subplots
# import plotly.express as px
# import re
# from groq import Groq

# # --- INITIALIZATION ---
# if 'master_data' not in st.session_state:
#     st.session_state.master_data = pd.DataFrame(columns=[
#         'Include', 'Sample ID', 'Datestamp', 'Sample Name', 'Run', 'Description'
#     ])

# if 'raw_metrics_df' not in st.session_state:
#     st.session_state.raw_metrics_df = pd.DataFrame()

# if 'processed_files' not in st.session_state:
#     st.session_state.processed_files = set()

# if 'show_plotting' not in st.session_state:
#     st.session_state.show_plotting = False

# if 'num_plots' not in st.session_state:
#     st.session_state.num_plots = 1

# st.set_page_config(page_title="MJFF Sample Manager", layout="wide")

# # --- CUSTOM CSS FOR "WING" HINT ---
# st.markdown("""
#     <style>
#     @keyframes nudge {
#       0% { transform: translateX(0); }
#       50% { transform: translateX(8px); }
#       100% { transform: translateX(0); }
#     }
#     .insight-hint {
#         background-color: #e8f4f8;
#         border-left: 5px solid #007bff;
#         padding: 12px;
#         border-radius: 8px;
#         font-size: 0.95rem;
#         margin-bottom: 15px;
#         animation: nudge 2s infinite ease-in-out;
#         display: flex;
#         align-items: center;
#         gap: 10px;
#     }
#     </style>
# """, unsafe_allow_html=True)

# st.title("MJFF Analysis Data Visualization")

# # --- NEW: APP FUNCTIONALITY GUIDE ---
# with st.expander("📖 How to use this App (Feature Guide)", expanded=True):
#     st.markdown("""
#     ### 🚀 Getting Started
#     1. **Upload Data**: Use the CSV uploader below. The app automatically parses Sample IDs into Names, Dates, and Run numbers.
    
#     ### 🛠️ Key Functionalities
#     * **Bulk Management**: Use the tools in **Section 1** to batch-rename samples, add prefixes/suffixes, or re-index run numbers.
#     * **Selection Control**: Check/Uncheck the **'Plot?'** column in the table to choose exactly which data points appear on your charts.
#     * **Visualization Modes**: 
#         * *Detailed*: Shows every individual run for forensic comparison.
#         * *Global*: Groups by Sample Name and shows Mean + Standard Deviation.
#     * **Smart Sorting**: Sort your plots alphabetically or by the value of the primary metric (Ascending/Descending).
#     * **🤖 AI Agent Tool**: Located in **Section 3**. Select an "Expert Lens" or type a **Human Language Query** (e.g., *"Why is Run 2 different?"*) to get automated root-cause analysis.
#     * **Data Table**: A clean, tabulated view of all plotted data is available at the bottom for easy reference or copying.

#     ### 🔄 How to Restart
#     * To clear all data and start fresh, click the **"Restart & Clear All Data"** button in the sidebar or simply **Refresh your Browser (F5)**.
#     """)

# # --- AI INSIGHT ENGINE ---
# def get_detailed_insights(df, metric, lens_type, custom_query=None):
#     try:
#         client = Groq(api_key=st.secrets["GROQ_API_KEY"])
#     except KeyError:
#         return "Error: GROQ_API_KEY not found in Streamlit Secrets."
    
#     summary_report = []
#     other_params = ['Barcode av.', 'Barcode std.', 'NrDrops']
    
#     for name in df['Sample Name'].unique():
#         sub = df[df['Sample Name'] == name]
#         mean = sub[metric].mean()
#         std = sub[metric].std()
#         cv = (std / mean * 100) if mean != 0 else 0
        
#         outliers = sub[(sub[metric] > mean + 1*std) | (sub[metric] < mean - 1*std)]
#         group_head = f"GROUP: {name}\n- Primary Metric ({metric}) Mean: {mean:.2f} (±{std:.2f})\n- Group CV: {cv:.1f}%"
        
#         outlier_notes = []
#         if not outliers.empty:
#             for _, row in outliers.iterrows():
#                 note = f"  * OUTLIER DETECTED: Run {row['Run']} value is {row[metric]:.2f}."
#                 evidence = []
#                 for p in other_params:
#                     p_mean = sub[p].mean()
#                     p_std = sub[p].std()
#                     if p_std > 0 and abs(row[p] - p_mean) > 1 * p_std:
#                         evidence.append(f"{p} is abnormal at {row[p]:.2f} (Group Avg: {p_mean:.2f})")
#                 note += "\n    EVIDENCE: " + (" | ".join(evidence) if evidence else "Secondary parameters were stable.")
#                 outlier_notes.append(note)
#         else:
#             outlier_notes.append("  * No outliers detected.")
#         summary_report.append(group_head + "\n" + "\n".join(outlier_notes))

#     full_data_summary = "\n\n".join(summary_report)
#     prompts = {
#         "General Analyst": "Summarize performance and outliers.",
#         "Quality Control Specialist": "Critique stability; suggest if runs should be discarded.",
#         "Root Cause Investigator": "Forensic focus. Correlate outliers with Barcode/Drops data."
#     }

#     system_msg = f"You are an expert {lens_type}. " + prompts[lens_type]
#     user_msg = f"LAB DATA ANALYSIS REQUEST:\nPRIMARY METRIC: {metric}\n\nDATA SUMMARY:\n{full_data_summary}"
    
#     if custom_query:
#         user_msg += f"\n\nUSER QUESTION: {custom_query}\n\nPlease prioritize answering the user's question using the data provided."

#     try:
#         completion = client.chat.completions.create(
#             model="llama-3.3-70b-versatile",
#             messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
#             temperature=0.1
#         )
#         return completion.choices[0].message.content
#     except Exception as e:
#         return f"AI Error: {str(e)}"

# # --- FILE UPLOADER ---
# uploaded_file = st.file_uploader("Upload CSV", type="csv")

# if uploaded_file:
#     if uploaded_file.name not in st.session_state.processed_files:
#         df = pd.read_csv(uploaded_file)
#         if 'Sample' in df.columns:
#             st.session_state.raw_metrics_df = pd.concat(
#                 [st.session_state.raw_metrics_df, df], ignore_index=True
#             ).drop_duplicates(subset=['Sample'])
            
#             new_rows = []
#             for s_id in df['Sample'].unique():
#                 if s_id not in st.session_state.master_data['Sample ID'].tolist():
#                     s_id_str = str(s_id)
#                     date_match = re.search(r'(\d{8})[-_]', s_id_str)
#                     ds = date_match.group(1) if date_match else "Unknown"
#                     rest = s_id_str.split(ds, 1)[1].lstrip('-_') if date_match else s_id_str
#                     sample_name, run_val = rest, "1"
#                     if "_" in rest:
#                         parts = rest.rsplit("_", 1)
#                         if parts[1].isdigit():
#                             sample_name, run_val = parts[0], parts[1]
#                     new_rows.append({'Include': True, 'Sample ID': s_id, 'Datestamp': ds, 'Sample Name': sample_name, 'Run': run_val, 'Description': ""})
            
#             if new_rows:
#                 st.session_state.master_data = pd.concat([st.session_state.master_data, pd.DataFrame(new_rows)], ignore_index=True)
#             st.session_state.processed_files.add(uploaded_file.name)
#             st.rerun()

# if not st.session_state.master_data.empty:
#     st.subheader("1. Sample ID List Table")

#     # --- RESTORED BULK TOOLS ---
#     with st.expander("🛠️ Bulk Rename & Selection Tools"):
#         b_col1, b_col2, b_col3, b_col4 = st.columns(4)
#         with b_col1:
#             st.markdown("**Find & Replace**")
#             f_txt = st.text_input("Text to find")
#             r_txt = st.text_input("Replace with")
#             if st.button("Replace in Names"):
#                 st.session_state.master_data['Sample Name'] = st.session_state.master_data['Sample Name'].str.replace(f_txt, r_txt)
#                 st.rerun()
#         with b_col2:
#             st.markdown("**Add Text**")
#             pre_txt = st.text_input("Add Prefix")
#             suf_txt = st.text_input("Add Suffix")
#             if st.button("Apply Text"):
#                 if pre_txt: st.session_state.master_data['Sample Name'] = pre_txt + st.session_state.master_data['Sample Name']
#                 if suf_txt: st.session_state.master_data['Sample Name'] = st.session_state.master_data['Sample Name'] + suf_txt
#                 st.rerun()
#         with b_col3:
#             st.markdown("**Batch Run Update**")
#             mode = st.radio("Run Logic", ["Set Constant", "Sequential"])
#             val = st.number_input("Start/Constant", min_value=0, step=1)
#             if st.button("Update Runs"):
#                 if mode == "Set Constant":
#                     st.session_state.master_data['Run'] = str(val)
#                 else:
#                     st.session_state.master_data['Run'] = [str(i) for i in range(val, val + len(st.session_state.master_data))]
#                 st.rerun()
#         with b_col4:
#             st.markdown("**Selection Control**")
#             if st.button("✅ Select All"):
#                 st.session_state.master_data['Include'] = True
#                 st.rerun()
#             if st.button("❌ Deselect All"):
#                 st.session_state.master_data['Include'] = False
#                 st.rerun()

#     edited_df = st.data_editor(
#         st.session_state.master_data,
#         key="editor_widget",
#         column_config={
#             "Include": st.column_config.CheckboxColumn("Plot?", default=True),
#             "Sample ID": st.column_config.TextColumn("Original ID", disabled=True),
#             "Datestamp": st.column_config.TextColumn("Date", disabled=True),
#             "Run": st.column_config.TextColumn("Run"),
#         },
#         hide_index=True,
#         use_container_width=True,
#     )

#     col1, col2 = st.columns([1, 5])
#     with col1:
#         if st.button("Commit Changes"):
#             st.session_state.master_data = edited_df
#             st.success("Changes saved!")
    
#     with col2:
#         if st.button("Proceed to Plotting 📊"):
#             st.session_state.master_data = edited_df 
#             st.session_state.show_plotting = True

# # --- PLOTTING & INSIGHTS ---
# if st.session_state.show_plotting:
#     st.divider()
    
#     # THE WING HINT
#     st.markdown('<div class="insight-hint"><span>🤖</span><b>Automated Insights Available:</b> Scroll to Section 3 for AI root-cause analysis and custom queries.</div>', unsafe_allow_html=True)
    
#     st.subheader("2. Comparison Plotting")
#    #Filter only samples marked as 'Include'
#     filtered_master = st.session_state.master_data[st.session_state.master_data['Include'] == True]

#     if filtered_master.empty:
#         st.warning("No samples selected. Please check at least one sample in the table above.")
#     else:
#         # Prepare Base Data using only filtered samples
#         plot_df = pd.merge(
#             filtered_master, 
#             st.session_state.raw_metrics_df, 
#             left_on='Sample ID', 
#             right_on='Sample'
#         )
        
#         core_metrics = ['PP-Gauss', 'PP-750', 'Barcode av.', 'Barcode std.', 'NrDrops']
#         available_metrics = [m for m in core_metrics if m in plot_df.columns]

#         view_mode = st.radio(
#             "Select Visualization Mode:",
#             ["Detailed (Show Every Run)", "Global (Mean & Std Dev)"],
#             horizontal=True
#         )

#         for i in range(st.session_state.num_plots):
#             st.markdown(f"### Plot Window {i+1}")
#             c1, c2 = st.columns(2)
            
#             with c1:
#                 selected_metric = st.selectbox(
#                     f"Select Metric", 
#                     available_metrics, 
#                     key=f"metric_select_{i}",
#                     index=i % len(available_metrics)
#                 )
#             with c2:
#                 sort_order = st.selectbox(
#                     "Sort Order",
#                     ["Default (Name)", "Ascending (by Mean)", "Descending (by Mean)"],
#                     key=f"sort_select_{i}"
#                 )

#             if view_mode == "Detailed (Show Every Run)":
#                 temp_df = plot_df.copy()
                
#                 if sort_order != "Default (Name)":
#                     group_means = temp_df.groupby('Sample Name')[selected_metric].mean()
#                     ascending = True if "Ascending" in sort_order else False
#                     sorted_names = group_means.sort_values(ascending=ascending).index
#                     temp_df['Sample Name'] = pd.Categorical(temp_df['Sample Name'], categories=sorted_names, ordered=True)
#                     temp_df = temp_df.sort_values(['Sample Name', 'Datestamp', 'Run'])
#                 else:
#                     temp_df = temp_df.sort_values(by=['Sample Name', 'Datestamp', 'Run'])

#                 temp_df['Plot_X'] = (
#                     "<span style='color:teal; font-weight:bold'>" + temp_df['Sample Name'].astype(str) + "</span><br>" + 
#                     "<span style='color:gray'>" + temp_df['Datestamp'].astype(str) + "</span><br>" + 
#                     "<span style='color:tomato'>Run: " + temp_df['Run'].astype(str) + "</span>" # .astype(str) ensures it works
#                 )
                
#                 y_val = temp_df[selected_metric]
#                 error_val = None
#                 custom_data = temp_df[['Description']]
#                 htemp = "<b>%{x}</b><br>Value: %{y}<br>Description: %{customdata[0]}<extra></extra>"
#                 display_df = temp_df

#             else:
#                 agg_results = plot_df.groupby('Sample Name')[available_metrics].agg(['mean', 'std']).reset_index()
#                 agg_results.columns = [f"{col[0]}_{col[1]}" if col[1] else col[0] for col in agg_results.columns]
                
#                 if sort_order != "Default (Name)":
#                     ascending = True if "Ascending" in sort_order else False
#                     agg_results = agg_results.sort_values(by=f"{selected_metric}_mean", ascending=ascending)
                
#                 agg_results['Plot_X'] = "<span style='color:teal; font-weight:bold'>" + agg_results['Sample Name'] + "</span>"
                
#                 y_val = agg_results[f"{selected_metric}_mean"]
#                 error_val = agg_results[f"{selected_metric}_std"]
#                 custom_data = error_val
#                 htemp = "<b>%{x}</b><br>Mean: %{y:.2f}<br>Std Dev: %{customdata:.2f}<extra></extra>"
#                 display_df = agg_results

#             unique_names = plot_df['Sample Name'].unique()
#             color_palette = px.colors.qualitative.Plotly 
#             name_to_color = {name: color_palette[idx % len(color_palette)] for idx, name in enumerate(unique_names)}
#             display_df['BarColor'] = display_df['Sample Name'].map(name_to_color)

#             fig = go.Figure()
#             fig.add_trace(
#                 go.Bar(
#                     x=display_df['Plot_X'], 
#                     y=y_val, 
#                     marker_color=display_df['BarColor'],
#                     text=y_val.round(2),
#                     textposition='auto',
#                     error_y=dict(type='data', array=error_val, visible=True) if view_mode == "Global (Mean & Std Dev)" else None,
#                     customdata=custom_data,
#                     hovertemplate=htemp
#                 )
#             )

#             fig.update_layout(
#                 height=500, 
#                 yaxis_title=selected_metric, 
#                 template="plotly_white", 
#                 showlegend=False,
#                 yaxis=dict(range=[0, y_val.max() * 1.2] if not y_val.empty else None)
#             )
#             fig.update_xaxes(tickangle=0)
#             st.plotly_chart(fig, use_container_width=True, key=f"chart_{i}")

#         col_btn1, col_btn2 = st.columns([1, 4])
#         with col_btn1:
#             if st.button("➕ Add Plot"):
#                 st.session_state.num_plots += 1
#                 st.rerun()
#         with col_btn2:
#             if st.session_state.num_plots > 1:
#                 if st.button("Reset Plots"):
#                     st.session_state.num_plots = 1
#                     st.rerun()

#         st.write("---")
#         st.subheader("3. Plotted Data Reference Table")
#         table_df = plot_df.copy()
#         table_df['SAMPLE ID'] = table_df['Datestamp'] + "_" + table_df['Sample Name'] + "_" + table_df['Run'].astype(str)
        
#         st.dataframe(
#             table_df[['Datestamp', 'Sample Name', 'Run', 'SAMPLE ID'] + available_metrics],
#             column_config={
#                 "Datestamp": st.column_config.TextColumn("Date", width=100),
#                 "Run": st.column_config.TextColumn("Run"), # Update this to TextColumn
#                 "SAMPLE ID": st.column_config.TextColumn("Combined ID", width=300),
#                 **{m: st.column_config.NumberColumn(m, width=120, format="%.2f") for m in available_metrics}
#             },
#             hide_index=True,
#             use_container_width=True
#         )

#     st.divider()
#     st.subheader("3. 🤖 Automated Data Insights")
    
#     with st.expander("⚙️ AI Analysis & Custom Questions", expanded=True):
#         i_col1, i_col2 = st.columns([2, 1])
#         with i_col1:
#             lens = st.selectbox("Select Expert Lens", ["General Analyst", "Quality Control Specialist", "Root Cause Investigator"])
#             custom_q = st.text_area("💬 Human Language Query", placeholder="e.g., 'Is there a correlation between NrDrops and the outliers in Sample B?'")
#         with i_col2:
#             st.write(" ")
#             generate_btn = st.button("Generate Insights 🪄", use_container_width=True)

#     if generate_btn:
#         # (Assuming 'plot_df' and 'selected_metric' are defined in the plotting block)
#         with st.spinner("Analyzing..."):
#             final_report = get_detailed_insights(plot_df, selected_metric, lens, custom_q)
#             st.info(final_report)


import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import re
from groq import Groq

# --- INITIALIZATION ---
if 'master_data' not in st.session_state:
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

st.set_page_config(page_title="MJFF Sample Manager", layout="wide")

# --- CUSTOM CSS FOR "WING" HINT ---
st.markdown("""
    <style>
    @keyframes nudge {
      0% { transform: translateX(0); }
      50% { transform: translateX(5px); }
      100% { transform: translateX(0); }
    }
    .insight-hint {
        background-color: #e8f4f8;
        border-left: 5px solid #007bff;
        padding: 12px;
        border-radius: 8px;
        font-size: 0.95rem;
        margin-bottom: 15px;
        animation: nudge 3s ease-in-out 3;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("MJFF Analysis Data Visualization")

# --- APP FUNCTIONALITY GUIDE ---
with st.expander("📖 How to use this App (Feature Guide)", expanded=True):
    st.markdown("""
    ### 🚀 Getting Started
    1. **Upload Data**: Use the CSV uploader below. The app parses Sample IDs between boundaries (`_xcxcx-`, `-xzxzx-`, `_cxcx_`) and isolates pure text.
    2. **Auto Run Counts**: Run sequences ($1, 2, 3, \dots$) are automatically computed based on sample name occurrence order during import.
    
    ### 🛠️ Key Functionalities
    * **Bulk Management**: Use **Section 1** tools to batch-rename samples, append structural elements, or re-index counts on demand.
    * **Target Dropdown Filter**: In **Section 2**, cleanly isolate individual groups from your dropdown menu to instantly re-render active viewports.
    * **🤖 AI Agent Tool**: Located in **Section 4** for automated root-cause evaluation.
    """)

# --- AI INSIGHT ENGINE ---
def get_detailed_insights(df, metric, lens_type, custom_query=None):
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    except KeyError:
        return "Error: GROQ_API_KEY not found in Streamlit Secrets."
    
    summary_report = []
    other_params = ['Barcode av.', 'Barcode std.', 'NrDrops']
    other_params = [p for p in other_params if p in df.columns]
    
    for name in df['Sample Name'].unique():
        sub = df[df['Sample Name'] == name]
        mean = sub[metric].mean()
        std = sub[metric].std()
        cv = (std / mean * 100) if mean != 0 else 0
        
        outliers = sub[(sub[metric] > mean + 1*std) | (sub[metric] < mean - 1*std)]
        group_head = f"GROUP: {name}\n- Primary Metric ({metric}) Mean: {mean:.2f} (±{std:.2f})\n- Group CV: {cv:.1f}%"
        
        outlier_notes = []
        if not outliers.empty:
            for _, row in outliers.iterrows():
                note = f"  * OUTLIER DETECTED: Run {row['Run']} value is {row[metric]:.2f}."
                evidence = []
                for p in other_params:
                    p_mean = sub[p].mean()
                    p_std = sub[p].std()
                    if p_std > 0 and abs(row[p] - p_mean) > 1 * p_std:
                        evidence.append(f"{p} is abnormal at {row[p]:.2f} (Group Avg: {p_mean:.2f})")
                note += "\n    EVIDENCE: " + (" | ".join(evidence) if evidence else "Secondary parameters were stable.")
                outlier_notes.append(note)
        else:
            outlier_notes.append("  * No outliers detected.")
        summary_report.append(group_head + "\n" + "\n".join(outlier_notes))

    full_data_summary = "\n\n".join(summary_report)
    prompts = {
        "General Analyst": "Summarize performance and outliers.",
        "Quality Control Specialist": "Critique stability; suggest if runs should be discarded.",
        "Root Cause Investigator": "Forensic focus. Correlate outliers with Barcode/Drops data."
    }

    system_msg = f"You are an expert {lens_type}. " + prompts[lens_type]
    user_msg = f"LAB DATA ANALYSIS REQUEST:\nPRIMARY METRIC: {metric}\n\nDATA SUMMARY:\n{full_data_summary}"
    
    if custom_query:
        user_msg += f"\n\nUSER QUESTION: {custom_query}\n\nPlease prioritize answering the user's question using the data provided."

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
            temperature=0.1
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"AI Error: {str(e)}"

# --- FILE UPLOADER WITH AUTOMATED SEQUENCE GENERATION ---
uploaded_file = st.file_uploader("Upload CSV", type="csv")

if uploaded_file:
    if uploaded_file.name not in st.session_state.processed_files:
        df = pd.read_csv(uploaded_file)
        if 'Sample' in df.columns:
            st.session_state.raw_metrics_df = pd.concat(
                [st.session_state.raw_metrics_df, df], ignore_index=True
            ).drop_duplicates(subset=['Sample'])
            
            # Temporary holder dataframe to compute cumulative occurrences accurately for this patch
            parsing_list = []
            
            for s_id in df['Sample'].unique():
                if s_id not in st.session_state.master_data['Sample ID'].tolist():
                    s_id_str = str(s_id)
                    
                    # 1. Parse standard Datestamp
                    date_match = re.search(r'(\d{8})[-_]', s_id_str)
                    ds = date_match.group(1) if date_match else "Unknown"
                    
                    # 2. Extract name strictly between tokens: _xcxcx- or -xzxzx- or _cxcx_ keeping only alpha characters
                    boundary_match = re.search(r'(?:[-_][a-zA-Z]+[-_])([a-zA-Z]+)', s_id_str)
                    
                    if boundary_match:
                        sample_name = boundary_match.group(1)
                    else:
                        # Fallback parsing strategy
                        rest = s_id_str.split(ds, 1)[1].lstrip('-_') if date_match else s_id_str
                        sample_name = re.sub(r'[^a-zA-Z]', '', rest.split('_')[0])
                    
                    parsing_list.append({
                        'Include': True, 
                        'Sample ID': s_id, 
                        'Datestamp': ds, 
                        'Sample Name': sample_name, 
                        'Description': ""
                    })
            
            if parsing_list:
                new_batch_df = pd.DataFrame(parsing_list)
                
                # Combine with existing master data temporary baseline to calculate true sequential occurrence matrix
                combined_temp = pd.concat([st.session_state.master_data, new_batch_df], ignore_index=True)
                
                # Dynamic run counter calculated directly off running value group size occurrences (1, 2, 3...)
                combined_temp['Run'] = (combined_temp.groupby('Sample Name').cumcount() + 1).astype(str)
                
                # Re-assign structural update back to session state
                st.session_state.master_data = combined_temp
                
            st.session_state.processed_files.add(uploaded_file.name)
            st.rerun()

if not st.session_state.master_data.empty:
    st.subheader("1. Sample ID List Table")

    # --- BULK TOOLS SECTION ---
    with st.expander("🛠️ Bulk Rename & Selection Tools"):
        b_col1, b_col2, b_col3, b_col4 = st.columns(4)
        with b_col1:
            st.markdown("**Find & Replace**")
            f_txt = st.text_input("Text to find", key="bulk_find")
            r_txt = st.text_input("Replace with", key="bulk_replace")
            if st.button("Replace in Names", key="btn_replace"):
                st.session_state.master_data['Sample Name'] = st.session_state.master_data['Sample Name'].str.replace(f_txt, r_txt)
                # Recalculate run sequences dynamically since name criteria fields shifted
                st.session_state.master_data['Run'] = (st.session_state.master_data.groupby('Sample Name').cumcount() + 1).astype(str)
                st.rerun()
        with b_col2:
            st.markdown("**Add Text**")
            pre_txt = st.text_input("Add Prefix", key="bulk_prefix")
            suf_txt = st.text_input("Add Suffix", key="bulk_suffix")
            if st.button("Apply Text", key="btn_apply_text"):
                if pre_txt: st.session_state.master_data['Sample Name'] = pre_txt + st.session_state.master_data['Sample Name']
                if suf_txt: st.session_state.master_data['Sample Name'] = st.session_state.master_data['Sample Name'] + suf_txt
                st.session_state.master_data['Run'] = (st.session_state.master_data.groupby('Sample Name').cumcount() + 1).astype(str)
                st.rerun()
        with b_col3:
            st.markdown("**Batch Run Update**")
            mode = st.radio("Run Logic", ["Set Constant", "Recalculate Occurrences (1,2,3...)"], key="bulk_run_mode")
            val = st.number_input("Start Value Offset", min_value=0, step=1, value=1, key="bulk_run_val")
            if st.button("Update Runs", key="btn_update_runs"):
                if mode == "Set Constant":
                    st.session_state.master_data['Run'] = str(val)
                else:
                    st.session_state.master_data['Run'] = (
                        st.session_state.master_data.groupby('Sample Name').cumcount() + val
                    ).astype(str)
                st.rerun()
        with b_col4:
            st.markdown("**Selection Control**")
            if st.button("✅ Select All", key="btn_select_all"):
                st.session_state.master_data['Include'] = True
                st.rerun()
            if st.button("❌ Deselect All", key="btn_deselect_all"):
                st.session_state.master_data['Include'] = False
                st.rerun()

    edited_df = st.data_editor(
        st.session_state.master_data,
        key="editor_widget",
        column_config={
            "Include": st.column_config.CheckboxColumn("Plot?", default=True),
            "Sample ID": st.column_config.TextColumn("Original ID", disabled=True),
            "Datestamp": st.column_config.TextColumn("Date", disabled=True),
            "Run": st.column_config.TextColumn("Run Custom Override"),
        },
        hide_index=True,
        use_container_width=True,
    )

    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("Commit Changes", key="btn_commit"):
            st.session_state.master_data = edited_df
            st.success("Changes saved!")
    
    with col2:
        if st.button("Proceed to Plotting 📊", key="btn_proceed"):
            st.session_state.master_data = edited_df 
            st.session_state.show_plotting = True

# --- PLOTTING & INSIGHTS ---
if st.session_state.show_plotting:
    st.divider()
    st.markdown('<div class="insight-hint"><span>🤖</span><b>Automated Insights Available:</b> Scroll to Section 4 for AI root-cause analysis and custom queries.</div>', unsafe_allow_html=True)
    
    st.subheader("2. Comparison Plotting")
    base_filtered = st.session_state.master_data[st.session_state.master_data['Include'] == True]

    if base_filtered.empty:
        st.warning("No samples marked for selection. Please check the 'Plot?' boxes in the table above.")
    else:
        available_sample_names = sorted(base_filtered['Sample Name'].unique())
        selected_samples = st.multiselect(
            "🔎 Select Sample Names to Plot from Dropdown:",
            options=available_sample_names,
            default=available_sample_names,
            key="sample_dropdown_filter"
        )
        
        final_filtered_master = base_filtered[base_filtered['Sample Name'].isin(selected_samples)]

        if final_filtered_master.empty:
            st.info("Please select at least one sample name from the dropdown menu to render plots.")
        else:
            plot_df = pd.merge(
                final_filtered_master, 
                st.session_state.raw_metrics_df, 
                left_on='Sample ID', 
                right_on='Sample'
            )
            
            core_metrics = ['PP-Gauss', 'PP-750', 'Barcode av.', 'Barcode std.', 'NrDrops']
            available_metrics = [m for m in core_metrics if m in plot_df.columns]

            view_mode = st.radio(
                "Select Visualization Mode:",
                ["Detailed (Show Every Run)", "Global (Mean & Std Dev)"],
                horizontal=True,
                key="view_mode_selector"
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
                        "<span style='color:tomato'>Run: " + temp_df['Run'].astype(str) + "</span>"
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
                if st.button("➕ Add Plot", key="btn_add_plot"):
                    st.session_state.num_plots += 1
                    st.rerun()
            with col_btn2:
                if st.session_state.num_plots > 1:
                    if st.button("Reset Plots", key="btn_reset_plots"):
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
                    "Run": st.column_config.TextColumn("Run"), 
                    "SAMPLE ID": st.column_config.TextColumn("Combined ID", width=300),
                    **{m: st.column_config.NumberColumn(m, width=120, format="%.2f") for m in available_metrics}
                },
                hide_index=True,
                use_container_width=True
            )

        st.divider()
        st.subheader("4. 🤖 Automated Data Insights")
        
        with st.expander("⚙️ AI Analysis & Custom Questions", expanded=True):
            i_col1, i_col2, i_col3 = st.columns([1, 1, 1])
            with i_col1:
                ai_metric = st.selectbox("Target Analysis Metric", available_metrics, key="ai_target_metric")
                lens = st.selectbox("Select Expert Lens", ["General Analyst", "Quality Control Specialist", "Root Cause Investigator"], key="ai_lens")
            with i_col2:
                custom_q = st.text_area("💬 Human Language Query", placeholder="e.g., 'Is there a correlation between NrDrops and the outliers in Sample B?'", key="ai_query")
            with i_col3:
                st.write(" ")
                st.write(" ")
                generate_btn = st.button("Generate Insights 🪄", use_container_width=True, key="btn_generate_insights")

        if generate_btn:
            with st.spinner("Analyzing..."):
                final_report = get_detailed_insights(plot_df, ai_metric, lens, custom_q)
                st.info(final_report)