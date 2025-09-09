from setuptools import setup, find_packages

setup(
    name="enhanced-link-tracker",
    version="2.0.0",
    description="Enhanced Link Tracker API with analytics and bulk processing",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "qrcode[pil]>=7.4.0",
        "python-multipart>=0.0.6"
    ],
)
