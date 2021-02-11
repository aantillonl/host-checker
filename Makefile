CONFIG_TARGETS=producer_config env

$(CONFIG_TARGETS):
	cp templates/$@ $@

config: $(CONFIG_TARGETS) certs

certs:
	mkdir -p certs

test:
	pytest --cov=host_metrics src/tests/

lint:
	pylint src/host_metrics/

build-image: Dockerfile config env certs
	docker build -t host-metrics .

start:
	docker-compose up

clean:
	rm $(CONFIG_TARGETS)