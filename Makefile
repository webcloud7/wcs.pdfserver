IMAGE_NAME ?= webcloud7/pdfserver

all: build

build:
	docker buildx build --platform linux/amd64,linux/arm64 --no-cache -t $(IMAGE_NAME):latest -t $(IMAGE_NAME):$(TAG) --push .
	git tag -a $(TAG) -m "Release version $(TAG)"
	git push --tags

.PHONY: all build
