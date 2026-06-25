import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, inspect
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import hashlib
from PIL import Image
from io import BytesIO
import requests
import os

# Database configuration
DB_CONFIG = {
    "host": "172.18.0.1",
    "database": "postgres",
    "user": "postgres",
    "password": "postgres",
    "port": 5441,
}

# Row limit for table requests (for plotting performance)
ROWS_LIMIT = int(os.getenv("ROWS_LIMIT", "1000"))

# Page configuration
st.set_page_config(
    page_title="User Profiles CRM",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("👥 User Profiles CRM Dashboard")
st.markdown("---")

# Initialize session state for user navigation
if "selected_user_id" not in st.session_state:
    st.session_state.selected_user_id = None
if "selected_user_rfm_group" not in st.session_state:
    st.session_state.selected_user_rfm_group = None
if "view_user_details" not in st.session_state:
    st.session_state.view_user_details = False

# Connection cache
@st.cache_resource
def get_db_engine():
    """Create and cache SQLAlchemy database engine"""
    try:
        engine = create_engine(
            f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
        )
        return engine
    except Exception as e:
        st.error(f"Failed to connect to database: {e}")
        return None

# Fetch available tables
@st.cache_data(ttl=3600)
def get_user_segment_tables():
    """Get all tables starting with 'user_segment_'"""
    engine = get_db_engine()
    if not engine:
        return []
    
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        user_segment_tables = [t for t in tables if t.startswith('user_segment_')]
        return sorted(user_segment_tables)
    except Exception as e:
        st.error(f"Error fetching tables: {e}")
        return []

# Load data from selected table
@st.cache_data(ttl=600)
def load_segment_table(table_name):
    """Load data from a specific user_segment table with row limit"""
    engine = get_db_engine()
    if not engine:
        return None
    
    try:
        # Load with row limit for performance
        # Quote table name to handle special characters (hyphens, etc)
        query = f'SELECT * FROM "{table_name}" LIMIT {ROWS_LIMIT}'
        df = pd.read_sql(query, engine)
        return df
    except Exception as e:
        st.error(f"Error loading table {table_name}: {e}")
        return None

# Get RFM groups from table
def get_rfm_info(df):
    """Extract RFM group information"""
    if df is None or df.empty:
        return None
    
    # Check for RFM-related columns
    rfm_columns = [col for col in df.columns if 'rfm' in col.lower() or 'segment' in col.lower()]
    
    if not rfm_columns:
        return None
    
    # Use the first RFM-like column
    rfm_col = rfm_columns[0]
    rfm_stats = df[rfm_col].value_counts().reset_index()
    rfm_stats.columns = ['RFM_Group', 'Count']
    
    return rfm_stats, rfm_col

# Get top users from RFM group
def get_top_users(df, rfm_col, rfm_group, limit=5):
    """Get top users from a specific RFM group"""
    filtered_df = df[df[rfm_col] == rfm_group]
    
    # Try to identify user ID and value columns
    id_cols = ['user_id']
    id_col = "user_id"
    value_cols = [col for col in df.columns if 'value' in col.lower() or 'revenue' in col.lower() or 'amount' in col.lower()]
    
    if not id_cols:
        id_col = df.columns[0]  # Use first column as fallback
    else:
        id_col = id_cols[0]
    
    if value_cols:
        sorted_df = filtered_df.sort_values(value_cols[0], ascending=False)
    else:
        sorted_df = filtered_df
    
    return sorted_df.head(limit), id_col

# Generate user avatar URL
def get_user_avatar(user_id, size=200):
    """Generate a consistent user avatar URL based on their ID"""
    # Using DiceBear API for deterministic avatars
    hash_val = hashlib.md5(str(user_id).encode()).hexdigest()
    return f"https://api.dicebear.com/7.x/avataaars/svg?seed={user_id}&size={size}"

# Generate product image URL
def get_product_image(product_name, size=200):
    """Generate a consistent product image URL using DiceBear icons"""
    # Use DiceBear icons API for product thumbnails
    return f"https://api.dicebear.com/7.x/icons/svg?seed={product_name}&size={size}&scale=80"

# Create RFM Radar plot
def create_rfm_radar(user_row):
    """Create a radar chart for RFM metrics"""
    # Extract RFM metrics
    metrics = {}
    
    metric_patterns = {
        'Recency': 'recency',
        'Frequency': 'frequency',
        'Monetary': 'monetary'
    }
    
    for display_name, pattern in metric_patterns.items():
        for col_name, value in user_row.items():
            if pattern.lower() in col_name.lower():
                metrics[display_name] = float(value) if value else 0
                break
    
    if not metrics or len(metrics) < 2:
        return None
    
    # Normalize metrics to 0-100 scale for better visualization
    max_recency = 100  # days
    max_frequency = 50  # purchases
    max_monetary = 5000  # currency
    
    normalized = {}
    if 'Recency' in metrics:
        # Higher recency (older) = lower score
        recency_score = max(0, 100 - (metrics['Recency'] / max_recency * 100))
        normalized['Recency'] = min(100, recency_score)
    
    if 'Frequency' in metrics:
        normalized['Frequency'] = min(100, (metrics['Frequency'] / max_frequency * 100))
    
    if 'Monetary' in metrics:
        normalized['Monetary'] = min(100, (metrics['Monetary'] / max_monetary * 100))
    
    # Create radar chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=[normalized.get('Recency', 0), normalized.get('Frequency', 0), normalized.get('Monetary', 0)],
        theta=['Recency', 'Frequency', 'Monetary'],
        fill='toself',
        name='RFM Score',
        line=dict(color='#1f77b4'),
        fillcolor='rgba(31, 119, 180, 0.3)'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )
        ),
        height=400,
        title="RFM Metrics Score",
        showlegend=False
    )
    
    return fig

