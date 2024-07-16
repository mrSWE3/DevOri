from setuptools import setup, find_packages

setup(
    name='your_package',  # Replace with your package's name
    version='0.1.0',  # Replace with your package's version
    packages=find_packages(),
    include_package_data=True,
    package_data={'your_package': ['py.typed']},  # Replace 'your_package' with your actual package name
)