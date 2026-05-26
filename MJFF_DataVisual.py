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
#       50% { transform: translateX(5px); }
#       100% { transform: translateX(0); }
#     }
#     .insight-hint {
#         background-color: #e8f4f8;
#         border-left: 5px solid #007bff;
#         padding: 12px;
#         border-radius: 8px;
#         font-size: 0.95rem;
#         margin-bottom: 15px;
#         animation: nudge 3s ease-in-out 3;
#         display: flex;
#         align-items: center;
#         gap: 10px;
#     }
#     </style>
# """, unsafe_allow_html=True)

# st.title("MJFF Analysis Data Visualization")

# # --- APP FUNCTIONALITY GUIDE ---
# with st.expander("📖 How to use this App (Feature Guide)", expanded=True):
#     st.markdown("""
#     ### 🚀 Getting Started
#     1. **Upload Data**: Use the CSV uploader below. The app parses Sample IDs between boundaries (`_xcxcx-`, `-xzxzx-`, `_cxcx_`) and isolates pure text.
#     2. **Auto Run Counts**: Run sequences ($1, 2, 3, \dots$) are automatically computed based on sample name occurrence order during import.
    
#     ### 🛠️ Key Functionalities
#     * **Bulk Management**: Use **Section 1** tools to batch-rename samples, append structural elements, or re-index counts on demand.
#     * **Target Dropdown Filter**: In **Section 2**, cleanly isolate individual groups from your dropdown menu to instantly re-render active viewports.
#     * **📊 Cross-Metric Outlier Filtering**: Filter out anomalies using one parameter (e.g., *Barcode std.*) and view the surviving records plotted in your core parameter (e.g., *PP-Gauss*).
#     * **📈 Cohort Summaries**: Section 3 displays grouped analysis criteria specifically tracking variance indices of PP-Gauss data.
#     """)

# # --- AI INSIGHT ENGINE ---
# def get_detailed_insights(df, metric, lens_type, custom_query=None):
#     try:
#         client = Groq(api_key=st.secrets["GROQ_API_KEY"])
#     except KeyError:
#         return "Error: GROQ_API_KEY not found in Streamlit Secrets."
    
#     summary_report = []
#     other_params = ['Barcode av.', 'Barcode std.', 'NrDrops']
#     other_params = [p for p in other_params if p in df.columns]
    
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

# # --- FILE UPLOADER WITH AUTOMATED SEQUENCE GENERATION ---
# uploaded_file = st.file_uploader("Upload CSV", type="csv")

# if uploaded_file:
#     if uploaded_file.name not in st.session_state.processed_files:
#         df = pd.read_csv(uploaded_file)
#         if 'Sample' in df.columns:
#             st.session_state.raw_metrics_df = pd.concat(
#                 [st.session_state.raw_metrics_df, df], ignore_index=True
#             ).drop_duplicates(subset=['Sample'])
            
#             parsing_list = []
#             for s_id in df['Sample'].unique():
#                 if s_id not in st.session_state.master_data['Sample ID'].tolist():
#                     s_id_str = str(s_id)
                    
#                     date_match = re.search(r'(\d{8})[-_]', s_id_str)
#                     ds = date_match.group(1) if date_match else "Unknown"
                    
#                     boundary_match = re.search(r'(?:[-_][a-zA-Z]+[-_])([a-zA-Z]+)', s_id_str)
                    
#                     if boundary_match:
#                         sample_name = boundary_match.group(1)
#                     else:
#                         rest = s_id_str.split(ds, 1)[1].lstrip('-_') if date_match else s_id_str
#                         sample_name = re.sub(r'[^a-zA-Z]', '', rest.split('_')[0])
                    
#                     parsing_list.append({
#                         'Include': True, 
#                         'Sample ID': s_id, 
#                         'Datestamp': ds, 
#                         'Sample Name': sample_name, 
#                         'Description': ""
#                     })
            
#             if parsing_list:
#                 new_batch_df = pd.DataFrame(parsing_list)
#                 combined_temp = pd.concat([st.session_state.master_data, new_batch_df], ignore_index=True)
#                 combined_temp['Run'] = (combined_temp.groupby('Sample Name').cumcount() + 1).astype(str)
#                 st.session_state.master_data = combined_temp
                
#             st.session_state.processed_files.add(uploaded_file.name)
#             st.rerun()