# Parse table name to extract components
def parse_table_name(table_name):
    """
    Parse table name like: user_segment_YYYY-MonthName-10pct_model_name
    Examples: 
        - user_segment_2019-Dec-10pct_kmeans → ('2019-Dec', 'kmeans')
        - user_segment_2020-Jan-10pct_agglomerative → ('2020-Jan', 'agglomerative')
    Returns: (date_string, model_name) or (None, None)
    """
    try:
        # Remove user_segment_ prefix
        remainder = table_name.replace('user_segment_', '')
        
        # Look for the -10pct_ separator pattern
        if '-10pct_' in remainder:
            parts = remainder.split('-10pct_')
            if len(parts) == 2:
                date_part = parts[0]  # e.g., "2019-Dec"
                model_name = parts[1]  # e.g., "kmeans"
                return date_part, model_name
    except Exception as e:
        pass
    return None, None

# Get available models
@st.cache_data(ttl=3600)
def get_available_models():
    """Get all available models from user_segment tables"""
    tables = get_user_segment_tables()
    models = set()
    
    for table in tables:
        _, model = parse_table_name(table)
        if model:
            models.add(model)
    
    return sorted(list(models))

# Get tables for a specific model
@st.cache_data(ttl=3600)
def get_tables_for_model(model_name):
    """Get all tables for a specific model, ordered by date"""
    tables = get_user_segment_tables()
    model_tables = []
    
    for table in tables:
        date_part, model = parse_table_name(table)
        if model == model_name and date_part:
            model_tables.append((date_part, table))
    
    # Sort by date
    model_tables.sort(key=lambda x: x[0], reverse=True)
    return model_tables

# Get detailed parsing info for all tables
@st.cache_data(ttl=3600)
def get_parsing_info():
    """Get detailed information about all parsed tables"""
    tables = get_user_segment_tables()
    
    parsed_info = {
        'models': {},
        'dates': {},
        'unparsed': []
    }
    
    for table in tables:
        date_part, model = parse_table_name(table)
        
        if date_part and model:
            # Track by model
            if model not in parsed_info['models']:
                parsed_info['models'][model] = []
            parsed_info['models'][model].append({'date': date_part, 'table': table})
            
            # Track by date
            if date_part not in parsed_info['dates']:
                parsed_info['dates'][date_part] = []
            parsed_info['dates'][date_part].append({'model': model, 'table': table})
        else:
            parsed_info['unparsed'].append(table)
    
    return parsed_info

