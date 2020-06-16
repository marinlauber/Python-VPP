import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="Python-VPP",  # Replace with your own username
    version="0.0.2",
    author="Marin Lauber, Otto Vilani and Thomas Dickson",
    author_email="M.Lauber@soton.ac.uk",
    description="OOP Velocity Prediction Program",
    long_description=long_description,
    long_description_content_type="text/markdown",
    # url="https://github.com/marinlauber/OOpyPST",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.5",
)