# if not st.session_state.master_data.empty:
#     st.subheader("1. Sample ID List Table")

#     # --- BULK TOOLS SECTION ---
#     with st.expander("🛠️ Bulk Rename & Selection Tools"):
#         b_col1, b_col2, b_col3, b_col4 = st.columns(4)
#         with b_col1:
#             st.markdown("**Find & Replace**")
#             f_txt = st.text_input("Text to find", key="bulk_find")
#             r_txt = st.text_input("Replace with", key="bulk_replace")
#             if st.button("Replace in Names", key="btn_replace"):
#                 st.session_state.master_data['Sample Name'] = st.session_state.master_data['Sample Name'].str.replace(f_txt, r_txt)
#                 st.session_state.master_data['Run'] = (st.session_state.master_data.groupby('Sample Name').cumcount() + 1).astype(str)
#                 st.rerun()
#         with b_col2:
#             st.markdown("**Add Text**")
#             pre_txt = st.text_input("Add Prefix", key="bulk_prefix")
#             suf_txt = st.text_input("Add Suffix", key="bulk_suffix")
#             if st.button("Apply Text", key="btn_apply_text"):
#                 if pre_txt: st.session_state.master_data['Sample Name'] = pre_txt + st.session_state.master_data['Sample Name']
#                 if suf_txt: st.session_state.master_data['Sample Name'] = st.session_state.master_data['Sample Name'] + suf_txt
#                 st.session_state.master_data['Run'] = (st.session_state.master_data.groupby('Sample Name').cumcount() + 1).astype(str)
#                 st.rerun()
#         with b_col3:
#             st.markdown("**Batch Run Update**")
#             mode = st.radio("Run Logic", ["Set Constant", "Recalculate Occurrences (1,2,3...)"], key="bulk_run_mode")
#             val = st.number_input("Start Value Offset", min_value=0, step=1, value=1, key="bulk_run_val")
#             if st.button("Update Runs", key="btn_update_runs"):
#                 if mode == "Set Constant":
#                     st.session_state.master_data['Run'] = str(val)
#                 else:
#                     st.session_state.master_data['Run'] = (
#                         st.session_state.master_data.groupby('Sample Name').cumcount() + val
#                     ).astype(str)
#                 st.rerun()
#         with b_col4:
#             st.markdown("**Selection Control**")
#             if st.button("✅ Select All", key="btn_select_all"):
#                 st.session_state.master_data['Include'] = True
#                 st.rerun()
#             if st.button("❌ Deselect All", key="btn_deselect_all"):
#                 st.session_state.master_data['Include'] = False
#                 st.rerun()

#     edited_df = st.data_editor(
#         st.session_state.master_data,
#         key="editor_widget",
#         column_config={
#             "Include": st.column_config.CheckboxColumn("Plot?", default=True),
#             "Sample ID": st.column_config.TextColumn("Original ID", disabled=True),
#             "Datestamp": st.column_config.TextColumn("Date", disabled=True),
#             "Run": st.column_config.TextColumn("Run Custom Override"),
#         },
#         hide_index=True,
#         use_container_width=True,
#     )

#     col1, col2 = st.columns([1, 5])
#     with col1:
#         if st.button("Commit Changes", key="btn_commit"):
#             st.session_state.master_data = edited_df
#             st.success("Changes saved!")
    
#     with col2:
#         if st.button("Proceed to Plotting 📊", key="btn_proceed"):
#             st.session_state.master_data = edited_df 
#             st.session_state.show_plotting = True

# # --- PLOTTING & INSIGHTS ---
# if st.session_state.show_plotting:
#     st.divider()
#     st.markdown('<div class="insight-hint"><span>🤖</span><b>Automated Insights Available:</b> Scroll to Section 5 for AI root-cause analysis and custom queries.</div>', unsafe_allow_html=True)
    
#     st.subheader("2. Comparison Plotting")
#     base_filtered = st.session_state.master_data[st.session_state.master_data['Include'] == True]

#     if base_filtered.empty:
#         st.warning("No samples marked for selection. Please check the 'Plot?' boxes in the table above.")
#     else:
#         available_sample_names = sorted(base_filtered['Sample Name'].unique())
#         selected_samples = st.multiselect(
#             "🔎 Select Sample Names to Plot from Dropdown:",
#             options=available_sample_names,
#             default=available_sample_names,
#             key="sample_dropdown_filter"
#         )
        