# Main dashboard
def main():
    # Sidebar for table selection
    st.sidebar.header("📊 Controls")
    
    tables = get_user_segment_tables()
    
    if not tables:
        st.warning("No user_segment_* tables found in the database.")
        return
    
    # Display row limit setting
    st.sidebar.info(f"📊 **Row Limit:** {ROWS_LIMIT:,} rows/table\n\n*(Set via `ROWS_LIMIT` env var)*")
    
    # Get parsing information
    parsing_info = get_parsing_info()
    
    # Display parsing info in sidebar
    with st.sidebar.expander("🔍 Database Overview", expanded=False):
        st.write(f"**Total Tables:** {len(tables)}")
        st.write(f"**Successfully Parsed:** {sum(len(v) for v in parsing_info['models'].values())}")
        st.write(f"**Unparsed Tables:** {len(parsing_info['unparsed'])}")
        
        # Show models breakdown
        if parsing_info['models']:
            st.write("**Models Found:**")
            for model in sorted(parsing_info['models'].keys()):
                count = len(parsing_info['models'][model])
                st.write(f"  • `{model}` — {count} month(s)")
        
        # Show dates breakdown
        if parsing_info['dates']:
            st.write("**Dates Found:**")
            for date in sorted(parsing_info['dates'].keys(), reverse=True):
                count = len(parsing_info['dates'][date])
                st.write(f"  • `{date}` — {count} model(s)")
        
        # Show unparsed if any
        if parsing_info['unparsed']:
            st.warning(f"**⚠️ Unparsed ({len(parsing_info['unparsed'])}):**")
            for table in parsing_info['unparsed']:
                st.code(table, language="text")
    
    # Get available models
    models = get_available_models()
    
    if not models:
        st.warning("No models found. Available tables cannot be parsed.")
        return
    
    # Model selector
    selected_model = st.sidebar.selectbox(
        "🤖 Select Model:",
        models,
        key="main_model_selector"
    )
    
    # Get available months for selected model
    model_tables = get_tables_for_model(selected_model)
    month_options = [date_part for date_part, _ in model_tables]
    
    if not month_options:
        st.warning(f"No data available for model: {selected_model}")
        return
    
    # Month selector
    selected_month = st.sidebar.selectbox(
        "📅 Select Month:",
        month_options,
        index=0,  # Default to most recent month
        key="main_month_selector"
    )
    
    # Get the table name from model and month
    selected_table = next(table for date, table in model_tables if date == selected_month)
    
    st.sidebar.markdown("---")
    
    # Display selected configuration
    st.sidebar.info(f"📊 **Model:** {selected_model}\n\n📅 **Month:** {selected_month}")
    
    # Load data
    with st.spinner(f"Loading {selected_table}..."):
        df = load_segment_table(selected_table)
    
    if df is None or df.empty:
        st.error(f"Could not load data from {selected_table}")
        return
    
    # Display table info
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Users", len(df))
    with col2:
        st.metric("Total Columns", len(df.columns))
    with col3:
        st.metric("Month", selected_table.replace("user_segment_", "").upper())
    
    st.markdown("---")
    
    # Get RFM info
    rfm_info = get_rfm_info(df)
    
    if rfm_info is None:
        st.warning("No RFM group column found in the data")
        st.write("Available columns:", df.columns.tolist())
        return
    
    rfm_stats, rfm_col = rfm_info
    
    # Create tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 RFM Overview", "👤 Top Users by RFM", "🎯 Cluster View", "📋 Data Inspector", "🔧 Parsing Debug"])
    
    with tab1:
        st.subheader("RFM Groups Distribution")
        
        # Display RFM stats in columns
        cols = st.columns(len(rfm_stats))
        for idx, (group, count) in enumerate(zip(rfm_stats['RFM_Group'], rfm_stats['Count'])):
            with cols[idx % len(cols)]:
                st.metric(f"Group: {group}", count)
        
        # Visualization
        fig = px.bar(
            rfm_stats,
            x='RFM_Group',
            y='Count',
            title=f"RFM Groups Distribution - {selected_table.replace('user_segment_', '').upper()}",
            color='Count',
            color_continuous_scale='Viridis'
        )
        fig.update_layout(height=400, xaxis_title="RFM Group", yaxis_title="Number of Users")
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("🏆 Top 5 Users by RFM Group")
        
        # Check if viewing a specific user from cluster details
        viewing_specific_user = st.session_state.view_user_details
        
        if viewing_specific_user and st.session_state.selected_user_id:
            # Display back button
            if st.button("← Back to Cluster Details"):
                st.session_state.view_user_details = False
                st.session_state.selected_user_id = None
                st.session_state.selected_user_rfm_group = None
                st.rerun()
            
            st.markdown(f"### Viewing Details for User: `{st.session_state.selected_user_id}`")
            
            # Find the user in the dataframe
            user_row = df[df["user_id"] == st.session_state.selected_user_id]
            
            if user_row.empty:
                st.warning(f"User {st.session_state.selected_user_id} not found in current dataset")
            else:
                user_row = user_row.iloc[0]
                user_id = st.session_state.selected_user_id
                
                # User profile header with avatar
                profile_cols = st.columns([1, 3])
                
                with profile_cols[0]:
                    try:
                        avatar_url = get_user_avatar(user_id, size=150)
                        st.markdown(f"<div style='text-align: center;'><img src='{avatar_url}' width='120' style='border-radius: 50%; border: 3px solid #1f77b4;'></div>", unsafe_allow_html=True)
                    except:
                        st.markdown(f"<div style='text-align: center; padding: 20px; background-color: #f0f0f0; border-radius: 50%; width: 120px; height: 120px; display: flex; align-items: center; justify-content: center;'><strong style='font-size: 40px;'>👤</strong></div>", unsafe_allow_html=True)
                
                with profile_cols[1]:
                    st.markdown(f"### {user_id}")
                    
                    # Get user data
                    user_data = user_row.to_dict()
                    
                    # Display label from 'label' column if available
                    if 'label' in user_row.index:
                        label_value = user_row['label']
                        st.markdown(f"**RFM Group:** `{label_value}`")
                    
                    # Display cluster label if available
                    segment_cols = [col for col in user_row.index if 'segment' in col.lower() or 'cluster' in col.lower()]
                    if segment_cols:
                        cluster_label = user_row[segment_cols[0]]
                        st.markdown(f"**Cluster:** `{cluster_label}`")
                    
                    # Display only the requested metrics
                    metrics_to_show = [
                        ('rfm', 'RFM Score'),
                        ('recency', 'Recency'),
                        ('frequency', 'Frequency'),
                        ('monetary', 'Monetary'),
                        ('average_basket', 'Avg Basket'),
                        ('number_of_purchases', 'Total Purchases'),
                        ('label', 'Groupe RFM')
                    ]
                    
                    metrics_cols = st.columns(3)
                    metric_idx = 0
                    
                    for key_pattern, display_name in metrics_to_show:
                        # Find matching column
                        matching_col = None
                        for col_name, value in user_data.items():
                            if key_pattern.lower() in col_name.lower():
                                matching_col = col_name
                                value_to_display = value
                                break
                        
                        if matching_col:
                            with metrics_cols[metric_idx % 3]:
                                st.metric(display_name, value_to_display)
                            metric_idx += 1
                
                st.divider()
                
                # Display RFM Radar plot
                radar_fig = create_rfm_radar(user_row)
                if radar_fig:
                    st.plotly_chart(radar_fig, use_container_width=True, key=f"radar_detail_{user_id}")
                
                st.divider()
                
                # Display articles/products with thumbnails
                articles_col = [col for col in user_row.index if 'article' in col.lower()]
                
                if articles_col:
                    st.write("**📦 Purchased Products:**")
                    
                    for col in articles_col:
                        articles_value = user_row[col]
                        
                        if articles_value:
                            # Parse articles from format: {product|timestamp,product|timestamp,...}
                            articles_list = []
                            
                            if isinstance(articles_value, str):
                                # Remove outer braces
                                cleaned = str(articles_value).strip('{}[] ')
                                
                                if cleaned:
                                    # Split by comma
                                    items = cleaned.split(',')
                                    
                                    for item in items:
                                        item = item.strip()
                                        if item:
                                            # Extract product name (before the | separator)
                                            if '|' in item:
                                                product_name = item.split('|')[0].strip()
                                            else:
                                                product_name = item
                                            
                                            # Only add if not empty or 'unknown'
                                            if product_name and product_name.lower() != 'unknown':
                                                articles_list.append(product_name)
                            else:
                                articles_list = [str(articles_value)]
                            
                            # Remove duplicates while preserving order
                            seen = set()
                            articles_list = [x for x in articles_list if not (x in seen or seen.add(x))]
                            
                            if articles_list:
                                # Display products in a grid
                                products_per_row = 4
                                for i in range(0, len(articles_list), products_per_row):
                                    product_cols = st.columns(products_per_row)
                                    
                                    for col_idx, product in enumerate(articles_list[i:i+products_per_row]):
                                        with product_cols[col_idx]:
                                            with st.container(border=True):
                                                try:
                                                    # Generate random product image
                                                    product_image = get_product_image(product, size=120)
                                                    st.markdown(f"<div style='text-align: center;'><img src='{product_image}' width='100' style='border-radius: 8px;'></div>", unsafe_allow_html=True)
                                                except:
                                                    st.markdown(f"<div style='text-align: center; padding: 30px; background-color: #e0e0e0; border-radius: 8px;'>📦</div>", unsafe_allow_html=True)
                                                
                                                st.markdown(f"<p style='text-align: center; font-size: 12px; font-weight: bold; margin: 5px 0;'>{product.split('.')[-1][:15]}</p>", unsafe_allow_html=True)
        
        else:
            # Original display logic for browsing all users by RFM group
            # Select RFM group
            selected_group = st.selectbox(
                "Select RFM Group:",
                sorted(rfm_stats['RFM_Group'].unique()),
                key="group_selector"
            )
            
            st.markdown(f"### RFM Group: `{selected_group}`")
            
            # Get top users
            top_users_df, id_col = get_top_users(df, rfm_col, selected_group)
            
            if top_users_df.empty:
                st.info("No users found in this RFM group.")
            else:
                st.metric("Users in Group", len(df[df[rfm_col] == selected_group]))
                
                # Display user details
                for idx, (_, user_row) in enumerate(top_users_df.iterrows(), 1):
                    user_id = user_row.get(id_col, f"User_{idx}")
                    
                    with st.expander(f"👤 User #{idx} - {user_id}", expanded=idx==1):
                        # User profile header with avatar
                        profile_cols = st.columns([1, 3])
                        
                        with profile_cols[0]:
                            try:
                                avatar_url = get_user_avatar(user_id, size=150)
                                st.markdown(f"<div style='text-align: center;'><img src='{avatar_url}' width='120' style='border-radius: 50%; border: 3px solid #1f77b4;'></div>", unsafe_allow_html=True)
                            except:
                                st.markdown(f"<div style='text-align: center; padding: 20px; background-color: #f0f0f0; border-radius: 50%; width: 120px; height: 120px; display: flex; align-items: center; justify-content: center;'><strong style='font-size: 40px;'>👤</strong></div>", unsafe_allow_html=True)
                        
                        with profile_cols[1]:
                            st.markdown(f"### {user_id}")
                            
                            # Get user data
                            user_data = user_row.to_dict()
                            
                            # Display label from 'label' column if available
                            if 'label' in user_row.index:
                                label_value = user_row['label']
                                st.markdown(f"**RFM Group:** `{label_value}`")
                            
                            # Display cluster label if available
                            segment_cols = [col for col in user_row.index if 'segment' in col.lower() or 'cluster' in col.lower()]
                            if segment_cols:
                                cluster_label = user_row[segment_cols[0]]
                                st.markdown(f"**Cluster:** `{cluster_label}`")
                            
                            # Display only the requested metrics
                            metrics_to_show = [
                                ('rfm', 'RFM Score'),
                                ('recency', 'Recency'),
                                ('frequency', 'Frequency'),
                                ('monetary', 'Monetary'),
                                ('average_basket', 'Avg Basket'),
                                ('total_purchases', 'Total Purchases')
                            ]
                            
                            metrics_cols = st.columns(3)
                            metric_idx = 0
                            
                            for key_pattern, display_name in metrics_to_show:
                                # Find matching column
                                matching_col = None
                                for col_name, value in user_data.items():
                                    if key_pattern.lower() in col_name.lower():
                                        matching_col = col_name
                                        value_to_display = value
                                        break
                                
                                if matching_col:
                                    with metrics_cols[metric_idx % 3]:
                                        st.metric(display_name, value_to_display)
                                    metric_idx += 1
                        
                        st.divider()
                        
                        # Display RFM Radar plot
                        radar_fig = create_rfm_radar(user_row)
                        if radar_fig:
                            st.plotly_chart(radar_fig, use_container_width=True, key=f"radar_expand_{idx}_{user_id}")
                        
                        st.divider()
                        
                        # Display articles/products with thumbnails
                        articles_col = [col for col in user_row.index if 'article' in col.lower()]
                        
                        if articles_col:
                            st.write("**📦 Purchased Products:**")
                            
                            for col in articles_col:
                                articles_value = user_row[col]
                                
                                if articles_value:
                                    # Parse articles from format: {product|timestamp,product|timestamp,...}
                                    articles_list = []
                                    
                                    if isinstance(articles_value, str):
                                        # Remove outer braces
                                        cleaned = str(articles_value).strip('{}[] ')
                                        
                                        if cleaned:
                                            # Split by comma
                                            items = cleaned.split(',')
                                            
                                            for item in items:
                                                item = item.strip()
                                                if item:
                                                    # Extract product name (before the | separator)
                                                    if '|' in item:
                                                        product_name = item.split('|')[0].strip()
                                                    else:
                                                        product_name = item
                                                    
                                                    # Only add if not empty or 'unknown'
                                                    if product_name and product_name.lower() != 'unknown':
                                                        articles_list.append(product_name)
                                    else:
                                        articles_list = [str(articles_value)]
                                    
                                    # Remove duplicates while preserving order
                                    seen = set()
                                    articles_list = [x for x in articles_list if not (x in seen or seen.add(x))]
                                    
                                    if articles_list:
                                        # Display products in a grid
                                        products_per_row = 4
                                        for i in range(0, len(articles_list), products_per_row):
                                            product_cols = st.columns(products_per_row)
                                            
                                            for col_idx, product in enumerate(articles_list[i:i+products_per_row]):
                                                with product_cols[col_idx]:
                                                    with st.container(border=True):
                                                        try:
                                                            # Generate random product image
                                                            product_image = get_product_image(product, size=120)
                                                            st.markdown(f"<div style='text-align: center;'><img src='{product_image}' width='100' style='border-radius: 8px;'></div>", unsafe_allow_html=True)
                                                        except:
                                                            st.markdown(f"<div style='text-align: center; padding: 30px; background-color: #e0e0e0; border-radius: 8px;'>📦</div>", unsafe_allow_html=True)
                                                        
                                                        st.markdown(f"<p style='text-align: center; font-size: 12px; font-weight: bold; margin: 5px 0;'>{product.split('.')[-1][:15]}</p>", unsafe_allow_html=True)
    
    with tab4:
        st.subheader("🎯 Cluster Progression by Month")
        
        # Get available models
        models = get_available_models()
        
        if not models:
            st.warning("No models found in the database")
        else:
            # Use the model selected in sidebar
            selected_model = st.session_state.get("main_model_selector", models[0])
            
            # Get tables for selected model
            model_tables = get_tables_for_model(selected_model)
            
            if not model_tables:
                st.warning(f"No tables found for model: {selected_model}")
            else:
                st.info(f"📊 Model: `{selected_model}` | Found {len(model_tables)} month(s)")
                
                # Display timeline of months
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Months", len(model_tables))
                with col2:
                    st.metric("Date Range", f"{model_tables[-1][0]} to {model_tables[0][0]}")
                with col3:
                    st.metric("Model", selected_model)
                
                st.markdown("---")
                
                # Create tabs for each month
                month_tabs = st.tabs([f"📅 {date}" for date, _ in model_tables])
                
                for tab_idx, (date_part, table_name) in enumerate(model_tables):
                    with month_tabs[tab_idx]:
                        st.markdown(f"### Month: {date_part}")
                        
                        # Load data for this month
                        with st.spinner(f"Loading data for {date_part}..."):
                            month_df = load_segment_table(table_name)
                        
                        if month_df is None or month_df.empty:
                            st.error(f"Could not load data for {date_part}")
                            continue
                        
                        # Get RFM info
                        rfm_info = get_rfm_info(month_df)
                        if rfm_info is None:
                            st.warning("No RFM group column found")
                            continue
                        
                        rfm_stats, rfm_col = rfm_info
                        
                        # Display month statistics
                        stat_cols = st.columns(4)
                        with stat_cols[0]:
                            st.metric("Total Users", len(month_df))
                        with stat_cols[1]:
                            st.metric("RFM Groups", len(rfm_stats))
                        with stat_cols[2]:
                            st.metric("Avg Group Size", f"{len(month_df) / len(rfm_stats):.0f}")
                        with stat_cols[3]:
                            st.metric("Table", table_name.replace("user_segment_", ""))
                        
                        # RFM distribution chart
                        fig = px.bar(
                            rfm_stats,
                            x='RFM_Group',
                            y='Count',
                            title=f"RFM Distribution - {date_part}",
                            color='Count',
                            color_continuous_scale='Blues'
                        )
                        fig.update_layout(height=350, xaxis_title="RFM Group", yaxis_title="Users")
                        st.plotly_chart(fig, use_container_width=True)
                        
                        st.markdown("---")
                        st.write("**📊 Cluster Details:**")
                        
                        # Select cluster for month
                        selected_cluster_month = st.selectbox(
                            "Select RFM Group:",
                            sorted(rfm_stats['RFM_Group'].unique()),
                            key=f"cluster_{date_part}"
                        )
                        
                        # Get users in cluster
                        cluster_users_df, id_col = get_top_users(month_df, rfm_col, selected_cluster_month, limit=None)
                        cluster_users_df = cluster_users_df.reset_index(drop=True)
                        
                        if cluster_users_df.empty:
                            st.info("No users found in this cluster.")
                        else:
                            # Display user avatars
                            st.write(f"**{len(cluster_users_df)} users in `{selected_cluster_month}` group:**")
                            
                            users_per_row = 5
                            user_columns = st.columns(users_per_row)
                            
                            for idx, (_, user_row) in enumerate(cluster_users_df.iterrows()):
                                col_idx = idx % users_per_row
                                
                                with user_columns[col_idx]:
                                    user_id = user_row.get(id_col, f"User_{idx}")
                                    
                                    with st.container(border=True):
                                        # User avatar
                                        try:
                                            avatar_url = get_user_avatar(user_id, size=150)
                                            st.markdown(f"<div style='text-align: center;'><img src='{avatar_url}' width='100' style='border-radius: 50%; border: 2px solid #1f77b4;'></div>", unsafe_allow_html=True)
                                        except:
                                            st.markdown(f"<div style='text-align: center; padding: 15px; background-color: #f0f0f0; border-radius: 50%; width: 100px; height: 100px; display: flex; align-items: center; justify-content: center;'><strong>👤</strong></div>", unsafe_allow_html=True)
                                        
                                        st.markdown(f"<p style='text-align: center; font-weight: bold; font-size: 13px;'>{user_id}</p>", unsafe_allow_html=True)
                                        
                                        # Value metric
                                        value_cols = [col for col in user_row.index if 'value' in col.lower() or 'revenue' in col.lower()]
                                        if value_cols:
                                            val = user_row[value_cols[0]]
                                            st.markdown(f"<p style='text-align: center; color: #2ca02c; font-weight: bold;'>💰 {val}</p>", unsafe_allow_html=True)
                                
                                if (idx + 1) % users_per_row == 0:
                                    user_columns = st.columns(users_per_row)
                            
                            # Show top users with details
                            st.markdown("---")
                            st.write("**🏆 Top 5 Users with Details:**")
                            
                            top_5 = cluster_users_df.head(5)
                            
                            for idx, (_, user_row) in enumerate(top_5.iterrows(), 1):
                                with st.expander(f"👤 User #{idx} - {user_row.get(id_col, 'N/A')}"):
                                    detail_cols = st.columns(2)
                                    
                                    with detail_cols[0]:
                                        st.write("**Attributes:**")
                                        for col in user_row.index:
                                            if 'article' not in col.lower():
                                                st.write(f"• {col}: `{user_row[col]}`")
                                    
                                    with detail_cols[1]:
                                        st.write("**Products:**")
                                        articles_cols = [col for col in user_row.index if 'article' in col.lower()]
                                        if articles_cols:
                                            for col in articles_cols:
                                                products = str(user_row[col]).split(',')
                                                for prod in products[:5]:
                                                    st.write(f"• {prod.strip()}")
                                        else:
                                            st.info("No products")
    
    with tab5:
        st.subheader("🔧 Parsing Debug Information")
        
        parsing_info = get_parsing_info()
        all_tables = get_user_segment_tables()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Tables", len(all_tables))
        with col2:
            st.metric("Successfully Parsed", sum(len(v) for v in parsing_info['models'].values()))
        with col3:
            st.metric("Unparsed Tables", len(parsing_info['unparsed']))
        
        st.markdown("---")
        
        # Show all models and their tables
        st.write("### 🤖 Models & Their Tables")
        for model in sorted(parsing_info['models'].keys()):
            with st.expander(f"**{model.upper()}** ({len(parsing_info['models'][model])} months)", expanded=False):
                model_data = []
                for item in sorted(parsing_info['models'][model], key=lambda x: x['date'], reverse=True):
                    model_data.append({
                        'Date': item['date'],
                        'Table Name': item['table']
                    })
                df_models = pd.DataFrame(model_data)
                st.dataframe(df_models, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Show all dates and their models
        st.write("### 📅 Dates & Their Models")
        for date in sorted(parsing_info['dates'].keys(), reverse=True):
            with st.expander(f"**{date}** ({len(parsing_info['dates'][date])} models)", expanded=False):
                date_data = []
                for item in sorted(parsing_info['dates'][date], key=lambda x: x['model']):
                    date_data.append({
                        'Model': item['model'],
                        'Table Name': item['table']
                    })
                df_dates = pd.DataFrame(date_data)
                st.dataframe(df_dates, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Show unparsed tables if any
        if parsing_info['unparsed']:
            st.write("### ⚠️ Unparsed Tables")
            st.warning(f"Found {len(parsing_info['unparsed'])} table(s) that couldn't be parsed:")
            for table in parsing_info['unparsed']:
                st.code(table, language="text")
        else:
            st.success("✅ All tables parsed successfully!")
    
    with tab3:
        st.subheader("📋 Data Inspector")
        
        # Show column info
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Column Information:**")
            col_info = pd.DataFrame({
                'Column': df.columns,
                'Type': [str(dtype) for dtype in df.dtypes],
                'Non-Null': [df[col].notna().sum() for col in df.columns],
                'Null': [df[col].isna().sum() for col in df.columns]
            })
            st.dataframe(col_info, use_container_width=True)
        
        with col2:
            st.write("**Data Sample:**")
            st.dataframe(df.head(10), use_container_width=True)
        
        st.divider()
        st.write("**🔍 Browse Users:**")
        
        # Create user browser
        browser_cols = st.columns(5)
        
        # Get top users overall
        top_overall = df.nlargest(20, [col for col in df.columns if 'monetary' in col.lower()][0] if any('monetary' in col.lower() for col in df.columns) else df.columns[0])
        
        for idx, (_, user_row) in enumerate(top_overall.iterrows()):
            col_idx = idx % 5
            if col_idx == 0 and idx > 0:
                browser_cols = st.columns(5)
            
            user_id = user_row.get(id_col, f"User_{idx}")
            
            with browser_cols[col_idx]:
                # Create clickable user card
                if st.button(f"👤 {str(user_id)[:12]}", key=f"user_btn_{user_id}", use_container_width=True):
                    st.session_state.selected_user_id = user_id
                    st.session_state.view_user_details = True
                    st.rerun()
        
        st.divider()
        
        # Raw data viewer
        if st.checkbox("Show Full Table Data"):
            st.dataframe(df, use_container_width=True, height=400)
        
        # Download options
        st.write("**Export Data:**")
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name=f"{selected_table}.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main()
