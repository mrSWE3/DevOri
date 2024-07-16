from setuptools import setup, find_packages

setup(
    name='DevOri',  # Replace with your package's name
    version='0.0.0',  # Replace with your package's version
    packages=find_packages(),
    include_package_data=True,
    package_data={'DevOri': ['py.typed']},  # Replace 'your_package' with your actual package name
)