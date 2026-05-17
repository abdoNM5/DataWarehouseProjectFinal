"""Airflow DAG that triggers each source collector."""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from ingestion.collectors.france_travail_collector import FranceTravailCollector
from ingestion.collectors.glassdoor_collector import GlassdoorCollector
from ingestion.collectors.indeed_collector import IndeedCollector
from ingestion.collectors.linkedin_collector import LinkedInCollector
from ingestion.collectors.remotive_collector import RemotiveCollector
from ingestion.collectors.storage import save_records
from ingestion.collectors.the_muse_collector import TheMuseCollector


def _collector_task(collector_cls, **context):
	since = context.get("data_interval_start")
	collector = collector_cls(since=since)
	records = list(collector.run())
	output = save_records(collector.source, records)
	print(f"{collector.source}: {len(records)} records saved to {output}")


default_args = {
	"owner": "data-platform",
	"depends_on_past": False,
	"retries": 1,
	"retry_delay": timedelta(minutes=5),
}


with DAG(
	dag_id="job_ingestion_dag",
	default_args=default_args,
	start_date=datetime(2024, 1, 1),
	schedule="*/30 * * * *",
	catchup=False,
) as dag:
	indeed = PythonOperator(
		task_id="ingest_indeed",
		python_callable=_collector_task,
		op_kwargs={"collector_cls": IndeedCollector},
	)

	linkedin = PythonOperator(
		task_id="ingest_linkedin",
		python_callable=_collector_task,
		op_kwargs={"collector_cls": LinkedInCollector},
	)

	france_travail = PythonOperator(
		task_id="ingest_france_travail",
		python_callable=_collector_task,
		op_kwargs={"collector_cls": FranceTravailCollector},
	)

	the_muse = PythonOperator(
		task_id="ingest_the_muse",
		python_callable=_collector_task,
		op_kwargs={"collector_cls": TheMuseCollector},
	)

	remotive = PythonOperator(
		task_id="ingest_remotive",
		python_callable=_collector_task,
		op_kwargs={"collector_cls": RemotiveCollector},
	)

	glassdoor = PythonOperator(
		task_id="ingest_glassdoor",
		python_callable=_collector_task,
		op_kwargs={"collector_cls": GlassdoorCollector},
	)

	[indeed, linkedin, france_travail, the_muse, remotive, glassdoor]
