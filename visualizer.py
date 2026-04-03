# # app.py
# import streamlit as st
# import sqlite3
# import os
# import pandas as pd
# import json
# import glob

# # ============== CONFIGURATION ==============
# BASE_PATH = os.path.expanduser("~/BIRD")
# TRAIN_DB_PATH = os.path.join(BASE_PATH, "train", "train_databases")
# DEV_DB_PATH = os.path.join(BASE_PATH, "dev_20240627", "dev_databases")
# TRAIN_JSON_PATH = os.path.join(BASE_PATH, "train", "train.json")
# DEV_JSON_PATH = os.path.join(BASE_PATH, "dev_20240627", "dev.json")
# TRAIN_GOLD_SQL_PATH = os.path.join(BASE_PATH, "train", "train_gold.sql")
# DEV_SQL_PATH = os.path.join(BASE_PATH, "dev_20240627", "dev.sql")
# # ============================================


# # -------------------------------------------
# # Helper Functions
# # -------------------------------------------

# @st.cache_data
# def get_all_databases():
#     """Scan both train and dev folders and return a dict of db_name -> {path, source}"""
#     databases = {}

#     # Scan TRAIN databases
#     if os.path.exists(TRAIN_DB_PATH):
#         for folder in sorted(os.listdir(TRAIN_DB_PATH)):
#             folder_path = os.path.join(TRAIN_DB_PATH, folder)
#             if os.path.isdir(folder_path):
#                 sqlite_files = glob.glob(os.path.join(folder_path, "*.sqlite"))
#                 for sf in sqlite_files:
#                     db_name = os.path.splitext(os.path.basename(sf))[0]
#                     databases[db_name] = {
#                         "path": sf,
#                         "source": "Train",
#                         "description_dir": os.path.join(folder_path, "database_description")
#                     }

#     # Scan DEV databases
#     if os.path.exists(DEV_DB_PATH):
#         for folder in sorted(os.listdir(DEV_DB_PATH)):
#             folder_path = os.path.join(DEV_DB_PATH, folder)
#             if os.path.isdir(folder_path):
#                 sqlite_files = glob.glob(os.path.join(folder_path, "*.sqlite"))
#                 for sf in sqlite_files:
#                     db_name = os.path.splitext(os.path.basename(sf))[0]
#                     if db_name in databases:
#                         databases[db_name]["source"] = "Train & Dev"
#                         databases[db_name]["dev_path"] = sf
#                     else:
#                         databases[db_name] = {
#                             "path": sf,
#                             "source": "Dev",
#                             "description_dir": os.path.join(folder_path, "database_description")
#                         }

#     return databases


# @st.cache_data
# def load_json_examples(json_path):
#     """Load JSON examples from train.json or dev.json"""
#     if os.path.exists(json_path):
#         with open(json_path, "r", encoding="utf-8") as f:
#             return json.load(f)
#     return []


# @st.cache_data
# def load_gold_sql(sql_path):
#     """Load gold SQL file (train_gold.sql or dev.sql)"""
#     gold = []
#     if os.path.exists(sql_path):
#         with open(sql_path, "r", encoding="utf-8") as f:
#             for line in f:
#                 line = line.strip()
#                 if line:
#                     gold.append(line)
#     return gold


# @st.cache_data
# def build_example_counts(train_examples, dev_examples, db_names):
#     """
#     Pre-compute example counts per database for sorting.
#     Returns a dict: db_name -> {train_count, dev_count, total_count}
#     """
#     counts = {}
#     for db_name in db_names:
#         t_count = sum(1 for ex in train_examples if ex.get("db_id", "") == db_name)
#         d_count = sum(1 for ex in dev_examples if ex.get("db_id", "") == db_name)
#         counts[db_name] = {
#             "train_count": t_count,
#             "dev_count": d_count,
#             "total_count": t_count + d_count
#         }
#     return counts


# def get_tables_and_schema(db_path):
#     """Get all tables and their schema from a SQLite database"""
#     schema_info = {}
#     try:
#         conn = sqlite3.connect(db_path)
#         cursor = conn.cursor()
#         cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
#         tables = [row[0] for row in cursor.fetchall()]

#         for table in tables:
#             cursor.execute(f"PRAGMA table_info(`{table}`);")
#             columns = cursor.fetchall()
#             schema_info[table] = columns

#         conn.close()
#     except Exception as e:
#         st.error(f"Error reading schema: {e}")
#     return schema_info


# def execute_sql(db_path, sql_query):
#     """Execute SQL query and return results as DataFrame"""
#     try:
#         conn = sqlite3.connect(db_path)
#         df = pd.read_sql_query(sql_query, conn)
#         conn.close()
#         return df, None
#     except Exception as e:
#         return None, str(e)


# def get_examples_for_db(db_name, examples):
#     """Filter examples that match a given database name"""
#     return [ex for ex in examples if ex.get("db_id", "") == db_name]


# def get_row_counts(db_path, tables):
#     """Get row counts for each table"""
#     counts = {}
#     try:
#         conn = sqlite3.connect(db_path)
#         cursor = conn.cursor()
#         for table in tables:
#             cursor.execute(f"SELECT COUNT(*) FROM `{table}`;")
#             counts[table] = cursor.fetchone()[0]
#         conn.close()
#     except:
#         pass
#     return counts


# # -------------------------------------------
# # Streamlit UI
# # -------------------------------------------

# st.set_page_config(
#     page_title="🐦 BIRD Benchmark SQL Explorer",
#     page_icon="🐦",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# # Custom CSS
# st.markdown("""
# <style>
#     .main-header {
#         font-size: 2.5rem;
#         font-weight: bold;
#         color: #1E88E5;
#         text-align: center;
#         margin-bottom: 0.5rem;
#     }
#     .sub-header {
#         text-align: center;
#         color: #666;
#         margin-bottom: 2rem;
#     }
#     .source-badge-train {
#         background-color: #4CAF50;
#         color: white;
#         padding: 4px 12px;
#         border-radius: 12px;
#         font-weight: bold;
#         font-size: 0.9rem;
#     }
#     .source-badge-dev {
#         background-color: #FF9800;
#         color: white;
#         padding: 4px 12px;
#         border-radius: 12px;
#         font-weight: bold;
#         font-size: 0.9rem;
#     }
#     .source-badge-both {
#         background-color: #9C27B0;
#         color: white;
#         padding: 4px 12px;
#         border-radius: 12px;
#         font-weight: bold;
#         font-size: 0.9rem;
#     }
#     .stCodeBlock {
#         max-height: 400px;
#     }
#     .sort-info {
#         background-color: #f0f2f6;
#         padding: 8px 12px;
#         border-radius: 8px;
#         font-size: 0.85rem;
#         color: #444;
#         margin-top: 4px;
#     }
# </style>
# """, unsafe_allow_html=True)

# st.markdown('<div class="main-header">🐦 BIRD Benchmark SQL Explorer</div>', unsafe_allow_html=True)
# st.markdown('<div class="sub-header">Query Train & Dev databases from the BIRD Text-to-SQL Benchmark</div>', unsafe_allow_html=True)

# # Load all databases
# databases = get_all_databases()

# if not databases:
#     st.error("❌ No databases found! Please check the paths in the CONFIGURATION section.")
#     st.info(f"Expected TRAIN path: `{TRAIN_DB_PATH}`")
#     st.info(f"Expected DEV path: `{DEV_DB_PATH}`")
#     st.stop()

