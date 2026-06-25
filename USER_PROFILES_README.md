# User Profiles CRM Dashboard

A Streamlit-based CRM interface for visualizing and analyzing user segmentation and RFM groups.

## Features

✨ **Key Capabilities:**
- **📊 RFM Overview**: View distribution of customers across RFM groups for each month
- **👤 Top Users Analysis**: Click on any RFM group to see the top 5 users and their details
- **🎯 Cluster View**: Interactive cluster browser with user avatars and product images
- **📦 Product History**: View purchased products from the "articles" column for each user
- **📈 Dynamic Data Loading**: Automatically discovers and loads all `user_segment_*` tables from the database
- **📋 Data Inspector**: Explore raw data and download as CSV

## Prerequisites

- Python 3.8+
- PostgreSQL database with `user_segment_*` tables accessible
- Database credentials configured

## Installation

1. Install the required dependencies:

```bash
pip install -r requirements_streamlit.txt
```

The following packages are included:
- **streamlit**: Dashboard framework
- **pandas**: Data manipulation
- **sqlalchemy**: Database ORM
- **psycopg2-binary**: PostgreSQL driver
- **plotly**: Interactive charts
- **pillow**: Image processing
- **requests**: HTTP requests for image loading

## Running the Dashboard

From the project root directory, run:

```bash
streamlit run user_profiles.py
```

The dashboard will open in your default web browser at `http://localhost:8501`

## Database Configuration

The dashboard connects to the PostgreSQL database with the following configuration:

```python
DB_CONFIG = {
    "host": "172.18.0.1",
    "database": "postgres",
    "user": "postgres",
    "password": "postgres",
    "port": 5441,
}
```

## Expected Table Structure

The dashboard expects tables named `user_segment_*` with columns including:

- **User ID Column**: Any column containing 'id' or 'user' in the name
- **RFM Group Column**: Any column containing 'rfm' or 'segment' in the name
- **Articles Column**: Column(s) containing product/article information
- **Optional RFM Metrics**: Columns for Recency, Frequency, or Monetary values
- **Optional Value Columns**: For ranking users (revenue, amount, etc.)

### Example Table Schema:

```
user_id | rfm_segment | articles | recency | frequency | monetary_value
--------|-------------|----------|---------|-----------|----------------
123     | Champions   | [....]   | 5       | 45        | 5000
456     | At Risk     | [....]   | 60      | 3         | 150
```

## Usage

### 1. Select Month/Table
Use the sidebar dropdown to select which month's segmentation data to view.

### 2. View RFM Distribution
The **RFM Overview** tab shows:
- Count of users in each RFM group
- Visual bar chart of group distribution

### 3. Analyze Top Users
The **Top Users by RFM** tab allows you to:
- Select an RFM group
- View top 5 users ranked by value/activity
- Expand each user to see:
  - User attributes and metrics
  - RFM scores (Recency, Frequency, Monetary)
  - Purchased products/articles

### 4. Explore Data
The **Data Inspector** tab provides:
- Column information and data types
- Data quality metrics
- Data preview
- CSV export functionality

## Navigation

- **Sidebar**: Month/table selection and quick stats
- **Tabs**:
  - 📈 **RFM Overview**: Distribution charts
  - 👤 **Top Users**: Detailed user analysis
  - 🎯 **Cluster View**: Visual cluster browser with avatars and product images
  - 📋 **Data Inspector**: Raw data exploration

## Features in Detail

### RFM Overview
Displays the distribution of customers across different RFM segments with:
- Individual metrics for each group
- Interactive bar chart visualization

### Top Users by RFM
For each selected RFM group:
- Shows total user count
- Lists top 5 users with expandable details
- User attributes and RFM metrics
- Product/article purchase history

### Cluster View
Interactive visualization of all users in a selected RFM group:
- **User Cards**: Display avatars and key metrics in a grid layout
- **User Selection**: Click to view detailed information for any user
- **Product Gallery**: Browse purchased products with thumbnail images
- **Visual Design**: Professional card-based UI with avatars powered by DiceBear API
- **Product Images**: Auto-generated product thumbnails for quick visual scanning

### Data Quality
- Null value counts per column
- Non-null value counts
- Data type information
- Full data preview and download options

## Troubleshooting

### Connection Failed
- Verify PostgreSQL server is running at `172.18.0.1:5441`
- Check credentials in the DB_CONFIG dictionary
- Ensure the database and tables exist

### No Tables Found
- Verify tables are named with `user_segment_` prefix
- Check database user has SELECT permissions
- Run a manual query to confirm table existence

### Missing Columns
The dashboard auto-detects columns:
- **ID columns**: Must contain 'id' or 'user' in name
- **RFM columns**: Must contain 'rfm' or 'segment' in name
- **Articles columns**: Can have any name containing 'article'

If columns aren't detected, check the **Data Inspector** tab to see actual column names.

## Performance Notes

- Data is cached for 10 minutes (tables) / 1 hour (structure)
- Clear cache via Streamlit menu if data has been updated
- For large tables (>100K users), consider adding filters

## Development

To modify styling or add features:
1. Edit `user_profiles.py`
2. Streamlit will auto-reload on save
3. Use the R key to clear cache if needed

## Support

For issues or questions, check:
- Database connectivity
- Table structure matches expected format
- Streamlit version compatibility
- Python version (3.8+)
