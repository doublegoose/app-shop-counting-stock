.ONESHELL:


PROJECT_NAME=app-shop-counting-shop


build:
	@echo
	docker build -t $(PROJECT_NAME) .


run: build
	@echo
	docker run -d --network host -v .:/app --name $(PROJECT_NAME) $(PROJECT_NAME)


stop:
	docker stop $(PROJECT_NAME)


clean: stop
	docker rm $(PROJECT_NAME)
	docker rmi $(PROJECT_NAME):latest
	docker builder prune --all -f

