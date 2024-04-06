import streamlit as st
import os
from utils.postgres_etl import PostgresETL
from utils.database_orchestrator import DatabaseOrchestrator
from utils.s3_utils import S3Manager
from utils.st_utils import initialize_st_page
from dotenv import load_dotenv

load_dotenv()

initialize_st_page("ETL Page", layout="wide", icon="📦")

st.subheader("Connect via S3")
col1, col2, col3, col4 = st.columns(4)
with col1:
    bucket_name = st.text_input("Bucket name", os.environ.get("S3_BUCKET_NAME"))
with col2:
    access_key_id = st.text_input("Access Key ID", os.environ.get("S3_ACCESS_KEY"), type="password")
with col3:
    secret_access_key = st.text_input("Secret Access Key", os.environ.get("S3_SECRET_KEY"), type="password")
with col4:
    region_name = st.text_input("Region Name", "ap-northeast-1")

replace = st.checkbox("Replace existing databases", False)

if st.button("Fetch databases"):
    s3_manager = S3Manager(bucket_name=bucket_name,
                           access_key_id=access_key_id,
                           secret_access_key=secret_access_key,
                           region_name=region_name)
    dbs = s3_manager.list_all_sqlite_files()
    n_files = len(dbs)
    file_counter = 0
    with st.spinner("Fetching databases... Please don't close this page"):
        with st.expander("Check status"):
            st.write(f"{n_files} databases were founded. Starting download...")
            for db in dbs:
                file_counter += 1
                st.info(s3_manager.download_file(db, replace))
                st.write(f"{(100 * file_counter / n_files):.2f} % Completed")

st.divider()

st.subheader("Wrap up in Postgres")
st.markdown("#### Select databases")
db_orchestrator = DatabaseOrchestrator(root_folder="data/s3/data/uploaded")  # TODO: Remove after debugging

with st.expander("Database status report"):
    st.dataframe(db_orchestrator.status_report, use_container_width=True)

sqlite_dbs = st.multiselect("SQLite databases", [db.db_path for db in db_orchestrator.healthy_dbs])
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    host = st.text_input("Host", "localhost")
with col2:
    port = st.number_input("Port", value=5480, step=1)
with col3:
    db_name = st.text_input("DB Name", "postgres")
with col4:
    db_user = st.text_input("DB User", "postgres")
with col5:
    db_password = st.text_input("DB Password", os.environ.get("POSTGRES_PASSWORD"), type="password")
clean_tables = st.checkbox("Clean tables before ingesting", False)
postgres_etl = PostgresETL(host=host,
                           port=port,
                           database=db_name,
                           user=db_user,
                           password=db_password)

st.markdown("#### Load databases")

if st.button("Load into Postgres database"):
    tables_dict = db_orchestrator.get_tables(sqlite_dbs)
    postgres_etl.create_tables()
    if clean_tables:
        postgres_etl.clean_tables()
    postgres_etl.insert_data(tables_dict)

