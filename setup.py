from setuptools import setup, find_packages

setup(
    name="fiber",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "rich>=10.0.0",
        "requests>=2.25.0",
        "python-dotenv>=0.19.0",
        "prompt_toolkit>=3.0.0",
        "lxml>=4.9.0",
        "psutil>=5.8.0"
    ],
    entry_points={
        "console_scripts": [
            "fiber=fiber.cli:main",
        ],
    },
    python_requires=">=3.8",
)
