import setuptools

with open('README.md') as f:
    long_description = f.read()

setuptools.setup(
    name='ergo',
    license='MIT',
    version='0.0.6',
    author='Elias Tarhini',
    author_email='eltrhn@gmail.com',
    url='https://github.com/eltrhn/ergo',
    description='argparse, take 99999',
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords='argparse argument parsing',
    python_requires='~=3.5',
    packages=setuptools.find_packages(),
    classifiers=(
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ),
)