#         final_filtered_master = base_filtered[base_filtered['Sample Name'].isin(selected_samples)]

#         if final_filtered_master.empty:
#             st.info("Please select at least one sample name from the dropdown menu to render plots.")
#         else:
#             plot_df = pd.merge(
#                 final_filtered_master, 
#                 st.session_state.raw_metrics_df, 
#                 left_on='Sample ID', 
#                 right_on='Sample'
#             )
            
#             core_metrics = ['PP-Gauss', 'PP-750', 'Barcode av.', 'Barcode std.', 'NrDrops']
#             available_metrics = [m for m in core_metrics if m in plot_df.columns]

#             # --- GLOBAL OUTLIER FILTER CONTROLS ---
#             st.markdown("#### 🛡️ Cross-Metric Outlier Configuration")
#             out_c1, out_c2, out_c3 = st.columns([1, 1, 2])
#             with out_c1:
#                 filter_metric = st.selectbox(
#                     "Metric to evaluate for Outliers:",
#                     options=available_metrics,
#                     index=available_metrics.index('Barcode std.') if 'Barcode std.' in available_metrics else 0,
#                     key="global_filter_metric"
#                 )
#             with out_c2:
#                 sigma_multiplier = st.selectbox(
#                     "Outlier Boundary (Sigma):",
#                     options=[1, 2, 3],
#                     index=1,
#                     format_func=lambda x: f"{x} Sigma ({x}σ)",
#                     key="global_sigma_multiplier"
#                 )
#             with out_c3:
#                 st.caption(f"**Rule Logic:** The system calculates the mean and standard deviation of **{filter_metric}** for each cohort. Points outside ±{sigma_multiplier}σ will be completely stripped out from the cleaned views.")

#             view_mode = st.radio(
#                 "Select Visualization Mode:",
#                 ["Detailed (Show Every Run)", "Global (Mean & Std Dev)"],
#                 horizontal=True,
#                 key="view_mode_selector"
#             )

#             # Pre-calculate the cleaned dataset globally so it matches across all plot windows and data tables
#             cleaned_plot_df_list = []
#             for name in plot_df['Sample Name'].unique():
#                 sub = plot_df[plot_df['Sample Name'] == name]
#                 if len(sub) > 1:
#                     mean_val = sub[filter_metric].mean()
#                     std_val = sub[filter_metric].std()
#                     if pd.isna(std_val) or std_val == 0:
#                         cleaned_plot_df_list.append(sub)
#                     else:
#                         cutoff = std_val * sigma_multiplier
#                         filtered_sub = sub[
#                             (sub[filter_metric] >= (mean_val - cutoff)) & 
#                             (sub[filter_metric] <= (mean_val + cutoff))
#                         ]
#                         cleaned_plot_df_list.append(filtered_sub)
#                 else:
#                     cleaned_plot_df_list.append(sub)
            
#             global_cleaned_df = pd.concat(cleaned_plot_df_list, ignore_index=True) if cleaned_plot_df_list else plot_df.copy()

#             # Track total lines pruned
#             lines_removed = len(plot_df) - len(global_cleaned_df)
#             if lines_removed > 0:
#                 st.toast(f"✂️ Pruned {lines_removed} outlier runs based on {filter_metric} ({sigma_multiplier}σ)!", icon="ℹ️")

#             # --- LOOP THROUGH PLOT WINDOWS ---
#             for i in range(st.session_state.num_plots):
#                 st.markdown(f"---")
#                 st.markdown(f"### Plot Window {i+1}")
#                 c1, c2 = st.columns(2)
                
#                 with c1:
#                     selected_metric = st.selectbox(
#                         f"Select Plotting Metric", 
#                         available_metrics, 
#                         key=f"metric_select_{i}",
#                         index=available_metrics.index('PP-Gauss') if 'PP-Gauss' in available_metrics and i == 0 else i % len(available_metrics)
#                     )
#                 with c2:
#                     sort_order = st.selectbox(
#                         "Sort Order",
#                         ["Default (Name)", "Ascending (by Mean)", "Descending (by Mean)"],
#                         key=f"sort_select_{i}"
#                     )

#                 def process_and_render_data(data_to_plot, is_clean_view):
#                     if view_mode == "Detailed (Show Every Run)":
#                         temp_df = data_to_plot.copy()
                        
