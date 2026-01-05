from setuptools import setup, find_packages

setup(
    name="rewards-service",
    version="1.0.0",
    description="Rewards service for Saint-Daniels project with SNAP-like eligibility enforcement",
    author="Saint-Daniels",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
    install_requires=[
        "fastapi>=0.104.1",
        "uvicorn[standard]>=0.24.0",
        "sqlalchemy>=2.0.23",
        "alembic>=1.12.1",
        "psycopg2-binary>=2.9.9",
        "pyjwt>=2.8.0",
        "cryptography>=41.0.7",
        "stripe>=7.7.0",
        "pydantic>=2.5.0",
        "pydantic-settings>=2.1.0",
        "structlog>=23.2.0",
    ],
)

