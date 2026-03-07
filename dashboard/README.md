# 👥 CRM Dashboard - User Segmentation Analysis

Interactive Streamlit dashboard for visualizing and analyzing user segmentation clusters from the AMAZING e-commerce platform.

## Features

### ⚡ Performance Optimized for Large Datasets
- **Smart Sampling**: Automatically uses stratified sampling for datasets > 10K users
- **Lazy Loading**: Only loads data when needed, not all 300K+ users at once
- **DuckDB Aggregations**: Performs calculations in database instead of loading to memory
- **Pagination**: Browse large result sets efficiently with configurable page sizes
- **Caching**: 5-minute cache for expensive queries

### 🎯 Interactive Cluster Visualization
- **Network/Scatter Plot**: Visual representation of user segments (A, B, C, D)
- **Color-coded clusters**: 
  - 🟢 Green (A): High-Value Customers
  - 🔵 Blue (B): Engaged Users  
  - 🟠 Orange (C): Moderate Activity
  - 🔴 Red (D): Low Engagement
- **Interactive selection**: Click on any user to see detailed profile

### 📊 Analytics Dashboard
- **Segment Distribution**: Pie and bar charts showing user distribution across segments
- **Temporal Evolution**: Track how segment populations change over time
- **Transition Matrix**: Heatmap showing user movement between segments across periods
- **Retention Metrics**: Calculate segment stability and user retention rates

### 🔍 User Lookup
- **Individual User Profiles**: Detailed view of any user's data
- **Segment Evolution Timeline**: Visualize how a user's segment changes over time
- **Batch Filtering**: Filter and export users by segment
- **CSV Export**: Download filtered user lists

## Installation

### Prerequisites
- Python 3.8+
- Conda environment (recommended)
- DuckDB database with `user_profiles` table

### Setup

1. **Install dependencies**:
```bash
cd dashboard
pip install -r requirements.txt
```

Or with conda:
```bash
conda install streamlit duckdb pandas plotly numpy
```

2. **Ensure data is available**:
   - Run the `interpret_clusters.ipynb` notebook first to create the `user_profiles` table
   - Database location: `../amazing.duckdb`

## Usage

### Running the Dashboard

From the `dashboard/` directory:

```bash
streamlit run crm_dashboard.py
```

Or from the project root:

```bash
streamlit run dashboard/crm_dashboard.py
```

The dashboard will open in your browser at `http://localhost:8501`

### Navigation

**Tab 1: Cluster Visualization**
- View all users plotted by segment
- Select period from sidebar
- Click on points or use dropdown to select users
- View detailed user profile below the chart

**Tab 2: Analytics**
- Distribution charts (pie + bar)
- Temporal evolution line chart (if multiple periods available)
- Transition matrix heatmap showing segment changes
- Retention metrics

**Tab 3: User Lookup**
- Filter users by segment
- Browse user list (max 100 displayed)
- Export filtered users as CSV

### Sidebar Controls
- **Period Selection**: Choose which month/year to analyze
- **Visualization Settings**: 
  - **Sample Size Slider**: Control how many users to display (1K - 20K)
  - **Segment Filter**: Focus visualization on specific segment
- **Quick Stats**: Summary of total users and available periods
- **Segment Breakdown**: Table showing user count per segment

## Performance Tuning

### For Large Datasets (100K+ users)

The dashboard is optimized for datasets with hundreds of thousands of users:

**Automatic Optimizations**:
- Stratified sampling ensures representative distribution
- DuckDB performs aggregations in-database (faster than pandas)
- Queries use indexes and LIMIT clauses
- Caching reduces repeated database hits

**Manual Controls**:
- **Sample Size Slider**: Reduce for faster rendering (recommended: 5K-10K for 300K+ users)
- **Segment Filter**: Filter to specific segment before visualization
- **Pagination**: Use in User Lookup tab to browse large results