#                         if sort_order != "Default (Name)":
#                             group_means = temp_df.groupby('Sample Name')[selected_metric].mean()
#                             ascending = True if "Ascending" in sort_order else False
#                             sorted_names = group_means.sort_values(ascending=ascending).index
#                             temp_df['Sample Name'] = pd.Categorical(temp_df['Sample Name'], categories=sorted_names, ordered=True)
#                             temp_df = temp_df.sort_values(['Sample Name', 'Datestamp', 'Run'])
#                         else:
#                             temp_df = temp_df.sort_values(by=['Sample Name', 'Datestamp', 'Run'])

#                         temp_df['Plot_X'] = (
#                             "<span style='color:teal; font-weight:bold'>" + temp_df['Sample Name'].astype(str) + "</span><br>" + 
#                             "<span style='color:gray'>" + temp_df['Datestamp'].astype(str) + "</span><br>" + 
#                             "<span style='color:tomato'>Run: " + temp_df['Run'].astype(str) + "</span>"
#                         )
                        
#                         y_val = temp_df[selected_metric]
#                         error_val = None
#                         custom_data = temp_df[['Description']]
#                         htemp = "<b>%{x}</b><br>Value: %{y}<br>Description: %{customdata[0]}<extra></extra>"
#                         display_df = temp_df

#                     else:
#                         agg_results = data_to_plot.groupby('Sample Name')[available_metrics].agg(['mean', 'std']).reset_index()
#                         agg_results.columns = [f"{col[0]}_{col[1]}" if col[1] else col[0] for col in agg_results.columns]
                        
#                         if sort_order != "Default (Name)":
#                             ascending = True if "Ascending" in sort_order else False
#                             agg_results = agg_results.sort_values(by=f"{selected_metric}_mean", ascending=ascending)
                        
#                         agg_results['Plot_X'] = "<span style='color:teal; font-weight:bold'>" + agg_results['Sample Name'] + "</span>"
                        
#                         y_val = agg_results[f"{selected_metric}_mean"]
#                         error_val = agg_results[f"{selected_metric}_std"]
#                         custom_data = error_val
#                         htemp = "<b>%{x}</b><br>Mean: %{y:.2f}<br>Std Dev: %{customdata:.2f}<extra></extra>"
#                         display_df = agg_results

#                     unique_names = plot_df['Sample Name'].unique()
#                     color_palette = px.colors.qualitative.Plotly 
#                     name_to_color = {name: color_palette[idx % len(color_palette)] for idx, name in enumerate(unique_names)}
#                     display_df['BarColor'] = display_df['Sample Name'].map(name_to_color)

#                     fig = go.Figure()
#                     fig.add_trace(
#                         go.Bar(
#                             x=display_df['Plot_X'], 
#                             y=y_val, 
#                             marker_color=display_df['BarColor'],
#                             text=y_val.round(2) if not y_val.isna().all() else "",
#                             textposition='auto',
#                             error_y=dict(type='data', array=error_val, visible=True) if view_mode == "Global (Mean & Std Dev)" else None,
#                             customdata=custom_data,
#                             hovertemplate=htemp
#                         )
#                     )

#                     title_lbl = f"{selected_metric} (Cleaned via {filter_metric} @ {sigma_multiplier}σ)" if is_clean_view else f"{selected_metric} (Unfiltered Original Data)"
#                     fig.update_layout(
#                         title=title_lbl,
#                         height=450, 
#                         yaxis_title=selected_metric, 
#                         template="plotly_white", 
#                         showlegend=False,
#                         yaxis=dict(range=[0, y_val.max() * 1.2] if not y_val.empty and not y_val.isna().all() else [0, 1])
#                     )
#                     fig.update_xaxes(tickangle=0)
#                     return fig

#                 graph_col1, graph_col2 = st.columns(2)
#                 with graph_col1:
#                     st.plotly_chart(process_and_render_data(plot_df, is_clean_view=False), use_container_width=True, key=f"chart_orig_{i}")
#                 with graph_col2:
#                     st.plotly_chart(process_and_render_data(global_cleaned_df, is_clean_view=True), use_container_width=True, key=f"chart_clean_{i}")

#             col_btn1, col_btn2 = st.columns([1, 4])
#             with col_btn1:
#                 if st.button("➕ Add Plot", key="btn_add_plot"):
#                     st.session_state.num_plots += 1
#                     st.rerun()
#             with col_btn2:
#                 if st.session_state.num_plots > 1:
#                     if st.button("Reset Plots", key="btn_reset_plots"):
#                         st.session_state.num_plots = 1
#                         st.rerun()

