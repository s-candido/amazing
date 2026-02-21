"""
CRM Dashboard - User Segmentation Analysis
Interactive visualization of clustered user segments with detailed user profiles
"""

import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from pathlib import Path
import re

# Page configuration
st.set_page_config(
    page_title="CRM Dashboard - User Segmentation",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database connection
DB_PATH = Path(__file__).parent.parent / "amazing.duckdb"

@st.cache_resource
def get_db_connection():
    """Create persistent DuckDB connection"""
    return duckdb.connect(str(DB_PATH), read_only=True)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_table_info():
    """Get basic info about user_profiles table without loading all data"""
    con = get_db_connection()
    
    # Check if table exists
    tables = con.execute("SHOW TABLES").df()
    if 'user_profiles' not in tables['name'].values:
        return None, [], 0
    
    # Get column names
    columns = con.execute("DESCRIBE user_profiles").df()
    all_cols = columns['column_name'].tolist()
    segment_cols = [col for col in all_cols if col.startswith('segment_')]
    
    # Get total count
    total_users = con.execute("SELECT COUNT(*) as cnt FROM user_profiles").df()['cnt'].iloc[0]
    
    return all_cols, segment_cols, total_users

@st.cache_data(ttl=300)
def load_user_profiles_sample(segment_col, sample_size=10000, segment_filter=None):
    """Load a sample of user profiles for visualization (optimized for large datasets)"""
    con = get_db_connection()
    
    # Build query with optional segment filter
    if segment_filter and segment_filter != 'All':
        query = f"""
            SELECT * FROM user_profiles 
            WHERE {segment_col} = '{segment_filter}'
            LIMIT {sample_size}
        """
    else:
        # Use stratified sampling to get representative sample from each segment
        query = f"""
            WITH segment_counts AS (
                SELECT {segment_col} as seg, COUNT(*) as cnt
                FROM user_profiles
                WHERE {segment_col} IS NOT NULL
                GROUP BY {segment_col}
            ),
            samples_per_segment AS (
                SELECT seg, GREATEST(CAST({sample_size} / (SELECT COUNT(DISTINCT {segment_col}) FROM user_profiles WHERE {segment_col} IS NOT NULL) AS INTEGER), 100) as sample_size
                FROM segment_counts
            )
            SELECT up.*
            FROM user_profiles up
            INNER JOIN samples_per_segment sps ON up.{segment_col} = sps.seg
            WHERE up.{segment_col} IS NOT NULL
            ORDER BY RANDOM()
            LIMIT {sample_size}
        """
    
    df = con.execute(query).df()
    return df

@st.cache_data(ttl=300)
def load_single_user(user_id):
    """Load data for a single user"""
    con = get_db_connection()
    df = con.execute(f"SELECT * FROM user_profiles WHERE user_id = '{user_id}'").df()
    return df

@st.cache_data(ttl=300)
def get_segment_stats(segment_col):
    """Calculate statistics for each segment (optimized for large datasets)"""
    con = get_db_connection()
    
    # Aggregate directly in DuckDB
    stats = con.execute(f"""
        SELECT 
            {segment_col} as segment,
            COUNT(*) as user_count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage
        FROM user_profiles
        WHERE {segment_col} IS NOT NULL
        GROUP BY {segment_col}
        ORDER BY segment
    """).df()
    
    # Add segment descriptions
    segment_labels = {
        'A': '🌟 High-Value Customers',
        'B': '💪 Engaged Users',
        'C': '👀 Moderate Activity',
        'D': '😴 Low Engagement'
    }
    stats['label'] = stats['segment'].map(segment_labels)
    
    return stats

@st.cache_data(ttl=300)
def get_user_ids_for_segment(segment_col, segment_value, limit=1000):
    """Get list of user IDs for a specific segment"""
    con = get_db_connection()
    
    if segment_value == 'All':
        query = f"SELECT user_id FROM user_profiles LIMIT {limit}"
    else:
        query = f"SELECT user_id FROM user_profiles WHERE {segment_col} = '{segment_value}' LIMIT {limit}"
    
    user_ids = con.execute(query).df()['user_id'].tolist()
    return user_ids

def create_cluster_network_viz(df, segment_col):
    """Create interactive network/scatter visualization of user clusters"""
    
    # Filter valid segments
    plot_df = df[df[segment_col].notna()].copy()
    
    if len(plot_df) == 0:
        return None
    
    # Add some jitter for visualization (simulated clustering positions)
    np.random.seed(42)
    segment_positions = {
        'A': (2, 2),
        'B': (2, -2),
        'C': (-2, 2),
        'D': (-2, -2)
    }
    
    plot_df['x'] = plot_df[segment_col].map(lambda s: segment_positions.get(s, (0, 0))[0])
    plot_df['y'] = plot_df[segment_col].map(lambda s: segment_positions.get(s, (0, 0))[1])
    
    # Add jitter
    plot_df['x'] += np.random.normal(0, 0.5, len(plot_df))
    plot_df['y'] += np.random.normal(0, 0.5, len(plot_df))
    
    # Color mapping
    color_map = {
        'A': '#2ecc71',  # Green
        'B': '#3498db',  # Blue
        'C': '#f39c12',  # Orange
        'D': '#e74c3c'   # Red
    }
    
    plot_df['color'] = plot_df[segment_col].map(color_map)
    
    # Create scatter plot
    fig = go.Figure()
    
    for segment in ['A', 'B', 'C', 'D']:
        segment_data = plot_df[plot_df[segment_col] == segment]
        
        if len(segment_data) > 0:
            segment_labels = {
                'A': 'High-Value (A)',
                'B': 'Engaged (B)',
                'C': 'Moderate (C)',
                'D': 'Low Engagement (D)'
            }
            
            fig.add_trace(go.Scatter(
                x=segment_data['x'],
                y=segment_data['y'],
                mode='markers',
                name=segment_labels[segment],
                marker=dict(
                    size=12,
                    color=color_map[segment],
                    opacity=0.7,
                    line=dict(width=1, color='white')
                ),
                text=segment_data['user_id'],
                customdata=segment_data['user_id'],
                hovertemplate='<b>User ID:</b> %{text}<br><b>Segment:</b> ' + segment + '<extra></extra>'
            ))
    
    fig.update_layout(
        title=f"User Segmentation Clusters - {segment_col.replace('segment_', '').replace('_', '/')}",
        xaxis=dict(showgrid=True, zeroline=True, showticklabels=False, title=""),
        yaxis=dict(showgrid=True, zeroline=True, showticklabels=False, title=""),
        hovermode='closest',
        plot_bgcolor='rgba(240,240,240,0.5)',
        height=600,
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    )
    
    return fig

def create_segment_distribution(stats_df):
    """Create pie chart for segment distribution"""
    colors = {
        'A': '#2ecc71',
        'B': '#3498db',
        'C': '#f39c12',
        'D': '#e74c3c'
    }
    
    fig = go.Figure(data=[go.Pie(
        labels=stats_df['label'],
        values=stats_df['user_count'],
        marker=dict(colors=[colors[s] for s in stats_df['segment']]),
        textinfo='label+percent',
        hovertemplate='<b>%{label}</b><br>Users: %{value}<br>Percentage: %{percent}<extra></extra>'
    )])
    
    fig.update_layout(
        title="Segment Distribution",
        height=400
    )
    
    return fig

def display_user_profile(user_id, segment_cols):
    """Display detailed user profile (optimized to load single user)"""
    # Load only this user's data
    user_data = load_single_user(user_id)
    
    if len(user_data) == 0:
        st.error(f"User {user_id} not found")
        return
    
    user_row = user_data.iloc[0]
    
    # Header
    st.markdown(f"## 👤 User Profile: `{user_id}`")
    
    # Current Segment (latest period)
    if segment_cols:
        latest_segment = segment_cols[-1]
        current_seg = user_row[latest_segment]
        
        segment_info = {
            'A': ('🌟 High-Value Customer', 'success'),
            'B': ('💪 Engaged User', 'info'),
            'C': ('👀 Moderate Activity', 'warning'),
            'D': ('😴 Low Engagement', 'error')
        }
        
        label, badge = segment_info.get(current_seg, ('Unknown', 'secondary'))
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Current Segment", current_seg)
        with col2:
            st.markdown(f"**Category:** {label}")
        with col3:
            period = latest_segment.replace('segment_', '').replace('_', '/')
            st.markdown(f"**Period:** {period}")
    
    st.divider()
    
    # Segment Evolution
    if len(segment_cols) > 1:
        st.markdown("### 📊 Segment Evolution")
        
        evolution_data = []
        for col in sorted(segment_cols):
            period = col.replace('segment_', '').replace('_', '/')
            segment = user_row[col]
            if pd.notna(segment):
                evolution_data.append({'Period': period, 'Segment': segment})
        
        if evolution_data:
            evo_df = pd.DataFrame(evolution_data)
            
            # Timeline visualization
            color_map = {
                'A': '#2ecc71',
                'B': '#3498db',
                'C': '#f39c12',
                'D': '#e74c3c'
            }
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=evo_df['Period'],
                y=evo_df['Segment'],
                mode='lines+markers',
                marker=dict(
                    size=15,
                    color=[color_map[s] for s in evo_df['Segment']],
                    line=dict(width=2, color='white')
                ),
                line=dict(width=3, color='gray'),
                hovertemplate='<b>Period:</b> %{x}<br><b>Segment:</b> %{y}<extra></extra>'
            ))
            
            fig.update_layout(
                title="Segment Changes Over Time",
                xaxis_title="Period (MM/YYYY)",
                yaxis_title="Segment",
                yaxis=dict(categoryorder='array', categoryarray=['D', 'C', 'B', 'A']),
                height=300,
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Summary table
            col1, col2 = st.columns(2)
            with col1:
                st.dataframe(evo_df, use_container_width=True, hide_index=True)
            with col2:
                # Calculate stability
                if len(evo_df) > 1:
                    changes = sum(evo_df['Segment'].iloc[i] != evo_df['Segment'].iloc[i+1] 
                                 for i in range(len(evo_df)-1))
                    stability = ((len(evo_df) - 1 - changes) / (len(evo_df) - 1) * 100)
                    st.metric("Segment Stability", f"{stability:.1f}%")
                    st.metric("Number of Changes", changes)
    
    st.divider()
    
    # Raw data
    with st.expander("📋 Full User Data"):
        user_dict = user_row.to_dict()
        st.json(user_dict)

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    # Title
    st.title("👥 CRM Dashboard - User Segmentation Analysis")
    st.markdown("Interactive visualization and analysis of user clusters based on behavior")
    
    # Load table info (lightweight)
    with st.spinner("Loading database info..."):
        all_cols, segment_cols, total_users = get_table_info()
    
    if all_cols is None or total_users == 0:
        st.error("⚠️ No user_profiles table found in database. Please run the interpret_clusters notebook first.")
        st.info("📍 Database location: `amazing.duckdb`")
        return
    
    # Sidebar
    st.sidebar.header("⚙️ Dashboard Controls")
    
    # Performance warning for large datasets
    if total_users > 50000:
        st.sidebar.warning(f"⚠️ Large dataset detected: {total_users:,} users")
        st.sidebar.info("Using optimized sampling for visualization")
    
    # Period selection
    if segment_cols:
        selected_period = st.sidebar.selectbox(
            "Select Period",
            segment_cols,
            index=len(segment_cols)-1,  # Default to latest
            format_func=lambda x: x.replace('segment_', 'Period: ').replace('_', '/')
        )
    else:
        st.error("No segment data available")
        return
    
    # Sample size control for visualization
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎲 Visualization Settings")
    
    if total_users > 10000:
        max_sample = min(20000, total_users)
        default_sample = min(10000, total_users)
        sample_size = st.sidebar.slider(
            "Sample size for visualization",
            min_value=1000,
            max_value=max_sample,
            value=default_sample,
            step=1000,
            help=f"Loading all {total_users:,} users would be slow. Use sampling for better performance."
        )
    else:
        sample_size = total_users
        st.sidebar.info(f"Using all {total_users:,} users")
    
    # Segment filter for visualization
    stats_df = get_segment_stats(selected_period)
    
    segment_filter = st.sidebar.selectbox(
        "Filter by Segment",
        ['All'] + sorted(stats_df['segment'].tolist()),
        help="Filter visualization to specific segment"
    )
    
    # Statistics
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Quick Stats")
    st.sidebar.metric("Total Users", f"{total_users:,}")
    st.sidebar.metric("Available Periods", len(segment_cols))
    
    if len(stats_df) > 0:
        st.sidebar.dataframe(
            stats_df[['segment', 'user_count', 'percentage']].rename(columns={
                'segment': 'Seg',
                'user_count': 'Users',
                'percentage': '%'
            }),
            hide_index=True,
            use_container_width=True
        )
    
    # Main content
    tab1, tab2, tab3 = st.tabs(["🎯 Cluster Visualization", "📊 Analytics", "🔍 User Lookup"])
    
    with tab1:
        st.markdown("### Interactive User Cluster Network")
        
        # Show sampling info
        if total_users > sample_size:
            st.info(f"📊 Displaying {sample_size:,} sampled users out of {total_users:,} total (stratified sampling for representative distribution)")
        
        # Load sample data
        with st.spinner("Loading user data..."):
            df_sample = load_user_profiles_sample(selected_period, sample_size, segment_filter)
        
        if len(df_sample) == 0:
            st.warning("No data available for selected filters")
        else:
            st.markdown(f"**Loaded {len(df_sample):,} users for visualization**")
            
            # Create visualization
            fig = create_cluster_network_viz(df_sample, selected_period)
            
            if fig:
                # Display chart
                st.plotly_chart(fig, use_container_width=True, key="cluster_viz")
                
                # User selection
                st.markdown("---")
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown("### 🔍 Select User for Details")
                
                with col2:
                    # Sample random users for quick selection
                    if st.button("🎲 Random User"):
                        st.session_state['selected_user'] = df_sample['user_id'].sample(1).iloc[0]
                
                # User ID input with search
                st.markdown("#### Search for User")
                user_search = st.text_input("Enter User ID:", key="user_search", help="Type to search for a specific user")
                
                if user_search:
                    # Try to load this user
                    selected_user = user_search
                elif 'selected_user' in st.session_state:
                    selected_user = st.session_state['selected_user']
                else:
                    selected_user = df_sample['user_id'].iloc[0] if len(df_sample) > 0 else None
                
                if selected_user:
                    st.markdown("---")
                    display_user_profile(selected_user, segment_cols)
            else:
                st.warning("No data available for visualization")
    
    with tab2:
        st.markdown("### 📈 Segment Analytics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Distribution pie chart
            if len(stats_df) > 0:
                fig_dist = create_segment_distribution(stats_df)
                st.plotly_chart(fig_dist, use_container_width=True)
        
        with col2:
            # Bar chart
            if len(stats_df) > 0:
                fig_bar = px.bar(
                    stats_df,
                    x='segment',
                    y='user_count',
                    color='segment',
                    color_discrete_map={
                        'A': '#2ecc71',
                        'B': '#3498db',
                        'C': '#f39c12',
                        'D': '#e74c3c'
                    },
                    labels={'user_count': 'Number of Users', 'segment': 'Segment'},
                    title='Users per Segment'
                )
                fig_bar.update_layout(showlegend=False, height=400)
                st.plotly_chart(fig_bar, use_container_width=True)
        
        # Temporal evolution
        if len(segment_cols) >= 2:
            st.markdown("### 📅 Temporal Evolution")
            
            # Calculate segment counts over time using DuckDB
            con = get_db_connection()
            
            temporal_data = []
            for col in sorted(segment_cols):
                period = col.replace('segment_', '').replace('_', '/')
                counts = con.execute(f"""
                    SELECT {col} as segment, COUNT(*) as count
                    FROM user_profiles
                    WHERE {col} IS NOT NULL
                    GROUP BY {col}
                    ORDER BY segment
                """).df()
                
                for _, row in counts.iterrows():
                    temporal_data.append({
                        'Period': period,
                        'Segment': row['segment'],
                        'Count': row['count']
                    })
            
            temp_df = pd.DataFrame(temporal_data)
            
            fig_temp = px.line(
                temp_df,
                x='Period',
                y='Count',
                color='Segment',
                color_discrete_map={
                    'A': '#2ecc71',
                    'B': '#3498db',
                    'C': '#f39c12',
                    'D': '#e74c3c'
                },
                markers=True,
                title='Segment Evolution Over Time'
            )
            fig_temp.update_layout(height=400)
            st.plotly_chart(fig_temp, use_container_width=True)
            
            # Transition matrix
            if len(segment_cols) >= 2:
                st.markdown("### 🔄 Segment Transitions")
                
                prev_col = segment_cols[-2]
                curr_col = segment_cols[-1]
                
                # Calculate transitions in DuckDB
                transition_data = con.execute(f"""
                    SELECT 
                        {prev_col} as from_segment,
                        {curr_col} as to_segment,
                        COUNT(*) as count
                    FROM user_profiles
                    WHERE {prev_col} IS NOT NULL AND {curr_col} IS NOT NULL
                    GROUP BY {prev_col}, {curr_col}
                    ORDER BY from_segment, to_segment
                """).df()
                
                if len(transition_data) > 0:
                    # Create transition matrix
                    trans_matrix = transition_data.pivot(
                        index='from_segment',
                        columns='to_segment',
                        values='count'
                    ).fillna(0)
                    
                    # Normalize to percentages
                    trans_matrix = trans_matrix.div(trans_matrix.sum(axis=1), axis=0) * 100
                    
                    # Ensure all segments are present
                    for seg in ['A', 'B', 'C', 'D']:
                        if seg not in trans_matrix.index:
                            trans_matrix.loc[seg] = 0
                        if seg not in trans_matrix.columns:
                            trans_matrix[seg] = 0
                    
                    trans_matrix = trans_matrix.sort_index().sort_index(axis=1)
                    
                    # Heatmap
                    fig_heat = px.imshow(
                        trans_matrix,
                        labels=dict(x="To Segment", y="From Segment", color="% of Users"),
                        x=['A', 'B', 'C', 'D'],
                        y=['A', 'B', 'C', 'D'],
                        color_continuous_scale='RdYlGn',
                        title=f'Transition Matrix: {prev_col.replace("segment_", "").replace("_", "/")} → {curr_col.replace("segment_", "").replace("_", "/")}',
                        text_auto='.1f'
                    )
                    fig_heat.update_layout(height=400)
                    st.plotly_chart(fig_heat, use_container_width=True)
                    
                    # Retention rate
                    retention_data = con.execute(f"""
                        SELECT 
                            COUNT(*) as retained,
                            ROUND(COUNT(*) * 100.0 / (
                                SELECT COUNT(*) FROM user_profiles 
                                WHERE {prev_col} IS NOT NULL AND {curr_col} IS NOT NULL
                            ), 1) as retention_pct
                        FROM user_profiles
                        WHERE {prev_col} = {curr_col}
                            AND {prev_col} IS NOT NULL AND {curr_col} IS NOT NULL
                    """).df()
                    
                    total_tracked = con.execute(f"""
                        SELECT COUNT(*) as cnt FROM user_profiles
                        WHERE {prev_col} IS NOT NULL AND {curr_col} IS NOT NULL
                    """).df()['cnt'].iloc[0]
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Users Tracked", f"{total_tracked:,}")
                    col2.metric("Retained Segment", f"{retention_data['retained'].iloc[0]:,}")
                    col3.metric("Retention Rate", f"{retention_data['retention_pct'].iloc[0]}%")
    
    with tab3:
        st.markdown("### 🔍 User Lookup & Batch Analysis")
        
        # Search by segment
        st.markdown("#### Filter by Segment")
        
        segment_options = ['All'] + sorted(stats_df['segment'].tolist())
        selected_seg = st.selectbox(
            "Select Segment to View Users:",
            segment_options,
            index=0
        )
        
        # Get count for selected segment
        con = get_db_connection()
        if selected_seg == 'All':
            count_query = f"SELECT COUNT(*) as cnt FROM user_profiles WHERE {selected_period} IS NOT NULL"
        else:
            count_query = f"SELECT COUNT(*) as cnt FROM user_profiles WHERE {selected_period} = '{selected_seg}'"
        
        filtered_count = con.execute(count_query).df()['cnt'].iloc[0]
        
        st.markdown(f"**Found {filtered_count:,} users**")
        
        # Pagination controls
        items_per_page = st.selectbox("Items per page:", [50, 100, 250, 500], index=1)
        
        total_pages = (filtered_count + items_per_page - 1) // items_per_page
        
        if total_pages > 1:
            page = st.number_input(
                f"Page (1-{total_pages}):",
                min_value=1,
                max_value=total_pages,
                value=1,
                step=1
            )
        else:
            page = 1
        
        # Load paginated data
        offset = (page - 1) * items_per_page
        
        if selected_seg == 'All':
            query = f"""
                SELECT * FROM user_profiles 
                WHERE {selected_period} IS NOT NULL
                ORDER BY user_id
                LIMIT {items_per_page} OFFSET {offset}
            """
        else:
            query = f"""
                SELECT * FROM user_profiles 
                WHERE {selected_period} = '{selected_seg}'
                ORDER BY user_id
                LIMIT {items_per_page} OFFSET {offset}
            """
        
        filtered_df = con.execute(query).df()
        
        # Display table
        display_cols = ['user_id'] + segment_cols
        available_cols = [col for col in display_cols if col in filtered_df.columns]
        
        st.dataframe(
            filtered_df[available_cols],
            use_container_width=True,
            hide_index=True
        )
        
        # Navigation info
        if total_pages > 1:
            st.info(f"📄 Showing page {page} of {total_pages} ({offset + 1} to {min(offset + items_per_page, filtered_count)} of {filtered_count:,} users)")
        
        # Export option
        st.markdown("#### 📥 Export Data")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            max_export = st.number_input(
                "Maximum rows to export:",
                min_value=100,
                max_value=min(100000, filtered_count),
                value=min(10000, filtered_count),
                step=1000,
                help="Large exports may take time. Consider filtering first."
            )
        
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔄 Generate Export"):
                with st.spinner(f"Generating export ({max_export:,} rows)..."):
                    if selected_seg == 'All':
                        export_query = f"SELECT * FROM user_profiles WHERE {selected_period} IS NOT NULL LIMIT {max_export}"
                    else:
                        export_query = f"SELECT * FROM user_profiles WHERE {selected_period} = '{selected_seg}' LIMIT {max_export}"
                    
                    export_df = con.execute(export_query).df()
                    csv = export_df[available_cols].to_csv(index=False)
                    
                    st.download_button(
                        label=f"💾 Download CSV ({len(export_df):,} rows)",
                        data=csv,
                        file_name=f"users_segment_{selected_seg}_{selected_period}.csv",
                        mime="text/csv"
                    )

if __name__ == "__main__":
    main()