# # Load examples
# train_examples = load_json_examples(TRAIN_JSON_PATH)
# dev_examples = load_json_examples(DEV_JSON_PATH)
# train_gold = load_gold_sql(TRAIN_GOLD_SQL_PATH)
# dev_gold = load_gold_sql(DEV_SQL_PATH)

# # Pre-compute example counts for all databases
# example_counts = build_example_counts(
#     train_examples, dev_examples, list(databases.keys())
# )

# # -------------------------------------------
# # SIDEBAR
# # -------------------------------------------
# with st.sidebar:
#     st.header("⚙️ Configuration")

#     # Database selection
#     st.subheader("📁 Select Database")

#     # Filter by source
#     source_filter = st.radio(
#         "Filter by source:",
#         ["All", "Train Only", "Dev Only"],
#         horizontal=True
#     )

#     if source_filter == "Train Only":
#         filtered_dbs = {k: v for k, v in databases.items() if "Train" in v["source"]}
#     elif source_filter == "Dev Only":
#         filtered_dbs = {k: v for k, v in databases.items() if "Dev" in v["source"]}
#     else:
#         filtered_dbs = databases

#     # Search
#     search_term = st.text_input("🔍 Search database:", "")
#     if search_term:
#         filtered_dbs = {k: v for k, v in filtered_dbs.items() if search_term.lower() in k.lower()}

#     # ==========================================
#     # NEW FEATURE: Sort databases by examples
#     # ==========================================
#     st.markdown("---")
#     st.subheader("🔀 Sort Databases")

#     sort_option = st.selectbox(
#         "Sort by:",
#         [
#             "Alphabetical (A → Z)",
#             "Alphabetical (Z → A)",
#             "Train Examples (High → Low)",
#             "Train Examples (Low → High)",
#             "Dev Examples (High → Low)",
#             "Dev Examples (Low → High)",
#             "Total Examples (High → Low)",
#             "Total Examples (Low → High)",
#         ],
#         index=0,
#         key="sort_option"
#     )

#     # Apply sorting
#     db_names_list = list(filtered_dbs.keys())

#     if sort_option == "Alphabetical (A → Z)":
#         db_names = sorted(db_names_list)
#     elif sort_option == "Alphabetical (Z → A)":
#         db_names = sorted(db_names_list, reverse=True)
#     elif sort_option == "Train Examples (High → Low)":
#         db_names = sorted(
#             db_names_list,
#             key=lambda x: example_counts.get(x, {}).get("train_count", 0),
#             reverse=True
#         )
#     elif sort_option == "Train Examples (Low → High)":
#         db_names = sorted(
#             db_names_list,
#             key=lambda x: example_counts.get(x, {}).get("train_count", 0),
#             reverse=False
#         )
#     elif sort_option == "Dev Examples (High → Low)":
#         db_names = sorted(
#             db_names_list,
#             key=lambda x: example_counts.get(x, {}).get("dev_count", 0),
#             reverse=True
#         )
#     elif sort_option == "Dev Examples (Low → High)":
#         db_names = sorted(
#             db_names_list,
#             key=lambda x: example_counts.get(x, {}).get("dev_count", 0),
#             reverse=False
#         )
#     elif sort_option == "Total Examples (High → Low)":
#         db_names = sorted(
#             db_names_list,
#             key=lambda x: example_counts.get(x, {}).get("total_count", 0),
#             reverse=True
#         )
#     elif sort_option == "Total Examples (Low → High)":
#         db_names = sorted(
#             db_names_list,
#             key=lambda x: example_counts.get(x, {}).get("total_count", 0),
#             reverse=False
#         )
#     else:
#         db_names = sorted(db_names_list)

#     if not db_names:
#         st.warning("No databases match your filter.")
#         st.stop()

#     # Build display labels with example counts
#     def format_db_label(db_name):
#         """Format database name with example count for the dropdown."""
#         counts = example_counts.get(db_name, {})
#         total = counts.get("total_count", 0)
#         if total > 0:
#             return f"{db_name}  ({total} examples)"
#         return f"{db_name}  (0 examples)"

#     db_display_labels = [format_db_label(name) for name in db_names]

#     selected_index = st.selectbox(
#         "Choose a database:",
#         range(len(db_names)),
#         index=0,
#         format_func=lambda i: db_display_labels[i],
#         key="db_selector"
#     )

#     selected_db = db_names[selected_index]
#     db_info = databases[selected_db]

#     # Show example count breakdown for selected DB
#     sel_counts = example_counts.get(selected_db, {})
#     st.markdown(
#         f'<div class="sort-info">'
#         f'📊 <b>{selected_db}</b><br>'
#         f'&nbsp;&nbsp;📚 Train: <b>{sel_counts.get("train_count", 0)}</b> &nbsp;|&nbsp; '
#         f'🧪 Dev: <b>{sel_counts.get("dev_count", 0)}</b> &nbsp;|&nbsp; '
#         f'📝 Total: <b>{sel_counts.get("total_count", 0)}</b>'
#         f'</div>',
#         unsafe_allow_html=True
#     )

#     # Source badge
#     source = db_info["source"]
#     if source == "Train":
#         st.markdown(f'<span class="source-badge-train">📚 TRAIN</span>', unsafe_allow_html=True)
#     elif source == "Dev":
#         st.markdown(f'<span class="source-badge-dev">🧪 DEV</span>', unsafe_allow_html=True)
#     else:
#         st.markdown(f'<span class="source-badge-both">📚🧪 TRAIN & DEV</span>', unsafe_allow_html=True)

#     st.divider()

#     # Stats
#     st.subheader("📊 Stats")
#     train_count = sum(1 for v in databases.values() if "Train" in v["source"])
#     dev_count = sum(1 for v in databases.values() if "Dev" in v["source"])
#     st.metric("Total Databases", len(databases))
#     col1, col2 = st.columns(2)
#     col1.metric("Train DBs", train_count)
#     col2.metric("Dev DBs", dev_count)
#     st.metric("Train Examples", len(train_examples))
#     st.metric("Dev Examples", len(dev_examples))

#     st.divider()

#     # Settings
#     st.subheader("🔧 Settings")
#     max_rows = st.slider("Max rows to display:", 10, 1000, 100, 10)
#     show_schema = st.checkbox("Show schema on load", value=True)


# # -------------------------------------------
# # MAIN AREA
# # -------------------------------------------

# # Create tabs
# tab1, tab2, tab3, tab4, tab5 = st.tabs([
#     "🔍 SQL Query",
#     "📋 Schema Explorer",
#     "📝 Benchmark Examples",
#     "📊 Database Info",
#     "📈 Example Leaderboard"
# ])

# # ==========================================
# # TAB 1: SQL Query
# # ==========================================
# with tab1:
#     st.subheader(f"🔍 Query: `{selected_db}`")

#     source = db_info["source"]
#     if source == "Train":
#         st.success(f"✅ This database is from the **TRAINING** set.")
#     elif source == "Dev":
#         st.warning(f"🧪 This database is from the **DEV** set.")
#     else:
#         st.info(f"📚🧪 This database exists in **BOTH Train and Dev** sets.")

#     # SQL Input
#     sql_query = st.text_area(
#         "Enter your SQL query:",
#         height=150,
#         placeholder="SELECT * FROM table_name LIMIT 10;",
#         key="sql_input"
#     )

#     col1, col2, col3 = st.columns([1, 1, 4])

#     with col1:
#         run_button = st.button("▶️ Run Query", type="primary", use_container_width=True)
#     with col2:
#         clear_button = st.button("🗑️ Clear", use_container_width=True)