#             # --- SECTION 3: COHORT SUMMARY STATISTICS TABLE ---
#             st.write("---")
#             st.subheader("3. Cohort Summary Statistics Table (PP-Gauss Focus)")
            
#             sum_c1, sum_c2 = st.columns([1, 3])
#             with sum_c1:
#                 summary_data_source = st.radio(
#                     "Summary Metric Source:",
#                     ["Use Cleaned Dataset", "Use Original Dataset"],
#                     key="summary_dataset_toggle"
#                 )
#             with sum_c2:
#                 st.caption(f"This dynamic breakdown updates context metrics purely tracking standard operational deviations of the prime metric target parameter (`PP-Gauss`).")

#             chosen_summary_df = global_cleaned_df if summary_data_source == "Use Cleaned Dataset" else plot_df

#             if 'PP-Gauss' in chosen_summary_df.columns and not chosen_summary_df.empty:
#                 # Group data to extract requested summary metrics
#                 cohort_summary = chosen_summary_df.groupby('Sample Name')['PP-Gauss'].agg(
#                     Total_Runs='count',
#                     Mean_PP_Gauss='mean',
#                     Std_PP_Gauss='std'
#                 ).reset_index()
                
#                 # Calculate Coefficient of Variation (CV%)
#                 cohort_summary['CV%'] = (cohort_summary['Std_PP_Gauss'] / cohort_summary['Mean_PP_Gauss']) * 100
#                 cohort_summary['CV%'] = cohort_summary['CV%'].fillna(0)

#                 st.dataframe(
#                     cohort_summary,
#                     column_config={
#                         "Sample Name": st.column_config.TextColumn("Sample Name"),
#                         "Total_Runs": st.column_config.NumberColumn("Total Runs Count", format="%d"),
#                         "Mean_PP_Gauss": st.column_config.NumberColumn("Mean PP-Gauss", format="%.3f"),
#                         "Std_PP_Gauss": st.column_config.NumberColumn("Std. Deviation PP-Gauss", format="%.3f"),
#                         "CV%": st.column_config.NumberColumn("CV %", format="%.2f%%"),
#                     },
#                     hide_index=True,
#                     use_container_width=True
#                 )
#             else:
#                 st.info("PP-Gauss metric not found or dataset view empty. Summary table cannot be rendered.")

#             # --- SECTION 4: PLOTTED DATA REFERENCE TABLE ---
#             st.write("---")
#             st.subheader("4. Plotted Data Reference Table")
            
#             t_cfg1, t_cfg2 = st.columns([1, 3])
#             with t_cfg1:
#                 table_view_mode = st.radio(
#                     "Table Data Source:",
#                     ["Show Cleaned Dataset", "Show Original Unfiltered Dataset"],
#                     key="table_view_mode"
#                 )
#             with t_cfg2:
#                 if table_view_mode == "Show Cleaned Dataset":
#                     st.caption(f"Showing **{len(global_cleaned_df)} surviving rows**. Outliers based on variance in `{filter_metric}` have been filtered out.")
#                 else:
#                     st.caption(f"Showing **{len(plot_df)} complete original rows**.")

#             selected_table_source = global_cleaned_df if table_view_mode == "Show Cleaned Dataset" else plot_df
#             table_df = selected_table_source.copy()
            
#             if not table_df.empty:
#                 table_df['SAMPLE ID'] = table_df['Datestamp'].astype(str) + "_" + table_df['Sample Name'].astype(str) + "_" + table_df['Run'].astype(str)
                
#                 st.dataframe(
#                     table_df[['Datestamp', 'Sample Name', 'Run', 'SAMPLE ID'] + available_metrics],
#                     column_config={
#                         "Datestamp": st.column_config.TextColumn("Date", width=100),
#                         "Run": st.column_config.TextColumn("Run"), 
#                         "SAMPLE ID": st.column_config.TextColumn("Combined ID", width=300),
#                         **{m: st.column_config.NumberColumn(m, width=120, format="%.2f") for m in available_metrics}
#                     },
#                     hide_index=True,
#                     use_container_width=True
#                 )
#             else:
#                 st.info("The selected dataset view is empty.")

