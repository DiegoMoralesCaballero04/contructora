## CONSTRUTECH-IA — Makefile shortcuts

.PHONY: up down logs migrate shell scrape health

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f django celery-worker

migrate:
	docker compose exec django python manage.py migrate

shell:
	docker compose exec django python manage.py shell

scrape:
	docker compose exec django python manage.py shell -c "from apps.scraping.tasks import scrape_licitaciones; scrape_licitaciones.delay()"

health:
	curl -s http://localhost:8000/api/v1/health/ | python -m json.tool

ps:
	docker compose ps

ollama-pull:
	docker compose exec ollama ollama pull llama3.2:3b

ollama-list:
	docker compose exec ollama ollama list

db-shell:
	docker compose exec postgres psql -U construtech -d construtech

mongo-shell:
	docker compose exec mongodb mongosh construtech_raw

superuser:
	docker compose exec django python manage.py createsuperuser

dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d django

dev-logs:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f django
