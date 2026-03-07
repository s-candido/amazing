# Quick Fix for Large Dataset (300K+ Users)

## Your dashboard is slow or crashing? Here's the fix:

### Step 1: Update the Dashboard
Make sure you're using the latest version of `crm_dashboard.py` which includes performance optimizations.

### Step 2: Launch with Optimal Settings

```bash
cd dashboard
streamlit run crm_dashboard.py
```

### Step 3: Adjust Settings in Sidebar

When dashboard loads:

1. **Sample Size Slider** (in sidebar):
   - For 300K users: Set to **10,000** (default)
   - If still slow: Reduce to **5,000**
   - If fast enough: Increase to **15,000**

2. **Segment Filter** (in sidebar):
   - Select specific segment (A, B, C, or D) instead of "All"
   - This reduces dataset by ~75% immediately

3. **Items per Page** (User Lookup tab):
   - Set to **100** or **250** for comfortable browsing
   - Avoid loading all users at once

### What Changed?

✅ **Sampling**: Only 10K users loaded for visualization (not all 300K)
✅ **Lazy Loading**: User profiles loaded on-demand
✅ **Smart Aggregations**: Stats calculated in database (DuckDB)
✅ **Pagination**: Browse large results efficiently
✅ **Caching**: Reduced repeated database queries

### Performance Expectations

With 300K users and default settings (10K sample):
- Initial load: **2-5 seconds** ✅
- Visualization: **1-3 seconds** ✅
- Analytics tab: **5-10 seconds** ✅
- User lookup: **<1 second** ✅

### Still Having Issues?

#### Dashboard crashes on startup
→ Restart and immediately reduce sample size to 5,000

#### Visualization is slow
→ Use segment filter to view one segment at a time

#### Export takes too long
→ Reduce "Maximum rows to export" to 10,000 or less

#### Out of memory
→ Close other applications and restart dashboard

### Visual Guide

```
┌─────────────────────────────────────┐
│ 👥 CRM Dashboard                    │
├─────────────────────────────────────┤
│ SIDEBAR                             │
│                                     │
│ ⚙️ Dashboard Controls               │
│                                     │
│ ⚠️ Large dataset: 300,000 users     │
│ ℹ️ Using optimized sampling         │
│                                     │
│ Period: [11/2019 ▼]                 │
│                                     │
│ ─────────────────────────────       │
│ 🎲 Visualization Settings           │
│                                     │
│ Sample size: 10000                  │
│ ├─────●───────────┤ (slider)        │
│ 1K              20K                 │
│                                     │
│ Filter: [All ▼]                     │
│                                     │
│ ─────────────────────────────       │
│ 📊 Quick Stats                      │
│ Total Users: 300,000                │
│ Available Periods: 3                │
└─────────────────────────────────────┘
```

### Pro Tips

1. **Start small**: Begin with 5K sample, increase if performance is good
2. **Filter first**: Select segment before visualization for faster load
3. **Use analytics wisely**: Tab 2 (Analytics) processes ALL data - may take 10s
4. **Export strategically**: Don't export all 300K users - filter and export smaller sets

### Technical Details

The dashboard now uses:
- **Stratified sampling**: Representative sample from each segment
- **DuckDB aggregations**: Fast, in-database calculations
- **Efficient queries**: LIMIT and OFFSET for pagination
- **Smart caching**: 5-minute cache for repeated queries

See [PERFORMANCE.md](PERFORMANCE.md) for detailed technical explanation.

### Need Help?

Check the main [README.md](README.md) for full documentation and troubleshooting.