#         # --- SECTION 5: AUTOMATED DATA INSIGHTS ---
#         st.divider()
#         st.subheader("5. 🤖 Automated Data Insights")
        
#         with st.expander("⚙️ AI Analysis & Custom Questions", expanded=True):
#             i_col1, i_col2, i_col3 = st.columns([1, 1, 1])
#             with i_col1:
#                 ai_metric = st.selectbox("Target Analysis Metric", available_metrics, key="ai_target_metric")
#                 lens = st.selectbox("Select Expert Lens", ["General Analyst", "Quality Control Specialist", "Root Cause Investigator"], key="ai_lens")
#             with i_col2:
#                 custom_q = st.text_area("💬 Human Language Query", placeholder="e.g., 'Is there a correlation between NrDrops and the outliers in Sample B?'", key="ai_query")
#             with i_col3:
#                 st.write(" ")
#                 st.write(" ")
#                 generate_btn = st.button("Generate Insights 🪄", use_container_width=True, key="btn_generate_insights")

#         if generate_btn:
#             with st.spinner("Analyzing..."):
#                 final_report = get_detailed_insights(plot_df, ai_metric, lens, custom_q)
#                 st.info(final_report)

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
    * **📊 Cross-Metric Outlier Filtering**: Filter out anomalies using one parameter (e.g., *Barcode std.*) and view the surviving records plotted in your core parameter (e.g., *PP-Gauss*).
    * **📈 Cohort Summaries & CV% Shifts**: Section 3 tracks quantitative and visual shifts in the Coefficient of Variation ($CV\%$) between raw and refined streams.
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
            
            parsing_list = []
            for s_id in df['Sample'].unique():
                if s_id not in st.session_state.master_data['Sample ID'].tolist():
                    s_id_str = str(s_id)
                    
                    date_match = re.search(r'(\d{8})[-_]', s_id_str)
                    ds = date_match.group(1) if date_match else "Unknown"
                    
                    boundary_match = re.search(r'(?:[-_][a-zA-Z]+[-_])([a-zA-Z]+)', s_id_str)
                    
                    if boundary_match:
                        sample_name = boundary_match.group(1)
                    else:
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
                combined_temp = pd.concat([st.session_state.master_data, new_batch_df], ignore_index=True)
                combined_temp['Run'] = (combined_temp.groupby('Sample Name').cumcount() + 1).astype(str)
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
    st.markdown('<div class="insight-hint"><span>🤖</span><b>Automated Insights Available:</b> Scroll to Section 5 for AI root-cause analysis and custom queries.</div>', unsafe_allow_html=True)
    
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

            # --- GLOBAL OUTLIER FILTER CONTROLS ---
            st.markdown("#### 🛡️ Cross-Metric Outlier Configuration")
            out_c1, out_c2, out_c3 = st.columns([1, 1, 2])
            with out_c1:
                filter_metric = st.selectbox(
                    "Metric to evaluate for Outliers:",
                    options=available_metrics,
                    index=available_metrics.index('Barcode std.') if 'Barcode std.' in available_metrics else 0,
                    key="global_filter_metric"
                )
            with out_c2:
                sigma_multiplier = st.selectbox(
                    "Outlier Boundary (Sigma):",
                    options=[1, 2, 3],
                    index=1,
                    format_func=lambda x: f"{x} Sigma ({x}σ)",
                    key="global_sigma_multiplier"
                )
            with out_c3:
                st.caption(f"**Rule Logic:** The system calculates the mean and standard deviation of **{filter_metric}** for each cohort. Points outside ±{sigma_multiplier}σ will be completely stripped out from the cleaned views.")

            view_mode = st.radio(
                "Select Visualization Mode:",
                ["Detailed (Show Every Run)", "Global (Mean & Std Dev)"],
                horizontal=True,
                key="view_mode_selector"
            )

            # Pre-calculate the cleaned dataset globally so it matches across all plot windows and data tables
            cleaned_plot_df_list = []
            for name in plot_df['Sample Name'].unique():
                sub = plot_df[plot_df['Sample Name'] == name]
                if len(sub) > 1:
                    mean_val = sub[filter_metric].mean()
                    std_val = sub[filter_metric].std()
                    if pd.isna(std_val) or std_val == 0:
                        cleaned_plot_df_list.append(sub)
                    else:
                        cutoff = std_val * sigma_multiplier
                        filtered_sub = sub[
                            (sub[filter_metric] >= (mean_val - cutoff)) & 
                            (sub[filter_metric] <= (mean_val + cutoff))
                        ]
                        cleaned_plot_df_list.append(filtered_sub)
                else:
                    cleaned_plot_df_list.append(sub)
            
            global_cleaned_df = pd.concat(cleaned_plot_df_list, ignore_index=True) if cleaned_plot_df_list else plot_df.copy()

            # Track total lines pruned
            lines_removed = len(plot_df) - len(global_cleaned_df)
            if lines_removed > 0:
                st.toast(f"✂️ Pruned {lines_removed} outlier runs based on {filter_metric} ({sigma_multiplier}σ)!", icon="ℹ️")

            # --- LOOP THROUGH PLOT WINDOWS ---
            for i in range(st.session_state.num_plots):
                st.markdown(f"---")
                st.markdown(f"### Plot Window {i+1}")
                c1, c2 = st.columns(2)
                
                with c1:
                    selected_metric = st.selectbox(
                        f"Select Plotting Metric", 
                        available_metrics, 
                        key=f"metric_select_{i}",
                        index=available_metrics.index('PP-Gauss') if 'PP-Gauss' in available_metrics and i == 0 else i % len(available_metrics)
                    )
                with c2:
                    sort_order = st.selectbox(
                        "Sort Order",
                        ["Default (Name)", "Ascending (by Mean)", "Descending (by Mean)"],
                        key=f"sort_select_{i}"
                    )

                def process_and_render_data(data_to_plot, is_clean_view):
                    if view_mode == "Detailed (Show Every Run)":
                        temp_df = data_to_plot.copy()
                        
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
                        agg_results = data_to_plot.groupby('Sample Name')[available_metrics].agg(['mean', 'std']).reset_index()
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
                            text=y_val.round(2) if not y_val.isna().all() else "",
                            textposition='auto',
                            error_y=dict(type='data', array=error_val, visible=True) if view_mode == "Global (Mean & Std Dev)" else None,
                            customdata=custom_data,
                            hovertemplate=htemp
                        )
                    )

                    title_lbl = f"{selected_metric} (Cleaned via {filter_metric} @ {sigma_multiplier}σ)" if is_clean_view else f"{selected_metric} (Unfiltered Original Data)"
                    fig.update_layout(
                        title=title_lbl,
                        height=450, 
                        yaxis_title=selected_metric, 
                        template="plotly_white", 
                        showlegend=False,
                        yaxis=dict(range=[0, y_val.max() * 1.2] if not y_val.empty and not y_val.isna().all() else [0, 1])
                    )
                    fig.update_xaxes(tickangle=0)
                    return fig

                graph_col1, graph_col2 = st.columns(2)
                with graph_col1:
                    st.plotly_chart(process_and_render_data(plot_df, is_clean_view=False), use_container_width=True, key=f"chart_orig_{i}")
                with graph_col2:
                    st.plotly_chart(process_and_render_data(global_cleaned_df, is_clean_view=True), use_container_width=True, key=f"chart_clean_{i}")

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

            # --- SECTION 3: COHORT SUMMARY STATISTICS & CV% COMPARISON ---
            st.write("---")
            st.subheader("3. Cohort Summary Statistics Table & CV% Stability Delta")
            
            if 'PP-Gauss' in plot_df.columns and not plot_df.empty:
                # Calculate metrics for Original Dataset
                orig_summary = plot_df.groupby('Sample Name')['PP-Gauss'].agg(
                    Total_Runs_Orig='count', Mean_Orig='mean', Std_Orig='std'
                ).reset_index()
                orig_summary['CV%_Orig'] = (orig_summary['Std_Orig'] / orig_summary['Mean_Orig']) * 100

                # Calculate metrics for Cleaned Dataset
                clean_summary = global_cleaned_df.groupby('Sample Name')['PP-Gauss'].agg(
                    Total_Runs_Clean='count', Mean_Clean='mean', Std_Clean='std'
                ).reset_index()
                clean_summary['CV%_Clean'] = (clean_summary['Std_Clean'] / clean_summary['Mean_Clean']) * 100

                # Merge both summaries to generate side-by-side structures
                merged_summary = pd.merge(orig_summary, clean_summary, on='Sample Name', how='outer').fillna(0)

                # --- CV% COMPARISON PLOT ---
                cv_fig = go.Figure()
                cv_fig.add_trace(go.Bar(
                    x=merged_summary['Sample Name'],
                    y=merged_summary['CV%_Orig'],
                    name='Original Dataset CV%',
                    marker_color='#ef553b',
                    text=merged_summary['CV%_Orig'].round(2).astype(str) + '%',
                    textposition='auto'
                ))
                cv_fig.add_trace(go.Bar(
                    x=merged_summary['Sample Name'],
                    y=merged_summary['CV%_Clean'],
                    name=f'Cleaned Dataset CV% (via {filter_metric})',
                    marker_color='#636efa',
                    text=merged_summary['CV%_Clean'].round(2).astype(str) + '%',
                    textposition='auto'
                ))
                cv_fig.update_layout(
                    title=f"Stability Impact: PP-Gauss CV% Delta After Outlier Pruning",
                    xaxis_title="Sample Cohorts",
                    yaxis_title="Coefficient of Variation (CV %)",
                    barmode='group',
                    template='plotly_white',
                    height=400,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(cv_fig, use_container_width=True, key="cv_comparison_chart")

                # --- INTERACTIVE BREAKDOWN SUB-TABLE ---
                sum_c1, sum_c2 = st.columns([1, 3])
                with sum_c1:
                    summary_data_source = st.radio(
                        "Summary Metric Source for Table:",
                        ["Use Cleaned Dataset", "Use Original Dataset"],
                        key="summary_dataset_toggle"
                    )
                with sum_c2:
                    st.caption(f"Review granular analytical parameter statistics targeting variance reductions in the target tracking field `PP-Gauss` below.")

                # Construct appropriate user reporting sub-view
                if summary_data_source == "Use Cleaned Dataset":
                    table_summary_view = clean_summary.rename(columns={
                        'Total_Runs_Clean': 'Total_Runs', 'Mean_Clean': 'Mean_PP_Gauss',
                        'Std_Clean': 'Std_PP_Gauss', 'CV%_Clean': 'CV%'
                    })
                else:
                    table_summary_view = orig_summary.rename(columns={
                        'Total_Runs_Orig': 'Total_Runs', 'Mean_Orig': 'Mean_PP_Gauss',
                        'Std_Orig': 'Std_PP_Gauss', 'CV%_Orig': 'CV%'
                    })

                st.dataframe(
                    table_summary_view[['Sample Name', 'Total_Runs', 'Mean_PP_Gauss', 'Std_PP_Gauss', 'CV%']],
                    column_config={
                        "Sample Name": st.column_config.TextColumn("Sample Name"),
                        "Total_Runs": st.column_config.NumberColumn("Total Runs Count", format="%d"),
                        "Mean_PP_Gauss": st.column_config.NumberColumn("Mean PP-Gauss", format="%.3f"),
                        "Std_PP_Gauss": st.column_config.NumberColumn("Std. Deviation PP-Gauss", format="%.3f"),
                        "CV%": st.column_config.NumberColumn("CV %", format="%.2f%%"),
                    },
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("PP-Gauss metric not found or dataset view empty. Summary components skipped.")

            # --- SECTION 4: PLOTTED DATA REFERENCE TABLE ---
            st.write("---")
            st.subheader("4. Plotted Data Reference Table")
            
            t_cfg1, t_cfg2 = st.columns([1, 3])
            with t_cfg1:
                table_view_mode = st.radio(
                    "Table Data Source:",
                    ["Show Cleaned Dataset", "Show Original Unfiltered Dataset"],
                    key="table_view_mode"
                )
            with t_cfg2:
                if table_view_mode == "Show Cleaned Dataset":
                    st.caption(f"Showing **{len(global_cleaned_df)} surviving rows**. Outliers based on variance in `{filter_metric}` have been filtered out.")
                else:
                    st.caption(f"Showing **{len(plot_df)} complete original rows**.")

            selected_table_source = global_cleaned_df if table_view_mode == "Show Cleaned Dataset" else plot_df
            table_df = selected_table_source.copy()
            
            if not table_df.empty:
                table_df['SAMPLE ID'] = table_df['Datestamp'].astype(str) + "_" + table_df['Sample Name'].astype(str) + "_" + table_df['Run'].astype(str)
                
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
            else:
                st.info("The selected dataset view is empty.")

        # --- SECTION 5: AUTOMATED DATA INSIGHTS ---
        st.divider()
        st.subheader("5. 🤖 Automated Data Insights")
        
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