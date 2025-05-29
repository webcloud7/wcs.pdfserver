# WeasyPrint PDF Conversion Service

This is a simple HTTP server that uses WeasyPrint to convert HTML pages to PDF files. It is intended for internal use only and does not include security features, so do not expose it on the open internet.

## Features

- Convert HTML pages to PDF files
- Apply custom CSS stylesheets
- Asynchronous conversion with status polling
- Synchronous conversion for immediate download
- In-memory caching of generated PDFs with expiration

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv .
   ```
3. Activate the virtual environment:
   ```
   source bin/activate
   ```
4. Install the package and its dependencies:
   ```
   ./bin/pip install -e . -c constraints.txt
   ```

## Running the Server

Start the server with:
```
./bin/python pdfserver/server.py
```

By default, the server will listen on `0.0.0.0:8040`.

### Environment Variables

The following optional environment variables can be set:

- `REMOTE_USERNAME`: Username for basic authentication when fetching remote URLs
- `REMOTE_PASSWORD`: Password for basic authentication when fetching remote URLs

## API

### POST /convert

Asynchronously convert an HTML page to PDF.

Request body:
```json
{
  "url": "http://example.com/page.html",
  "css": ["http://example.com/styles.css"],
  "filename": "output.pdf"
}
```

- `url` (required): The URL of the HTML page to convert
- `css` (optional): An array of URLs for CSS stylesheets to apply
- `filename` (optional): The filename to use for the generated PDF. Defaults to `output.pdf`.

Response:
```json
{
  "uid": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "output.pdf",
  "status": "running"
}
```

- `uid`: A unique identifier for the PDF conversion task
- `filename`: The filename that will be used for the generated PDF
- `status`: The status of the conversion task (`running`, `completed`, or `failed`)

### POST /convert_sync

Synchronously convert an HTML page to PDF. The generated PDF will be returned in the response.

Request body: Same as `/convert`

Response: The generated PDF file

### GET /status/{pdf_id}

Get the status of an asynchronous PDF conversion task.

Response:
```json
{
  "uid": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "filename": "output.pdf",
  "timestamp": 1621234567.89,
  "message": "",
  "download": "/pdf/550e8400-e29b-41d4-a716-446655440000"
}
```

- `uid`: The unique identifier for the PDF conversion task
- `status`: The status of the conversion task (`running`, `completed`, or `failed`)
- `filename`: The filename of the generated PDF
- `timestamp`: The Unix timestamp when the task completed
- `message`: An error message if the task failed
- `download`: The URL to download the generated PDF (only present if status is `completed`)

### GET /pdf/{pdf_id}

Download a generated PDF file.

Response: The generated PDF file

### GET /

A simple welcome message.

### GET /health

A health check endpoint that returns "OK" if the server is running.

## Testing

Install test dependencies:
```
./bin/pip install -e ".[test]" -c constraints.txt
```

Run tests:
```
./bin/pytest
```

## Docker

You can also run the pdfserver as a Docker container.

### Building the Docker Image

To build the Docker image, run the following command in the root directory of the project:

```bash
docker build --no-cache -t pdfserver .
```

This will build the Docker image with the tag `pdfserver`.

### Running the Docker Container

To run the pdfserver as a Docker container, use the following command:

```bash
docker run -p 8040:8040 pdfserver
```

This will start the container and map port 8040 from the container to port 8040 on the host machine. You can then access the pdfserver at `http://localhost:8040`.

### Building and Pushing Multi-Architecture Images

The `Makefile` includes a `build` target that uses `docker buildx` to build and push multi-architecture images (amd64 and arm64) to a Docker registry.

To build and push the images, run:

```bash
make build TAG=v1.0.0
```

Replace `v1.0.0` with the desired tag for the release.

This command will build the images for amd64 and arm64 architectures, tag them with `latest` and the provided release tag, and push them to the configured Docker registry.

You can customize the image name and default tag by setting the `IMAGE_NAME` and `TAG` variables in the `Makefile` or by passing them as arguments:

```bash
make build v1.0.0 IMAGE_NAME=your-registry/your-image TAG=custom-tag
```

Make sure to log in to your Docker registry before running the `make build` command, so that the images can be pushed successfully.

## License

This project is licensed under the MIT License.