**Performance Tips**:
```python
# For 300K users:
- Sample size: 5,000-10,000 (good balance of speed/representation)
- Filter by segment: Reduces dataset by ~75% immediately
- Export limit: Max 50K rows at a time for CSV generation
```

**Expected Performance**:
- Initial load: 2-5 seconds
- Visualization: 1-3 seconds (with 10K sample)
- Analytics: 5-10 seconds (aggregates all data)
- User lookup: < 1 second (paginated)

## Data Structure

### Required Database Table: `user_profiles`

Expected columns:
- `user_id`: Unique user identifier
- `segment_MM_YYYY`: Segment code (A/B/C/D) for each period
  - Example: `segment_11_2019`, `segment_12_2019`

### Segment Codes

| Code | Label | Description |
|------|-------|-------------|
| A | 🌟 High-Value Customers | Top purchasers, high engagement |
| B | 💪 Engaged Users | Frequent activity, regular purchases |
| C | 👀 Moderate Activity | Browsers and occasional buyers |
| D | 😴 Low Engagement | Minimal activity |

## Features Detail

### Interactive User Profile

When selecting a user, you'll see:
- **Current Segment**: Latest period classification
- **Segment Evolution Chart**: Visual timeline of segment changes
- **Stability Metric**: Percentage of periods where segment remained unchanged
- **Number of Changes**: Total segment transitions
- **Raw Data**: Full JSON view of user record

### Temporal Analysis

With multiple periods available:
- **Evolution Line Chart**: Track segment population changes over time
- **Transition Matrix**: Percentage-based heatmap showing:
  - Rows: Previous period segment
  - Cols: Current period segment
  - Values: % of users who transitioned
- **Retention Rate**: % of users who stayed in same segment

### Performance

- **Caching**: Data cached for 5 minutes to improve performance
- **Read-only DB**: Safe concurrent access
- **Optimized queries**: Efficient DuckDB queries for large datasets

## Troubleshooting

### "No user_profiles table found"
→ Run `ml_ia/models/clustering/interpret_clusters.ipynb` first to create the table

### Dashboard won't start
→ Check that all requirements are installed: `pip install -r requirements.txt`

### No segment data visible
→ Ensure `interpret_clusters.ipynb` processed at least one monthly segment table

### Database connection error
→ Verify `amazing.duckdb` exists in parent directory: `../amazing.duckdb`

### Dashboard is slow with large dataset
→ **Solutions**:
1. Reduce sample size slider (sidebar) to 5,000-10,000
2. Use segment filter to view one segment at a time
3. Check cache is enabled (`@st.cache_data` decorators)
4. Avoid exporting > 50K rows at once

### Out of memory error
→ **Causes**: Trying to load all 300K users at once
→ **Solutions**:
1. Restart dashboard (clears cache)
2. Reduce sample size to minimum (1,000)
3. Use segment filter before visualization
4. Increase system RAM or use swap space

### Visualization not showing all users
→ **This is expected!** Dashboard uses sampling for datasets > 10K
→ All analytics and stats use full dataset, only visualization is sampled
→ Adjust sample size slider to show more/fewer points

## Development

### File Structure
```
dashboard/
├── crm_dashboard.py      # Main Streamlit application
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

### Customization

**Change color scheme**: Modify `color_map` dictionary in functions:
- `create_cluster_network_viz()`
- `create_segment_distribution()`

**Adjust cache duration**: Change `ttl` parameter in `@st.cache_data(ttl=300)`

**Add new metrics**: Extend `get_segment_stats()` function

## Related Files

- **Data Generation**: `ml_ia/models/clustering/interpret_clusters.ipynb`
- **Clustering Models**: `ml_ia/models/clustering/clustering_kmeans_goat.ipynb`
- **Database**: `amazing.duckdb`

## Contributing

When adding features:
1. Update this README
2. Add new dependencies to `requirements.txt`
3. Use caching (`@st.cache_data`) for expensive operations
4. Follow existing code style and structure

## Version

- Streamlit: 1.28+
- DuckDB: 0.9+
- Python: 3.8+

Created: February 2026