#     if clear_button:
#         st.rerun()

#     if run_button and sql_query.strip():
#         db_path = db_info["path"]

#         with st.spinner("Executing query..."):
#             df, error = execute_sql(db_path, sql_query.strip())

#         if error:
#             st.error(f"❌ SQL Error: {error}")
#         else:
#             st.success(f"✅ Query executed successfully! Returned **{len(df)}** rows, **{len(df.columns)}** columns.")

#             if len(df) > max_rows:
#                 st.warning(f"⚠️ Showing first {max_rows} of {len(df)} rows.")
#                 st.dataframe(df.head(max_rows), use_container_width=True)
#             else:
#                 st.dataframe(df, use_container_width=True)

#             # Download button
#             csv = df.to_csv(index=False)
#             st.download_button(
#                 label="📥 Download Results as CSV",
#                 data=csv,
#                 file_name=f"{selected_db}_query_results.csv",
#                 mime="text/csv"
#             )

#     elif run_button and not sql_query.strip():
#         st.warning("⚠️ Please enter a SQL query.")

#     # Quick queries
#     st.divider()
#     st.subheader("⚡ Quick Queries")

#     schema_info = get_tables_and_schema(db_info["path"])
#     if schema_info:
#         table_names = list(schema_info.keys())
#         selected_table = st.selectbox("Select a table for quick query:", table_names, key="quick_table")

#         qcol1, qcol2, qcol3, qcol4 = st.columns(4)

#         with qcol1:
#             if st.button(f"📋 SELECT * (LIMIT 10)", use_container_width=True):
#                 quick_sql = f"SELECT * FROM `{selected_table}` LIMIT 10;"
#                 df, error = execute_sql(db_info["path"], quick_sql)
#                 if error:
#                     st.error(f"❌ {error}")
#                 else:
#                     st.code(quick_sql, language="sql")
#                     st.dataframe(df, use_container_width=True)

#         with qcol2:
#             if st.button(f"🔢 COUNT(*)", use_container_width=True):
#                 quick_sql = f"SELECT COUNT(*) as row_count FROM `{selected_table}`;"
#                 df, error = execute_sql(db_info["path"], quick_sql)
#                 if error:
#                     st.error(f"❌ {error}")
#                 else:
#                     st.code(quick_sql, language="sql")
#                     st.dataframe(df, use_container_width=True)

#         with qcol3:
#             if st.button(f"📊 Column Info", use_container_width=True):
#                 quick_sql = f"PRAGMA table_info(`{selected_table}`);"
#                 df, error = execute_sql(db_info["path"], quick_sql)
#                 if error:
#                     st.error(f"❌ {error}")
#                 else:
#                     st.code(quick_sql, language="sql")
#                     st.dataframe(df, use_container_width=True)

#         with qcol4:
#             if st.button(f"🔗 Foreign Keys", use_container_width=True):
#                 quick_sql = f"PRAGMA foreign_key_list(`{selected_table}`);"
#                 df, error = execute_sql(db_info["path"], quick_sql)
#                 if error:
#                     st.error(f"❌ {error}")
#                 else:
#                     st.code(quick_sql, language="sql")
#                     if df.empty:
#                         st.info("No foreign keys found for this table.")
#                     else:
#                         st.dataframe(df, use_container_width=True)


# # ==========================================
# # TAB 2: Schema Explorer
# # ==========================================
# with tab2:
#     st.subheader(f"📋 Schema: `{selected_db}`")

#     schema_info = get_tables_and_schema(db_info["path"])

#     if schema_info:
#         row_counts = get_row_counts(db_info["path"], schema_info.keys())

#         st.info(f"📊 **{len(schema_info)}** tables found in `{selected_db}`")

#         for table_name, columns in schema_info.items():
#             count = row_counts.get(table_name, "?")
#             with st.expander(f"📁 **{table_name}** ({count} rows, {len(columns)} columns)", expanded=False):
#                 col_data = []
#                 for col in columns:
#                     col_data.append({
#                         "CID": col[0],
#                         "Column Name": col[1],
#                         "Type": col[2],
#                         "Not Null": "✅" if col[3] else "❌",
#                         "Default": col[4] if col[4] else "-",
#                         "Primary Key": "🔑" if col[5] else "-"
#                     })
#                 df_cols = pd.DataFrame(col_data)
#                 st.dataframe(df_cols, use_container_width=True, hide_index=True)

#                 # CREATE TABLE statement
#                 conn = sqlite3.connect(db_info["path"])
#                 cursor = conn.cursor()
#                 cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?;", (table_name,))
#                 result = cursor.fetchone()
#                 conn.close()
#                 if result and result[0]:
#                     st.code(result[0], language="sql")
#     else:
#         st.warning("No schema information found.")


# # ==========================================
# # TAB 3: Benchmark Examples
# # ==========================================
# with tab3:
#     st.subheader(f"📝 Benchmark Examples for: `{selected_db}`")

#     # Get examples for this database
#     train_db_examples = get_examples_for_db(selected_db, train_examples)
#     dev_db_examples = get_examples_for_db(selected_db, dev_examples)

#     if not train_db_examples and not dev_db_examples:
#         st.info(f"No benchmark examples found for `{selected_db}`.")
#     else:
#         # Train examples
#         if train_db_examples:
#             st.markdown(f"### 📚 Train Examples ({len(train_db_examples)})")
#             for i, ex in enumerate(train_db_examples):
#                 with st.expander(
#                     f"**Q{i+1}** [{ex.get('difficulty', 'N/A')}]: {ex.get('question', 'N/A')[:100]}...",
#                     expanded=False
#                 ):
#                     st.markdown(f"**Question:** {ex.get('question', 'N/A')}")
#                     st.markdown(f"**Difficulty:** `{ex.get('difficulty', 'N/A')}`")

#                     if ex.get('evidence'):
#                         st.markdown(f"**Evidence:** {ex.get('evidence', '')}")

#                     gold_sql = ex.get("SQL", ex.get("sql", "N/A"))
#                     st.markdown("**Gold SQL:**")
#                     st.code(gold_sql, language="sql")

#                     # Button to run gold SQL
#                     if st.button(f"▶️ Run this SQL", key=f"train_run_{i}"):
#                         df, error = execute_sql(db_info["path"], gold_sql)
#                         if error:
#                             st.error(f"❌ {error}")
#                         else:
#                             st.success(f"✅ {len(df)} rows returned.")
#                             st.dataframe(df.head(max_rows), use_container_width=True)

#             st.divider()

#         # Dev examples
#         if dev_db_examples:
#             st.markdown(f"### 🧪 Dev Examples ({len(dev_db_examples)})")
#             for i, ex in enumerate(dev_db_examples):
#                 with st.expander(
#                     f"**Q{i+1}** [{ex.get('difficulty', 'N/A')}]: {ex.get('question', 'N/A')[:100]}...",
#                     expanded=False
#                 ):
#                     st.markdown(f"**Question:** {ex.get('question', 'N/A')}")
#                     st.markdown(f"**Difficulty:** `{ex.get('difficulty', 'N/A')}`")

#                     if ex.get('evidence'):
#                         st.markdown(f"**Evidence:** {ex.get('evidence', '')}")

#                     gold_sql = ex.get("SQL", ex.get("sql", "N/A"))
#                     st.markdown("**Gold SQL:**")
#                     st.code(gold_sql, language="sql")

