THIS_FILE := $(lastword $(MAKEFILE_LIST))
.PHONY: build run

build:
	docker compose -f docker-compose.yml up --build -d
run:
	docker compose -f docker-compose.yml up -d
