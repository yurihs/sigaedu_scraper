from setuptools import setup


def readme():
    with open('README.rst') as f:
        return f.read()

setup(name='sigaedu_scraper',
      version='0.1',
      description='SIGA-EDU web app scraper',
      long_description=readme(),
      classifiers=[
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Natural Language :: Portuguese (Brazilian)'
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
      ],
      keywords='sigaedu sigaepct scraper',
      url='http://github.com/yurihs/sigaedu_scraper',
      author='yurihs',
      license='MIT',
      packages=['sigaedu_scraper'],
      install_requires=[
          'requests',
          'lxml'
      ],
      zip_safe=False)