#                     # Button to run gold SQL
#                     db_path_to_use = db_info.get("dev_path", db_info["path"])
#                     if st.button(f"▶️ Run this SQL", key=f"dev_run_{i}"):
#                         df, error = execute_sql(db_path_to_use, gold_sql)
#                         if error:
#                             st.error(f"❌ {error}")
#                         else:
#                             st.success(f"✅ {len(df)} rows returned.")
#                             st.dataframe(df.head(max_rows), use_container_width=True)


# # ==========================================
# # TAB 4: Database Info
# # ==========================================
# with tab4:
#     st.subheader(f"📊 Database Info: `{selected_db}`")

#     source = db_info["source"]
#     col1, col2 = st.columns(2)

#     with col1:
#         st.markdown("### 📌 General Info")
#         info_data = {
#             "Property": [
#                 "Database Name",
#                 "Source",
#                 "File Path",
#                 "File Size",
#                 "Number of Tables"
#             ],
#             "Value": [
#                 selected_db,
#                 source,
#                 db_info["path"],
#                 f"{os.path.getsize(db_info['path']) / (1024*1024):.2f} MB",
#                 str(len(get_tables_and_schema(db_info["path"])))
#             ]
#         }
#         st.dataframe(pd.DataFrame(info_data), use_container_width=True, hide_index=True)

#     with col2:
#         st.markdown("### 📊 Example Counts")
#         train_count = len(get_examples_for_db(selected_db, train_examples))
#         dev_count = len(get_examples_for_db(selected_db, dev_examples))

#         count_data = {
#             "Set": ["Train", "Dev", "Total"],
#             "Examples": [train_count, dev_count, train_count + dev_count]
#         }
#         st.dataframe(pd.DataFrame(count_data), use_container_width=True, hide_index=True)

#     # Table row counts
#     st.markdown("### 📁 Table Row Counts")
#     schema_info = get_tables_and_schema(db_info["path"])
#     if schema_info:
#         row_counts = get_row_counts(db_info["path"], schema_info.keys())
#         table_stats = []
#         for table_name, columns in schema_info.items():
#             table_stats.append({
#                 "Table": table_name,
#                 "Columns": len(columns),
#                 "Rows": row_counts.get(table_name, 0)
#             })
#         df_stats = pd.DataFrame(table_stats)
#         df_stats = df_stats.sort_values("Rows", ascending=False)

#         st.dataframe(df_stats, use_container_width=True, hide_index=True)

#         # Bar chart
#         st.bar_chart(df_stats.set_index("Table")["Rows"])

#     # Description files
#     desc_dir = db_info.get("description_dir", "")
#     if os.path.exists(desc_dir):
#         st.markdown("### 📄 Database Description Files")
#         csv_files = glob.glob(os.path.join(desc_dir, "*.csv"))
#         if csv_files:
#             for csv_file in sorted(csv_files):
#                 fname = os.path.basename(csv_file)
#                 with st.expander(f"📄 {fname}"):
#                     try:
#                         df_desc = pd.read_csv(csv_file, nrows=20, encoding="utf-8")
#                         st.dataframe(df_desc, use_container_width=True)
#                     except Exception as e:
#                         try:
#                             df_desc = pd.read_csv(csv_file, nrows=20, encoding="latin-1")
#                             st.dataframe(df_desc, use_container_width=True)
#                         except Exception as e2:
#                             st.error(f"Could not read file: {e2}")
#         else:
#             st.info("No description CSV files found.")
#     else:
#         st.info("No database description directory found.")


# # ==========================================
# # TAB 5: Example Leaderboard (NEW)
# # ==========================================
# with tab5:
#     st.subheader("📈 Database Example Leaderboard")
#     st.markdown("View all databases ranked by their number of training/dev examples.")

#     # Build leaderboard dataframe
#     leaderboard_data = []
#     for db_name, counts in example_counts.items():
#         db_src = databases[db_name]["source"]
#         leaderboard_data.append({
#             "Database": db_name,
#             "Source": db_src,
#             "Train Examples": counts["train_count"],
#             "Dev Examples": counts["dev_count"],
#             "Total Examples": counts["total_count"]
#         })

#     df_leaderboard = pd.DataFrame(leaderboard_data)

#     # Leaderboard sort options
#     lb_col1, lb_col2, lb_col3 = st.columns([2, 2, 2])

#     with lb_col1:
#         lb_sort_by = st.selectbox(
#             "Sort leaderboard by:",
#             ["Total Examples", "Train Examples", "Dev Examples", "Database"],
#             index=0,
#             key="lb_sort"
#         )
#     with lb_col2:
#         lb_sort_order = st.radio(
#             "Order:",
#             ["Descending", "Ascending"],
#             horizontal=True,
#             key="lb_order"
#         )
#     with lb_col3:
#         lb_source_filter = st.selectbox(
#             "Filter source:",
#             ["All", "Train", "Dev", "Train & Dev"],
#             index=0,
#             key="lb_source"
#         )

#     # Apply source filter
#     if lb_source_filter != "All":
#         df_leaderboard = df_leaderboard[
#             df_leaderboard["Source"].str.contains(lb_source_filter)
#         ]

#     # Apply sorting
#     ascending = lb_sort_order == "Ascending"
#     df_leaderboard = df_leaderboard.sort_values(
#         lb_sort_by, ascending=ascending
#     ).reset_index(drop=True)

#     # Add rank column
#     df_leaderboard.insert(0, "Rank", range(1, len(df_leaderboard) + 1))

#     # Summary metrics
#     m_col1, m_col2, m_col3, m_col4 = st.columns(4)
#     m_col1.metric("Databases Shown", len(df_leaderboard))
#     m_col2.metric("Total Train Examples", df_leaderboard["Train Examples"].sum())
#     m_col3.metric("Total Dev Examples", df_leaderboard["Dev Examples"].sum())
#     m_col4.metric(
#         "Avg Examples/DB",
#         f"{df_leaderboard['Total Examples'].mean():.1f}" if len(df_leaderboard) > 0 else "0"
#     )

#     st.dataframe(
#         df_leaderboard,
#         use_container_width=True,
#         hide_index=True,
#         height=500
#     )

#     # Visualization
#     st.markdown("### 📊 Top 20 Databases by Example Count")

#     top_20 = df_leaderboard.head(20).copy()
#     if not top_20.empty:
#         chart_data = top_20.set_index("Database")[["Train Examples", "Dev Examples"]]
#         st.bar_chart(chart_data)

#     # Download leaderboard
#     csv_lb = df_leaderboard.to_csv(index=False)
#     st.download_button(
#         label="📥 Download Leaderboard as CSV",
#         data=csv_lb,
#         file_name="bird_database_example_leaderboard.csv",
#         mime="text/csv"
#     )


# # -------------------------------------------
# # FOOTER
# # -------------------------------------------
# st.divider()
# st.markdown("""
# <div style="text-align: center; color: #888; font-size: 0.85rem;">
#     🐦 BIRD Benchmark SQL Explorer | 
#     Built with Streamlit | 
#     <a href="https://bird-bench.github.io/" target="_blank">BIRD Benchmark</a>
# </div>
# """, unsafe_allow_html=True)

# app.py
import streamlit as st
import sqlite3
import os
import re
import pandas as pd
import json
import glob

# ============== CONFIGURATION ==============
BASE_PATH = os.path.expanduser("~/BIRD")
TRAIN_DB_PATH = os.path.join(BASE_PATH, "train", "train_databases")
DEV_DB_PATH = os.path.join(BASE_PATH, "dev_20240627", "dev_databases")
TRAIN_JSON_PATH = os.path.join(BASE_PATH, "train", "train.json")
DEV_JSON_PATH = os.path.join(BASE_PATH, "dev_20240627", "dev.json")
TRAIN_GOLD_SQL_PATH = os.path.join(BASE_PATH, "train", "train_gold.sql")
DEV_SQL_PATH = os.path.join(BASE_PATH, "dev_20240627", "dev.sql")
# ============================================


