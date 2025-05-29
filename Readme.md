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

## License

This project is licensed under the MIT License.
