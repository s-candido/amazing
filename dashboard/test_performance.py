#!/usr/bin/env python3
"""
Performance Test Script for CRM Dashboard
Run this to verify the optimizations are working correctly
"""

import duckdb
import time
from pathlib import Path

def test_performance():
    print("=" * 60)
    print("CRM Dashboard - Performance Test")
    print("=" * 60)
    
    # Connect to database
    db_path = Path(__file__).parent.parent / "amazing.duckdb"
    
    if not db_path.exists():
        print(f"\n❌ Database not found: {db_path}")
        print("   Run interpret_clusters.ipynb first to create user_profiles table")
        return
    
    print(f"\n✅ Database found: {db_path}")
    con = duckdb.connect(str(db_path), read_only=True)
    
    # Test 1: Check if table exists
    print("\n" + "-" * 60)
    print("Test 1: Checking user_profiles table...")
    
    tables = con.execute("SHOW TABLES").df()
    if 'user_profiles' not in tables['name'].values:
        print("❌ user_profiles table not found")
        print("   Run interpret_clusters.ipynb first")
        return
    
    print("✅ user_profiles table exists")
    
    # Test 2: Count total users
    print("\n" + "-" * 60)
    print("Test 2: Counting total users...")
    
    start = time.time()
    result = con.execute("SELECT COUNT(*) as cnt FROM user_profiles").df()
    total_users = result['cnt'].iloc[0]
    elapsed = time.time() - start
    
    print(f"✅ Total users: {total_users:,}")
    print(f"   Query time: {elapsed:.3f}s")
    
    if elapsed > 1.0:
        print("   ⚠️  Warning: Count query is slow (should be <1s)")
    
    # Test 3: Get segment distribution
    print("\n" + "-" * 60)
    print("Test 3: Computing segment distribution...")
    
    # Get segment columns
    columns = con.execute("DESCRIBE user_profiles").df()
    segment_cols = [col for col in columns['column_name'].tolist() if col.startswith('segment_')]
    
    if not segment_cols:
        print("❌ No segment columns found")
        return
    
    print(f"✅ Found {len(segment_cols)} period(s): {', '.join(segment_cols)}")
    
    latest_segment = segment_cols[-1]
    
    start = time.time()
    stats = con.execute(f"""
        SELECT 
            {latest_segment} as segment,
            COUNT(*) as user_count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage
        FROM user_profiles
        WHERE {latest_segment} IS NOT NULL
        GROUP BY {latest_segment}
        ORDER BY segment
    """).df()
    elapsed = time.time() - start
    
    print(f"✅ Aggregation completed in {elapsed:.3f}s")
    print("\nSegment Distribution:")
    for _, row in stats.iterrows():
        print(f"   {row['segment']}: {row['user_count']:,} users ({row['percentage']}%)")
    
    if elapsed > 5.0:
        print(f"\n   ⚠️  Warning: Aggregation took {elapsed:.1f}s (should be <5s)")
    
    # Test 4: Sample query
    print("\n" + "-" * 60)
    print("Test 4: Testing stratified sampling (10K users)...")
    
    start = time.time()
    sample = con.execute(f"""
        SELECT * FROM user_profiles
        WHERE {latest_segment} IS NOT NULL
        ORDER BY RANDOM()
        LIMIT 10000
    """).df()
    elapsed = time.time() - start
    
    print(f"✅ Sampled {len(sample):,} users in {elapsed:.3f}s")
    
    if elapsed > 2.0:
        print(f"   ⚠️  Warning: Sampling took {elapsed:.1f}s (should be <2s)")
    
    # Test 5: Single user lookup
    print("\n" + "-" * 60)
    print("Test 5: Testing single user lookup...")
    
    test_user = sample['user_id'].iloc[0]
    
    start = time.time()
    user_data = con.execute(f"SELECT * FROM user_profiles WHERE user_id = '{test_user}'").df()
    elapsed = time.time() - start
    
    print(f"✅ Loaded user {test_user} in {elapsed:.3f}s")
    
    if elapsed > 0.1:
        print(f"   ⚠️  Warning: User lookup took {elapsed:.3f}s (should be <0.1s)")
    
    # Test 6: Pagination test
    print("\n" + "-" * 60)
    print("Test 6: Testing pagination (page 1 of 100 items)...")
    
    start = time.time()
    page_data = con.execute(f"""
        SELECT user_id, {latest_segment}
        FROM user_profiles
        WHERE {latest_segment} IS NOT NULL
        ORDER BY user_id
        LIMIT 100 OFFSET 0
    """).df()
    elapsed = time.time() - start
    
    print(f"✅ Loaded page (100 items) in {elapsed:.3f}s")
    
    if elapsed > 0.5:
        print(f"   ⚠️  Warning: Pagination took {elapsed:.3f}s (should be <0.5s)")
    
    # Summary
    print("\n" + "=" * 60)
    print("PERFORMANCE SUMMARY")
    print("=" * 60)
    
    # Calculate expected dashboard performance
    if total_users < 50000:
        tier = "Small"
        expected_load = "1-2s"
        expected_viz = "0.5-1s"
    elif total_users < 200000:
        tier = "Medium"
        expected_load = "2-3s"
        expected_viz = "1-2s"
    else:
        tier = "Large"
        expected_load = "2-5s"
        expected_viz = "1-3s"
    
    print(f"\nDataset Tier: {tier} ({total_users:,} users)")
    print(f"Expected dashboard initial load: {expected_load}")
    print(f"Expected visualization render: {expected_viz}")
    print(f"Expected analytics tab: 5-10s")
    print(f"Expected user lookup: <1s")
    
    print("\n✅ All performance tests completed!")
    print("\nReady to run dashboard:")
    print("   cd dashboard")
    print("   streamlit run crm_dashboard.py")
    
    # Recommendations
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)
    
    if total_users > 100000:
        print("\n⚙️  For optimal performance with large dataset:")
        print("   - Use sample size: 5,000-10,000")
        print("   - Enable segment filter when possible")
        print("   - Limit exports to <50K rows")
    elif total_users > 50000:
        print("\n⚙️  For good performance:")
        print("   - Use sample size: 10,000-15,000")
        print("   - Segment filter optional")
    else:
        print("\n✅ Dataset is small enough to use without sampling!")
        print("   - Can visualize all users")
        print("   - No special configuration needed")
    
    print("\n")

if __name__ == "__main__":
    test_performance()
