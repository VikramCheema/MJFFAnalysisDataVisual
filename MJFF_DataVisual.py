import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px


st.set_page_config(page_title="Sample Manager", layout="wide")

# --- INITIALIZATION ---
if 'master_data' not in st.session_state:
    st.session_state.master_data = pd.DataFrame(columns=[
        'Sample ID', 'Datestamp', 'Sample Name', 'Run', 'Description', 'Remarks'
    ])

# Store the numerical data from CSVs separately to merge later
if 'raw_metrics_df' not in st.session_state:
    st.session_state.raw_metrics_df = pd.DataFrame()

if 'processed_files' not in st.session_state:
    st.session_state.processed_files = set()

# Flag to trigger the plotting section
if 'show_plotting' not in st.session_state:
    st.session_state.show_plotting = False

st.title("MJFF Analysis Data Visualization")

# --- FILE UPLOADER ---
uploaded_file = st.file_uploader("Upload CSV", type="csv")

if uploaded_file:
    if uploaded_file.name not in st.session_state.processed_files:
        df = pd.read_csv(uploaded_file)
        if 'Sample' in df.columns:
            # Store raw metrics for plotting later
            st.session_state.raw_metrics_df = pd.concat(
                [st.session_state.raw_metrics_df, df], ignore_index=True
            ).drop_duplicates(subset=['Sample'])
            
            new_ids = df['Sample'].unique()
            existing_ids = st.session_state.master_data['Sample ID'].tolist()
            new_rows = []
            for s_id in new_ids:
                if s_id not in existing_ids:
                    ds = s_id.split('-')[0] if '-' in s_id else ""
                    new_rows.append({
                        'Sample ID': s_id, 'Datestamp': ds, 
                        'Sample Name': "", 'Run': 0, 
                        'Description': "", 'Remarks': ""
                    })
            
            if new_rows:
                new_df = pd.DataFrame(new_rows)
                st.session_state.master_data = pd.concat([st.session_state.master_data, new_df], ignore_index=True)
            
            st.session_state.processed_files.add(uploaded_file.name)
            st.rerun()

# --- THE DATA EDITOR ---
if not st.session_state.master_data.empty:
    st.subheader("1. Sample ID List Table")
    
    edited_df = st.data_editor(
        st.session_state.master_data,
        key="editor_widget",
        column_config={
            "Sample ID": st.column_config.TextColumn(disabled=True),
            "Datestamp": st.column_config.TextColumn(disabled=True),
            "Run": st.column_config.NumberColumn(step=1),
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
        # This button appears once data is loaded, but only starts plotting logic when clicked
        if st.button("Proceed to Plotting 📊"):
            st.session_state.master_data = edited_df # Final save
            st.session_state.show_plotting = True

# --- INITIALIZE PLOT COUNTER ---
if 'num_plots' not in st.session_state:
    st.session_state.num_plots = 1
# --- PLOTTING PROTOCOL ---
if st.session_state.show_plotting:
    st.divider()
    st.subheader("2. Comparison Plotting")

    # 1. Prepare Data
    plot_df = pd.merge(
        st.session_state.master_data, 
        st.session_state.raw_metrics_df, 
        left_on='Sample ID', 
        right_on='Sample'
    )
    
    # Sort by Sample Name to group them
    plot_df = plot_df.sort_values(by=['Sample Name', 'Datestamp', 'Run'])

    # 2. Create the Requested "SAMPLE ID" and "Display Label"
    plot_df['SAMPLE ID'] = (
        plot_df['Datestamp'].astype(str) + "_" + 
        plot_df['Sample Name'].astype(str) + "_" + 
        plot_df['Run'].astype(str)
    )

    plot_df['Display Label'] = (
        "<span style='color:teal; font-weight:bold'>" + plot_df['Sample Name'].fillna("Unnamed") + "</span><br>" + 
        "<span style='color:gray'>" + plot_df['Datestamp'] + "</span><br>" + 
        "<span style='color:tomato'>Run: " + plot_df['Run'].astype(str) + "</span>"
    )

    # 3. Handle Colors
    unique_names = plot_df['Sample Name'].unique()
    color_palette = px.colors.qualitative.Plotly 
    name_to_color = {name: color_palette[i % len(color_palette)] for i, name in enumerate(unique_names)}
    plot_df['BarColor'] = plot_df['Sample Name'].map(name_to_color)

    core_metrics = ['PP-Gauss', 'PP-750', 'Barcode av.', 'Barcode std.', 'NrDrops']
    available_metrics = [m for m in core_metrics if m in plot_df.columns]

    # 4. Render Plot Windows
    for i in range(st.session_state.num_plots):
        selected_metric = st.selectbox(
            f"Select Metric for Plot {i+1}", 
            available_metrics, 
            key=f"metric_select_{i}",
            index=i % len(available_metrics)
        )

        fig = go.Figure()
        
        # Improvement: Round values for cleaner bar text labels
        bar_text = plot_df[selected_metric].round(2)

        fig.add_trace(
            go.Bar(
                x=plot_df['Display Label'], 
                y=plot_df[selected_metric], 
                marker_color=plot_df['BarColor'],
                # NEW: Add text labels on top of bars
                text=bar_text,
                textposition='auto', # 'auto' puts it inside if it fits, outside if it doesn't
                textfont=dict(size=12, color="white"), # Optional styling
                customdata=plot_df[['Description', 'Remarks']],
                hovertemplate="<b>%{x}</b><br>Value: %{y}<br>Description: %{customdata[0]}<br>Remarks: %{customdata[1]}<extra></extra>"
            )
        )

        fig.update_layout(
            height=450, 
            yaxis_title=selected_metric, 
            template="plotly_white", 
            showlegend=False,
            # Ensure enough space for labels on top of bars
            yaxis=dict(range=[0, plot_df[selected_metric].max() * 1.15]) 
        )
        fig.update_xaxes(tickangle=0)
        st.plotly_chart(fig, use_container_width=True)

    # UI Buttons for adding plots
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

    # 5. THE PLOTTED DATA TABLE (Refined Width Control)
    st.write("---")
    st.subheader("3. Plotted Data Reference Table")
    
    display_cols = ['Datestamp', 'Sample Name', 'Run', 'SAMPLE ID'] + available_metrics
    
    st.dataframe(
        plot_df[display_cols],
        column_config={
            # Use specific integer pixel values for strict control
            "Datestamp": st.column_config.TextColumn("Date", width=100),
            "Sample Name": st.column_config.TextColumn("Sample Name", width=150),
            "Run": st.column_config.NumberColumn("Run", format="%d", width=60),
            "SAMPLE ID": st.column_config.TextColumn("Combined ID", width=300),
            # You can even set widths for the metrics
            **{m: st.column_config.NumberColumn(m, width=120) for m in available_metrics}
        },
        hide_index=True,
        use_container_width=True
    )