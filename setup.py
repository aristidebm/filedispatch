from setuptools import setup, find_packages
from src import __version__

dependencies = [
    "aiohttp",
    "aiohttp-pydantic",
    "aiohttp-retry",
    "aiofiles",
    "aioftp",
    "aiosqlite",
    "pydantic",
    "pydantic-yaml",
    "watchfiles",
    "daemons",
    "mode-ng",
    "pypika",
]

with open("README.md", "r") as fp:
    readme = fp.read()


setup(
    name="filedispatch",
    version=__version__,
    description="Dispatch files to folder from a source folder",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/xxxx",  # FIXME: provide an url
    project_urls={
        "GitHub: repo": "https://github.com/xxxxx",  # FIXME: provide an url
    },
    download_url="https://github.com/xxxx",  # FIXME: provide an url,
    author="BAMAZI Aristide",
    author_email="bamaziaristide@gmail.com",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "filedispatch = src.cli:main",
        ],
    },
    install_requires=dependencies,
    # see: https://pypi.python.org/pypi?:action=list_classifiers
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Environment :: No Input/Output (Daemon)",
        "Environment :: Web Environment",
        "Intended Audience :: Customer Service",
        "Intended Audience :: Other Audience",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX",
        "Operating System :: POSIX :: Linux",
        "Topic :: System :: Monitoring",
        "Topic :: System :: Networking",
        "Topic :: Utilities",
        "Framework :: AsyncIO",
    ],
)