# -------------------------------------------
# READ-ONLY SAFETY LAYER
# -------------------------------------------

# Keywords that indicate write/destructive operations
BLOCKED_SQL_KEYWORDS = [
    'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE',
    'REPLACE', 'TRUNCATE', 'RENAME', 'GRANT', 'REVOKE',
    'ATTACH', 'DETACH', 'REINDEX', 'VACUUM',
    'LOAD_EXTENSION', 'SAVEPOINT', 'RELEASE',
    'BEGIN', 'COMMIT', 'ROLLBACK',
]

# Only these statement types are allowed
ALLOWED_SQL_PREFIXES = ('SELECT', 'PRAGMA', 'EXPLAIN', 'WITH')


def validate_sql_readonly(sql_query: str) -> tuple:
    """
    Validate that a SQL query is strictly read-only.
    Returns (is_safe: bool, error_message: str or None)
    
    Three layers of protection:
      1. Must start with an allowed prefix (SELECT, PRAGMA, EXPLAIN, WITH)
      2. Must not contain any blocked keywords
      3. Must not contain multiple statements (no ; splitting)
    """
    if not sql_query or not sql_query.strip():
        return False, "Empty query."

    cleaned = sql_query.strip()

    # ---- Layer 1: Block multiple statements ----
    # Remove string literals to avoid false positives on semicolons inside strings
    # Replace everything inside single quotes and double quotes with placeholders
    sanitized_for_split = re.sub(r"'[^']*'", "''", cleaned)
    sanitized_for_split = re.sub(r'"[^"]*"', '""', sanitized_for_split)

    statements = [s.strip() for s in sanitized_for_split.split(';') if s.strip()]
    if len(statements) > 1:
        return False, "🚫 Multiple SQL statements are not allowed. Please submit one query at a time."

    # ---- Layer 2: Must start with allowed prefix ----
    upper_cleaned = cleaned.upper().lstrip()
    if not upper_cleaned.startswith(ALLOWED_SQL_PREFIXES):
        return False, (
            f"🚫 Only read-only queries are allowed. "
            f"Your query must start with one of: {', '.join(ALLOWED_SQL_PREFIXES)}"
        )

    # ---- Layer 3: Scan for blocked keywords ----
    # Use word-boundary matching on the sanitized version (strings removed)
    sanitized_upper = sanitized_for_split.upper()
    for keyword in BLOCKED_SQL_KEYWORDS:
        pattern = r'\b' + keyword + r'\b'
        if re.search(pattern, sanitized_upper):
            return False, f"🚫 Blocked operation detected: `{keyword}`. Only read-only queries are permitted."

    return True, None


def get_readonly_connection(db_path: str) -> sqlite3.Connection:
    """
    Open a SQLite connection in read-only mode using URI.
    This is enforced at the SQLite engine level — even if SQL validation
    is somehow bypassed, the database file cannot be modified.
    """
    # Convert to absolute path for URI
    abs_path = os.path.abspath(db_path)
    # file: URI with ?mode=ro makes it physically read-only
    uri = f"file:{abs_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    # Belt-and-suspenders: also set PRAGMA query_only
    conn.execute("PRAGMA query_only = ON;")
    return conn


# -------------------------------------------
# Helper Functions
# -------------------------------------------

@st.cache_data
def get_all_databases():
    """Scan both train and dev folders and return a dict of db_name -> {path, source}"""
    databases = {}

    # Scan TRAIN databases
    if os.path.exists(TRAIN_DB_PATH):
        for folder in sorted(os.listdir(TRAIN_DB_PATH)):
            folder_path = os.path.join(TRAIN_DB_PATH, folder)
            if os.path.isdir(folder_path):
                sqlite_files = glob.glob(os.path.join(folder_path, "*.sqlite"))
                for sf in sqlite_files:
                    db_name = os.path.splitext(os.path.basename(sf))[0]
                    databases[db_name] = {
                        "path": sf,
                        "source": "Train",
                        "description_dir": os.path.join(folder_path, "database_description")
                    }

    # Scan DEV databases
    if os.path.exists(DEV_DB_PATH):
        for folder in sorted(os.listdir(DEV_DB_PATH)):
            folder_path = os.path.join(DEV_DB_PATH, folder)
            if os.path.isdir(folder_path):
                sqlite_files = glob.glob(os.path.join(folder_path, "*.sqlite"))
                for sf in sqlite_files:
                    db_name = os.path.splitext(os.path.basename(sf))[0]
                    if db_name in databases:
                        databases[db_name]["source"] = "Train & Dev"
                        databases[db_name]["dev_path"] = sf
                    else:
                        databases[db_name] = {
                            "path": sf,
                            "source": "Dev",
                            "description_dir": os.path.join(folder_path, "database_description")
                        }

    return databases


@st.cache_data
def load_json_examples(json_path):
    """Load JSON examples from train.json or dev.json"""
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


