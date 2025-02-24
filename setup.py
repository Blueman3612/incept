from setuptools import setup, find_packages

setup(
    name="incept",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "openai>=1.12.0",
        "python-dotenv>=1.0.0",
        "supabase>=2.3.0",
        "pytest>=7.4.4",
        "pytest-asyncio>=0.23.5"
    ]
) 