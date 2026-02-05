"""Setup script for FinanceBot CLI."""

from setuptools import setup, find_packages

setup(
    name='financebot',
    version='1.0.0',
    description='Financial transaction processing toolkit with AI categorization',
    author='James Chin Moody',
    py_modules=[
        'financebot_cli',
        'transaction_normalizer',
        'transaction_categorizer',
        'transaction_reconciler',
        'transaction_reporter'
    ],
    install_requires=[
        'pandas>=1.3.0',
        'anthropic>=0.40.0',
        'python-dotenv>=0.19.0',
        'openpyxl>=3.0.0',
        'click>=8.0.0'
    ],
    entry_points={
        'console_scripts': [
            'financebot=financebot_cli:main',
        ],
    },
    python_requires='>=3.9',
)
