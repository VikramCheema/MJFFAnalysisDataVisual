import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import re

st.set_page_config(page_title="Sample Manager", layout="wide")

# --- INITIALIZATION ---
if 'master_data' not in st.session_state:
    # Removed 'Remarks' column as requested
    st.session_state.master_data = pd.DataFrame(columns=[
        'Sample ID', 'Datestamp', 'Sample Name', 'Run', 'Description'
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
                    # Pattern: finds 8 digits (\d{8}) that are followed by - or _
                    date_match = re.search(r'(\d{8})[-_]', s_id_str)
                    
                    if date_match:
                        ds = date_match.group(1)
                        # The "rest" is everything after the date and its separator
                        rest = s_id_str.split(ds, 1)[1].lstrip('-_')
                    else:
                        # Fallback if no 8-digit date is found
                        ds = "Unknown"
                        rest = s_id_str
                    
                    # 2. Extract Run from the very end (after last underscore)
                    sample_name = rest
                    run_val = 1
                    
                    if "_" in rest:
                        parts = rest.rsplit("_", 1)
                        if parts[1].isdigit():
                            sample_name = parts[0]
                            run_val = int(parts[1])
                    
                    new_rows.append({
                        'Sample ID': s_id, 
                        'Datestamp': ds, 
                        'Sample Name': sample_name, 
                        'Run': run_val, 
                        'Description': ""
                    })
            
            if new_rows:
                new_df = pd.DataFrame(new_rows)
                st.session_state.master_data = pd.concat([st.session_state.master_data, new_df], ignore_index=True)
            
            st.session_state.processed_files.add(uploaded_file.name)
            st.rerun()

if not st.session_state.master_data.empty:
    st.subheader("1. Sample ID List Table")

    with st.expander("🛠️ Bulk Rename Tools (Finder Style)"):
        b_col1, b_col2, b_col3 = st.columns(3)
        
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
                    # Incrementing sequence
                    st.session_state.master_data['Run'] = range(val, val + len(st.session_state.master_data))
                st.rerun()

    # --- THE DATA EDITOR ---
    edited_df = st.data_editor(
        st.session_state.master_data,
        key="editor_widget",
        column_config={
            "Sample ID": st.column_config.TextColumn("Original ID", disabled=True),
            "Datestamp": st.column_config.TextColumn("Date", disabled=True),
            "Sample Name": st.column_config.TextColumn("Sample Name"),
            "Run": st.column_config.NumberColumn("Run", step=1),
            "Description": st.column_config.TextColumn("Description"),
        },
        hide_index=True,
        use_container_width=True,
    )

    # Standard Save/Proceed Buttons
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("Commit Changes"):
            st.session_state.master_data = edited_df
            st.success("Changes saved!")
    
    with col2:
        if st.button("Proceed to Plotting 📊"):
            st.session_state.master_data = edited_df 
            st.session_state.show_plotting = True

# --- INITIALIZE PLOT COUNTER ---
if 'num_plots' not in st.session_state:
    st.session_state.num_plots = 1
# --- PLOTTING PROTOCOL ---
if st.session_state.show_plotting:
    st.divider()
    st.subheader("2. Comparison Plotting")

    # 1. Prepare Base Data
    plot_df = pd.merge(
        st.session_state.master_data, 
        st.session_state.raw_metrics_df, 
        left_on='Sample ID', 
        right_on='Sample'
    )
    
    core_metrics = ['PP-Gauss', 'PP-750', 'Barcode av.', 'Barcode std.', 'NrDrops']
    available_metrics = [m for m in core_metrics if m in plot_df.columns]

    # --- VIEW MODE SELECTION ---
    view_mode = st.radio(
        "Select Visualization Mode:",
        ["Detailed (Show Every Run)", "Global (Mean & Std Dev)"],
        horizontal=True
    )

    if view_mode == "Detailed (Show Every Run)":
        # Sort for grouping
        plot_df = plot_df.sort_values(by=['Sample Name', 'Datestamp', 'Run'])
        
        # Create the IDs for the detailed view
        plot_df['SAMPLE ID'] = (
            plot_df['Datestamp'].astype(str) + "_" + 
            plot_df['Sample Name'].astype(str) + "_" + 
            plot_df['Run'].astype(str)
        )
        
        plot_df['Plot_X'] = (
            "<span style='color:teal; font-weight:bold'>" + plot_df['Sample Name'].fillna("Unnamed") + "</span><br>" + 
            "<span style='color:gray'>" + plot_df['Datestamp'] + "</span><br>" + 
            "<span style='color:tomato'>Run: " + plot_df['Run'].astype(str) + "</span>"
        )
        display_df = plot_df
        use_error_bars = False
        # Table columns for detailed view
        table_cols = ['Datestamp', 'Sample Name', 'Run', 'SAMPLE ID'] + available_metrics

    else:
        # GLOBAL AGGREGATION LOGIC
        # We also count how many runs are in each group ('size')
        agg_results = plot_df.groupby('Sample Name')[available_metrics].agg(['mean', 'std', 'count']).reset_index()
        
        # Flatten columns
        agg_results.columns = [f"{col[0]}_{col[1]}" if col[1] else col[0] for col in agg_results.columns]
        
        # Create a display ID for the global table
        agg_results['SAMPLE ID'] = "AGGREGATED_" + agg_results['Sample Name']
        agg_results['Plot_X'] = "<span style='color:teal; font-weight:bold'>" + agg_results['Sample Name'] + "</span>"
        
        display_df = agg_results
        use_error_bars = True
        # Table columns for global view (using the means)
        mean_cols = [f"{m}_mean" for m in available_metrics]
        table_cols = ['Sample Name', 'SAMPLE ID'] + mean_cols

    # 2. Handle Colors
    unique_names = plot_df['Sample Name'].unique()
    color_palette = px.colors.qualitative.Plotly 
    name_to_color = {name: color_palette[i % len(color_palette)] for i, name in enumerate(unique_names)}
    display_df['BarColor'] = display_df['Sample Name'].map(name_to_color)

    # 3. Render Plot Windows
    for i in range(st.session_state.num_plots):
        selected_metric = st.selectbox(
            f"Select Metric for Plot {i+1}", 
            available_metrics, 
            key=f"metric_select_{i}",
            index=i % len(available_metrics)
        )

        fig = go.Figure()

        if not use_error_bars:
            y_val = display_df[selected_metric]
            error_val = None
            custom_data = display_df[['Description']]
            htemp = "<b>%{x}</b><br>Value: %{y}<br>Description: %{customdata[0]}<extra></extra>"
        else:
            y_val = display_df[f"{selected_metric}_mean"]
            error_val = display_df[f"{selected_metric}_std"]
            custom_data = error_val
            htemp = "<b>%{x}</b><br>Mean: %{y:.2f}<br>Std Dev: %{customdata:.2f}<extra></extra>"

        fig.add_trace(
            go.Bar(
                x=display_df['Plot_X'], 
                y=y_val, 
                marker_color=display_df['BarColor'],
                text=y_val.round(2),
                textposition='auto',
                error_y=dict(type='data', array=error_val, visible=True) if use_error_bars else None,
                customdata=custom_data,
                hovertemplate=htemp
            )
        )

        fig.update_layout(height=500, yaxis_title=selected_metric, template="plotly_white", showlegend=False)
        fig.update_xaxes(tickangle=0)
        st.plotly_chart(fig, use_container_width=True)

    # UI Buttons for plots
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

    # 4. THE PLOTTED DATA TABLE
    st.write("---")
    st.subheader("3. Plotted Data Reference Table")
    
    # Configure columns dynamically to avoid errors in Global mode
    base_config = {
        "Datestamp": st.column_config.TextColumn("Date", width=100),
        "Sample Name": st.column_config.TextColumn("Sample Name", width=150),
        "Run": st.column_config.NumberColumn("Run", format="%d", width=60),
        "SAMPLE ID": st.column_config.TextColumn("Combined ID", width=300),
    }
    
    # Add metrics to config
    for m in available_metrics:
        col_name = m if not use_error_bars else f"{m}_mean"
        base_config[col_name] = st.column_config.NumberColumn(m, width=120, format="%.2f")

    st.dataframe(
        display_df[table_cols],
        column_config=base_config,
        hide_index=True,
        use_container_width=True
    )