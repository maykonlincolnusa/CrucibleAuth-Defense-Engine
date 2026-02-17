install:
	pip install -e .[dev]

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

migrate:
	python scripts/migrate.py

seed:
	python scripts/seed_synthetic_data.py

train:
	python scripts/train_bootstrap.py

test:
	pytest -q

load-test:
	locust -f load/locustfile.py --headless --host http://localhost:8000 --users 100 --spawn-rate 10 --run-time 2m

tf-init:
	terraform -chdir=infra/terraform/aws init

tf-plan:
	terraform -chdir=infra/terraform/aws plan

tf-apply:
	terraform -chdir=infra/terraform/aws apply
