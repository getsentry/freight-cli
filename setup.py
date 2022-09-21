from setuptools import find_packages, setup

install_requires = ["click>=7", "urllib3[secure]>=1.25,<1.26"]

setup(
    name="freight-cli",
    version="0.0.0",
    author="David Cramer",
    author_email="dcramer@gmail.com",
    url="https://github.com/getsentry/freight-cli",
    description="A command line interface to Freight",
    long_description=open("README.md").read(),
    install_requires=install_requires,
    entry_points={"console_scripts": ["freight=freight_cli:cli"]},
    py_modules=["freight_cli"],
    license="Apache 2.0",
    license_file='LICENSE',
    classifiers=[
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Operating System :: OS Independent",
        "Topic :: Software Development",
    ],
)