@st.cache_data
def load_gold_sql(sql_path):
    """Load gold SQL file (train_gold.sql or dev.sql)"""
    gold = []
    if os.path.exists(sql_path):
        with open(sql_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    gold.append(line)
    return gold


@st.cache_data
def build_example_counts(train_examples, dev_examples, db_names):
    """
    Pre-compute example counts per database for sorting.
    Returns a dict: db_name -> {train_count, dev_count, total_count}
    """
    counts = {}
    for db_name in db_names:
        t_count = sum(1 for ex in train_examples if ex.get("db_id", "") == db_name)
        d_count = sum(1 for ex in dev_examples if ex.get("db_id", "") == db_name)
        counts[db_name] = {
            "train_count": t_count,
            "dev_count": d_count,
            "total_count": t_count + d_count
        }
    return counts


def get_tables_and_schema(db_path):
    """Get all tables and their schema from a SQLite database (read-only)"""
    schema_info = {}
    try:
        conn = get_readonly_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            cursor.execute(f"PRAGMA table_info(`{table}`);")
            columns = cursor.fetchall()
            schema_info[table] = columns

        conn.close()
    except Exception as e:
        st.error(f"Error reading schema: {e}")
    return schema_info


def execute_sql(db_path, sql_query):
    """
    Execute SQL query and return results as DataFrame.
    Protected by:
      1. SQL validation (keyword + prefix + multi-statement check)
      2. Read-only SQLite URI connection (?mode=ro)
      3. PRAGMA query_only = ON
    """
    # ---- Validate before executing ----
    is_safe, error_msg = validate_sql_readonly(sql_query)
    if not is_safe:
        return None, error_msg

    try:
        conn = get_readonly_connection(db_path)
        df = pd.read_sql_query(sql_query, conn)
        conn.close()
        return df, None
    except Exception as e:
        return None, str(e)


def get_examples_for_db(db_name, examples):
    """Filter examples that match a given database name"""
    return [ex for ex in examples if ex.get("db_id", "") == db_name]


def get_row_counts(db_path, tables):
    """Get row counts for each table (read-only)"""
    counts = {}
    try:
        conn = get_readonly_connection(db_path)
        cursor = conn.cursor()
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM `{table}`;")
            counts[table] = cursor.fetchone()[0]
        conn.close()
    except:
        pass
    return counts


# -------------------------------------------
# Streamlit UI
# -------------------------------------------

st.set_page_config(
    page_title="🐦 BIRD Benchmark SQL Explorer",
    page_icon="🐦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .readonly-badge {
        background-color: #E8F5E9;
        border: 2px solid #4CAF50;
        color: #2E7D32;
        padding: 8px 16px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 0.9rem;
        text-align: center;
        margin-bottom: 1rem;
    }
    .source-badge-train {
        background-color: #4CAF50;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.9rem;
    }
    .source-badge-dev {
        background-color: #FF9800;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.9rem;
    }
    .source-badge-both {
        background-color: #9C27B0;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.9rem;
    }
    .stCodeBlock {
        max-height: 400px;
    }
    .sort-info {
        background-color: #f0f2f6;
        padding: 8px 12px;
        border-radius: 8px;
        font-size: 0.85rem;
        color: #444;
        margin-top: 4px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🐦 BIRD Benchmark SQL Explorer</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Query Train & Dev databases from the BIRD Text-to-SQL Benchmark</div>', unsafe_allow_html=True)

# Read-only badge
st.markdown(
    '<div class="readonly-badge">🔒 READ-ONLY MODE — All database connections are read-only. '
    'Only SELECT, PRAGMA, EXPLAIN, and WITH queries are permitted.</div>',
    unsafe_allow_html=True
)

# Load all databases
databases = get_all_databases()

if not databases:
    st.error("❌ No databases found! Please check the paths in the CONFIGURATION section.")
    st.info(f"Expected TRAIN path: `{TRAIN_DB_PATH}`")
    st.info(f"Expected DEV path: `{DEV_DB_PATH}`")
    st.stop()

# Load examples
train_examples = load_json_examples(TRAIN_JSON_PATH)
dev_examples = load_json_examples(DEV_JSON_PATH)
train_gold = load_gold_sql(TRAIN_GOLD_SQL_PATH)
dev_gold = load_gold_sql(DEV_SQL_PATH)

# Pre-compute example counts for all databases
example_counts = build_example_counts(
    train_examples, dev_examples, list(databases.keys())
)

# -------------------------------------------
# SIDEBAR
# -------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuration")

    # Database selection
    st.subheader("📁 Select Database")

    # Filter by source
    source_filter = st.radio(
        "Filter by source:",
        ["All", "Train Only", "Dev Only"],
        horizontal=True
    )

    if source_filter == "Train Only":
        filtered_dbs = {k: v for k, v in databases.items() if "Train" in v["source"]}
    elif source_filter == "Dev Only":
        filtered_dbs = {k: v for k, v in databases.items() if "Dev" in v["source"]}
    else:
        filtered_dbs = databases

    # Search
    search_term = st.text_input("🔍 Search database:", "")
    if search_term:
        filtered_dbs = {k: v for k, v in filtered_dbs.items() if search_term.lower() in k.lower()}

    # ==========================================
    # Sort databases by examples
    # ==========================================
    st.markdown("---")
    st.subheader("🔀 Sort Databases")

    sort_option = st.selectbox(
        "Sort by:",
        [
            "Alphabetical (A → Z)",
            "Alphabetical (Z → A)",
            "Train Examples (High → Low)",
            "Train Examples (Low → High)",
            "Dev Examples (High → Low)",
            "Dev Examples (Low → High)",
            "Total Examples (High → Low)",
            "Total Examples (Low → High)",
        ],
        index=0,
        key="sort_option"
    )

    # Apply sorting
    db_names_list = list(filtered_dbs.keys())

    if sort_option == "Alphabetical (A → Z)":
        db_names = sorted(db_names_list)
    elif sort_option == "Alphabetical (Z → A)":
        db_names = sorted(db_names_list, reverse=True)
    elif sort_option == "Train Examples (High → Low)":
        db_names = sorted(
            db_names_list,
            key=lambda x: example_counts.get(x, {}).get("train_count", 0),
            reverse=True
        )
    elif sort_option == "Train Examples (Low → High)":
        db_names = sorted(
            db_names_list,
            key=lambda x: example_counts.get(x, {}).get("train_count", 0),
            reverse=False
        )
    elif sort_option == "Dev Examples (High → Low)":
        db_names = sorted(
            db_names_list,
            key=lambda x: example_counts.get(x, {}).get("dev_count", 0),
            reverse=True
        )
    elif sort_option == "Dev Examples (Low → High)":
        db_names = sorted(
            db_names_list,
            key=lambda x: example_counts.get(x, {}).get("dev_count", 0),
            reverse=False
        )
    elif sort_option == "Total Examples (High → Low)":
        db_names = sorted(
            db_names_list,
            key=lambda x: example_counts.get(x, {}).get("total_count", 0),
            reverse=True
        )
    elif sort_option == "Total Examples (Low → High)":
        db_names = sorted(
            db_names_list,
            key=lambda x: example_counts.get(x, {}).get("total_count", 0),
            reverse=False
        )
    else:
        db_names = sorted(db_names_list)

    if not db_names:
        st.warning("No databases match your filter.")
        st.stop()

    # Build display labels with example counts
    def format_db_label(db_name):
        """Format database name with example count for the dropdown."""
        counts = example_counts.get(db_name, {})
        total = counts.get("total_count", 0)
        if total > 0:
            return f"{db_name}  ({total} examples)"
        return f"{db_name}  (0 examples)"

    db_display_labels = [format_db_label(name) for name in db_names]

    selected_index = st.selectbox(
        "Choose a database:",
        range(len(db_names)),
        index=0,
        format_func=lambda i: db_display_labels[i],
        key="db_selector"
    )

    selected_db = db_names[selected_index]
    db_info = databases[selected_db]

    # Show example count breakdown for selected DB
    sel_counts = example_counts.get(selected_db, {})
    st.markdown(
        f'<div class="sort-info">'
        f'📊 <b>{selected_db}</b><br>'
        f'&nbsp;&nbsp;📚 Train: <b>{sel_counts.get("train_count", 0)}</b> &nbsp;|&nbsp; '
        f'🧪 Dev: <b>{sel_counts.get("dev_count", 0)}</b> &nbsp;|&nbsp; '
        f'📝 Total: <b>{sel_counts.get("total_count", 0)}</b>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Source badge
    source = db_info["source"]
    if source == "Train":
        st.markdown(f'<span class="source-badge-train">📚 TRAIN</span>', unsafe_allow_html=True)
    elif source == "Dev":
        st.markdown(f'<span class="source-badge-dev">🧪 DEV</span>', unsafe_allow_html=True)
    else:
        st.markdown(f'<span class="source-badge-both">📚🧪 TRAIN & DEV</span>', unsafe_allow_html=True)

    st.divider()

    # Stats
    st.subheader("📊 Stats")
    train_count = sum(1 for v in databases.values() if "Train" in v["source"])
    dev_count = sum(1 for v in databases.values() if "Dev" in v["source"])
    st.metric("Total Databases", len(databases))
    col1, col2 = st.columns(2)
    col1.metric("Train DBs", train_count)
    col2.metric("Dev DBs", dev_count)
    st.metric("Train Examples", len(train_examples))
    st.metric("Dev Examples", len(dev_examples))

    st.divider()

    # Settings
    st.subheader("🔧 Settings")
    max_rows = st.slider("Max rows to display:", 10, 1000, 100, 10)
    show_schema = st.checkbox("Show schema on load", value=True)

    # Security info in sidebar
    st.divider()
    st.subheader("🔒 Security")
    st.markdown("""
    **Read-only protections active:**
    - ✅ SQLite URI `?mode=ro`
    - ✅ `PRAGMA query_only = ON`
    - ✅ SQL keyword validation
    - ✅ Multi-statement blocking
    - ✅ Prefix whitelist enforcement
    """)


# -------------------------------------------
# MAIN AREA
# -------------------------------------------

# Create tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍 SQL Query",
    "📋 Schema Explorer",
    "📝 Benchmark Examples",
    "📊 Database Info",
    "📈 Example Leaderboard"
])

# ==========================================
# TAB 1: SQL Query
# ==========================================
with tab1:
    st.subheader(f"🔍 Query: `{selected_db}`")

    source = db_info["source"]
    if source == "Train":
        st.success(f"✅ This database is from the **TRAINING** set.")
    elif source == "Dev":
        st.warning(f"🧪 This database is from the **DEV** set.")
    else:
        st.info(f"📚🧪 This database exists in **BOTH Train and Dev** sets.")

    # Read-only notice
    st.info("🔒 **Read-only mode**: Only `SELECT`, `PRAGMA`, `EXPLAIN`, and `WITH` statements are allowed.")

    # SQL Input
    sql_query = st.text_area(
        "Enter your SQL query:",
        height=150,
        placeholder="SELECT * FROM table_name LIMIT 10;",
        key="sql_input"
    )

    col1, col2, col3 = st.columns([1, 1, 4])

    with col1:
        run_button = st.button("▶️ Run Query", type="primary", use_container_width=True)
    with col2:
        clear_button = st.button("🗑️ Clear", use_container_width=True)

    if clear_button:
        st.rerun()

    if run_button and sql_query.strip():
        db_path = db_info["path"]

        with st.spinner("Executing query..."):
            df, error = execute_sql(db_path, sql_query.strip())

        if error:
            st.error(f"❌ SQL Error: {error}")
        else:
            st.success(f"✅ Query executed successfully! Returned **{len(df)}** rows, **{len(df.columns)}** columns.")

            if len(df) > max_rows:
                st.warning(f"⚠️ Showing first {max_rows} of {len(df)} rows.")
                st.dataframe(df.head(max_rows), use_container_width=True)
            else:
                st.dataframe(df, use_container_width=True)

            # Download button
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download Results as CSV",
                data=csv,
                file_name=f"{selected_db}_query_results.csv",
                mime="text/csv"
            )

    elif run_button and not sql_query.strip():
        st.warning("⚠️ Please enter a SQL query.")

    # Quick queries
    st.divider()
    st.subheader("⚡ Quick Queries")

    schema_info = get_tables_and_schema(db_info["path"])
    if schema_info:
        table_names = list(schema_info.keys())
        selected_table = st.selectbox("Select a table for quick query:", table_names, key="quick_table")

        qcol1, qcol2, qcol3, qcol4 = st.columns(4)

        with qcol1:
            if st.button(f"📋 SELECT * (LIMIT 10)", use_container_width=True):
                quick_sql = f"SELECT * FROM `{selected_table}` LIMIT 10;"
                df, error = execute_sql(db_info["path"], quick_sql)
                if error:
                    st.error(f"❌ {error}")
                else:
                    st.code(quick_sql, language="sql")
                    st.dataframe(df, use_container_width=True)

        with qcol2:
            if st.button(f"🔢 COUNT(*)", use_container_width=True):
                quick_sql = f"SELECT COUNT(*) as row_count FROM `{selected_table}`;"
                df, error = execute_sql(db_info["path"], quick_sql)
                if error:
                    st.error(f"❌ {error}")
                else:
                    st.code(quick_sql, language="sql")
                    st.dataframe(df, use_container_width=True)

        with qcol3:
            if st.button(f"📊 Column Info", use_container_width=True):
                quick_sql = f"PRAGMA table_info(`{selected_table}`);"
                df, error = execute_sql(db_info["path"], quick_sql)
                if error:
                    st.error(f"❌ {error}")
                else:
                    st.code(quick_sql, language="sql")
                    st.dataframe(df, use_container_width=True)

        with qcol4:
            if st.button(f"🔗 Foreign Keys", use_container_width=True):
                quick_sql = f"PRAGMA foreign_key_list(`{selected_table}`);"
                df, error = execute_sql(db_info["path"], quick_sql)
                if error:
                    st.error(f"❌ {error}")
                else:
                    st.code(quick_sql, language="sql")
                    if df.empty:
                        st.info("No foreign keys found for this table.")
                    else:
                        st.dataframe(df, use_container_width=True)


