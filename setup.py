from setuptools import setup, find_packages

setup(
    name="surveillance-video-event",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "kafka-python",
        "pymongo",
        "python-dotenv",
        "pandas",
        "fastapi",
        "uvicorn",
        "python-dateutil",
        "pytest",
        "streamlit",
        "opencv-python",
        "numpy",
        "plotly",
    ],
) 