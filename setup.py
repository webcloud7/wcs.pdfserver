from setuptools import setup

setup(name='wcs.pdfserver',
      version='0.1',
      description='This is a simple weasyprint http server, which is meant to use internally only.',
      url='https://github.com/webcloud7/wcs.pdfserver',
      author='Mathias Leimgruber',
      author_email='m.leimgruber@webcloud7.ch',
      license='MIT',
      packages=['pdfserver'],
      install_requires=[
            'aiohttp',
            'weasyprint',
            'urllib3',
      ],
      zip_safe=False)