# ==========================================
# TAB 2: Schema Explorer
# ==========================================
with tab2:
    st.subheader(f"📋 Schema: `{selected_db}`")

    schema_info = get_tables_and_schema(db_info["path"])

    if schema_info:
        row_counts = get_row_counts(db_info["path"], schema_info.keys())

        st.info(f"📊 **{len(schema_info)}** tables found in `{selected_db}`")

        for table_name, columns in schema_info.items():
            count = row_counts.get(table_name, "?")
            with st.expander(f"📁 **{table_name}** ({count} rows, {len(columns)} columns)", expanded=False):
                col_data = []
                for col in columns:
                    col_data.append({
                        "CID": col[0],
                        "Column Name": col[1],
                        "Type": col[2],
                        "Not Null": "✅" if col[3] else "❌",
                        "Default": col[4] if col[4] else "-",
                        "Primary Key": "🔑" if col[5] else "-"
                    })
                df_cols = pd.DataFrame(col_data)
                st.dataframe(df_cols, use_container_width=True, hide_index=True)

                # CREATE TABLE statement (using read-only connection)
                try:
                    conn = get_readonly_connection(db_info["path"])
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?;",
                        (table_name,)
                    )
                    result = cursor.fetchone()
                    conn.close()
                    if result and result[0]:
                        st.code(result[0], language="sql")
                except Exception as e:
                    st.error(f"Error reading CREATE statement: {e}")
    else:
        st.warning("No schema information found.")


# ==========================================
# TAB 3: Benchmark Examples
# ==========================================
with tab3:
    st.subheader(f"📝 Benchmark Examples for: `{selected_db}`")

    # Get examples for this database
    train_db_examples = get_examples_for_db(selected_db, train_examples)
    dev_db_examples = get_examples_for_db(selected_db, dev_examples)

    if not train_db_examples and not dev_db_examples:
        st.info(f"No benchmark examples found for `{selected_db}`.")
    else:
        # Train examples
        if train_db_examples:
            st.markdown(f"### 📚 Train Examples ({len(train_db_examples)})")
            for i, ex in enumerate(train_db_examples):
                with st.expander(
                    f"**Q{i+1}** [{ex.get('difficulty', 'N/A')}]: {ex.get('question', 'N/A')[:100]}...",
                    expanded=False
                ):
                    st.markdown(f"**Question:** {ex.get('question', 'N/A')}")
                    st.markdown(f"**Difficulty:** `{ex.get('difficulty', 'N/A')}`")

                    if ex.get('evidence'):
                        st.markdown(f"**Evidence:** {ex.get('evidence', '')}")

                    gold_sql = ex.get("SQL", ex.get("sql", "N/A"))
                    st.markdown("**Gold SQL:**")
                    st.code(gold_sql, language="sql")

                    # Button to run gold SQL
                    if st.button(f"▶️ Run this SQL", key=f"train_run_{i}"):
                        df, error = execute_sql(db_info["path"], gold_sql)
                        if error:
                            st.error(f"❌ {error}")
                        else:
                            st.success(f"✅ {len(df)} rows returned.")
                            st.dataframe(df.head(max_rows), use_container_width=True)

            st.divider()

        # Dev examples
        if dev_db_examples:
            st.markdown(f"### 🧪 Dev Examples ({len(dev_db_examples)})")
            for i, ex in enumerate(dev_db_examples):
                with st.expander(
                    f"**Q{i+1}** [{ex.get('difficulty', 'N/A')}]: {ex.get('question', 'N/A')[:100]}...",
                    expanded=False
                ):
                    st.markdown(f"**Question:** {ex.get('question', 'N/A')}")
                    st.markdown(f"**Difficulty:** `{ex.get('difficulty', 'N/A')}`")

                    if ex.get('evidence'):
                        st.markdown(f"**Evidence:** {ex.get('evidence', '')}")

                    gold_sql = ex.get("SQL", ex.get("sql", "N/A"))
                    st.markdown("**Gold SQL:**")
                    st.code(gold_sql, language="sql")

                    # Button to run gold SQL
                    db_path_to_use = db_info.get("dev_path", db_info["path"])
                    if st.button(f"▶️ Run this SQL", key=f"dev_run_{i}"):
                        df, error = execute_sql(db_path_to_use, gold_sql)
                        if error:
                            st.error(f"❌ {error}")
                        else:
                            st.success(f"✅ {len(df)} rows returned.")
                            st.dataframe(df.head(max_rows), use_container_width=True)


