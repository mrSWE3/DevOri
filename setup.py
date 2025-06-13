from setuptools import setup, find_packages

setup(
    name='DevOri', 
    version='0.0.0',
    packages=find_packages(),
    include_package_data=True,
    package_data={'DevOri': ['py.typed']}, 
)