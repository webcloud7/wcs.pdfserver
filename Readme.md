Description
===========

This is a simple weasyprint http server, which is meant to use internally only. 
There are no security features, so do not use it on the open internet.



Install for development
========================

```
python -m venv .
./bin/pip install -e . -c constraints.tx
```


Run
===

```
./bin/python pdfserver/server.py
```
