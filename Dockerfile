FROM python:3.12

WORKDIR /app

RUN git clone https://github.com/webcloud7/wcs.pdfserver.git .

RUN python -m venv .
RUN /bin/bash -c "source bin/activate"

RUN ./bin/pip install -e . -c constraints.txt

EXPOSE 8040

# Run the application
CMD ["./bin/python", "pdfserver/server.py"]
