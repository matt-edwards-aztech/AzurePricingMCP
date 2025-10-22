#!/usr/bin/env python3
"""
Setup script for Azure Retail Prices MCP Server
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="azure-pricing-mcp",
    version="1.0.0",
    author="Claude",
    author_email="support@anthropic.com",
    description="Model Context Protocol server for Azure retail pricing information",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/example/azure-pricing-mcp",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Office/Business :: Financial",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "azure-pricing-mcp=azure_pricing_mcp:main",
        ],
    },
    keywords="azure, pricing, mcp, model-context-protocol, cost-analysis, cloud-computing",
    project_urls={
        "Bug Reports": "https://github.com/example/azure-pricing-mcp/issues",
        "Source": "https://github.com/example/azure-pricing-mcp",
        "Documentation": "https://github.com/example/azure-pricing-mcp#readme",
    },
)