# ==========================================
# TAB 4: Database Info
# ==========================================
with tab4:
    st.subheader(f"📊 Database Info: `{selected_db}`")

    source = db_info["source"]
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📌 General Info")
        info_data = {
            "Property": [
                "Database Name",
                "Source",
                "File Path",
                "File Size",
                "Number of Tables",
                "Access Mode"
            ],
            "Value": [
                selected_db,
                source,
                db_info["path"],
                f"{os.path.getsize(db_info['path']) / (1024*1024):.2f} MB",
                str(len(get_tables_and_schema(db_info["path"]))),
                "🔒 Read-Only"
            ]
        }
        st.dataframe(pd.DataFrame(info_data), use_container_width=True, hide_index=True)

    with col2:
        st.markdown("### 📊 Example Counts")
        train_count = len(get_examples_for_db(selected_db, train_examples))
        dev_count = len(get_examples_for_db(selected_db, dev_examples))

        count_data = {
            "Set": ["Train", "Dev", "Total"],
            "Examples": [train_count, dev_count, train_count + dev_count]
        }
        st.dataframe(pd.DataFrame(count_data), use_container_width=True, hide_index=True)

    # Table row counts
    st.markdown("### 📁 Table Row Counts")
    schema_info = get_tables_and_schema(db_info["path"])
    if schema_info:
        row_counts = get_row_counts(db_info["path"], schema_info.keys())
        table_stats = []
        for table_name, columns in schema_info.items():
            table_stats.append({
                "Table": table_name,
                "Columns": len(columns),
                "Rows": row_counts.get(table_name, 0)
            })
        df_stats = pd.DataFrame(table_stats)
        df_stats = df_stats.sort_values("Rows", ascending=False)

        st.dataframe(df_stats, use_container_width=True, hide_index=True)

        # Bar chart
        st.bar_chart(df_stats.set_index("Table")["Rows"])

    # Description files
    desc_dir = db_info.get("description_dir", "")
    if os.path.exists(desc_dir):
        st.markdown("### 📄 Database Description Files")
        csv_files = glob.glob(os.path.join(desc_dir, "*.csv"))
        if csv_files:
            for csv_file in sorted(csv_files):
                fname = os.path.basename(csv_file)
                with st.expander(f"📄 {fname}"):
                    try:
                        df_desc = pd.read_csv(csv_file, nrows=20, encoding="utf-8")
                        st.dataframe(df_desc, use_container_width=True)
                    except Exception as e:
                        try:
                            df_desc = pd.read_csv(csv_file, nrows=20, encoding="latin-1")
                            st.dataframe(df_desc, use_container_width=True)
                        except Exception as e2:
                            st.error(f"Could not read file: {e2}")
        else:
            st.info("No description CSV files found.")
    else:
        st.info("No database description directory found.")


# ==========================================
# TAB 5: Example Leaderboard
# ==========================================
with tab5:
    st.subheader("📈 Database Example Leaderboard")
    st.markdown("View all databases ranked by their number of training/dev examples.")

    # Build leaderboard dataframe
    leaderboard_data = []
    for db_name, counts in example_counts.items():
        db_src = databases[db_name]["source"]
        leaderboard_data.append({
            "Database": db_name,
            "Source": db_src,
            "Train Examples": counts["train_count"],
            "Dev Examples": counts["dev_count"],
            "Total Examples": counts["total_count"]
        })

    df_leaderboard = pd.DataFrame(leaderboard_data)

    # Leaderboard sort options
    lb_col1, lb_col2, lb_col3 = st.columns([2, 2, 2])

    with lb_col1:
        lb_sort_by = st.selectbox(
            "Sort leaderboard by:",
            ["Total Examples", "Train Examples", "Dev Examples", "Database"],
            index=0,
            key="lb_sort"
        )
    with lb_col2:
        lb_sort_order = st.radio(
            "Order:",
            ["Descending", "Ascending"],
            horizontal=True,
            key="lb_order"
        )
    with lb_col3:
        lb_source_filter = st.selectbox(
            "Filter source:",
            ["All", "Train", "Dev", "Train & Dev"],
            index=0,
            key="lb_source"
        )

    # Apply source filter
    if lb_source_filter != "All":
        df_leaderboard = df_leaderboard[
            df_leaderboard["Source"].str.contains(lb_source_filter)
        ]

    # Apply sorting
    ascending = lb_sort_order == "Ascending"
    df_leaderboard = df_leaderboard.sort_values(
        lb_sort_by, ascending=ascending
    ).reset_index(drop=True)

    # Add rank column
    df_leaderboard.insert(0, "Rank", range(1, len(df_leaderboard) + 1))

    # Summary metrics
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric("Databases Shown", len(df_leaderboard))
    m_col2.metric("Total Train Examples", df_leaderboard["Train Examples"].sum())
    m_col3.metric("Total Dev Examples", df_leaderboard["Dev Examples"].sum())
    m_col4.metric(
        "Avg Examples/DB",
        f"{df_leaderboard['Total Examples'].mean():.1f}" if len(df_leaderboard) > 0 else "0"
    )

    st.dataframe(
        df_leaderboard,
        use_container_width=True,
        hide_index=True,
        height=500
    )

    # Visualization
    st.markdown("### 📊 Top 20 Databases by Example Count")

    top_20 = df_leaderboard.head(20).copy()
    if not top_20.empty:
        chart_data = top_20.set_index("Database")[["Train Examples", "Dev Examples"]]
        st.bar_chart(chart_data)

    # Download leaderboard
    csv_lb = df_leaderboard.to_csv(index=False)
    st.download_button(
        label="📥 Download Leaderboard as CSV",
        data=csv_lb,
        file_name="bird_database_example_leaderboard.csv",
        mime="text/csv"
    )


# -------------------------------------------
# FOOTER
# -------------------------------------------
st.divider()
st.markdown("""
<div style="text-align: center; color: #888; font-size: 0.85rem;">
    🐦 BIRD Benchmark SQL Explorer |
    🔒 Read-Only Mode |
    Built with Streamlit |
    <a href="https://bird-bench.github.io/" target="_blank">BIRD Benchmark</a>
</div>
""", unsafe_allow_html=True)