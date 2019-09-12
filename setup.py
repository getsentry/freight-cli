from setuptools import find_packages, setup

install_requires = ["click>=6.7,<7.0.0", "urllib3[secure]>=1.25,<1.26"]

setup(
    name="freight-cli",
    version="0.0.0",
    author="David Cramer",
    author_email="dcramer@gmail.com",
    url="https://github.com/getsentry/freight-cli",
    description="A command line interface to Freight",
    long_description=open("README.md").read(),
    packages=find_packages(),
    zip_safe=False,
    install_requires=install_requires,
    entry_points={"console_scripts": ["freight=freight_cli:cli"]},
    license="Apache 2.0",
    include_package_data=True,
    classifiers=[
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Operating System :: OS Independent",
        "Topic :: Software Development",
    ],
)
