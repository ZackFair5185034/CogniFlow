"""CogniFlow - 通用视觉感知处理框架的安装配置。"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="engine",
    version="0.1.0",
    author="CogniFlow Team",
    description="通用视觉感知处理框架，集模型训练、模型测试、模型推理、规则引擎于一体",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/CogniFlow/CogniFlow",
    packages=find_packages(exclude=["tests", "examples", "docs"]),
    python_requires=">=3.8",
    install_requires=[
        "torch>=2.0.0",
        "torchvision>=0.15.0",
        "numpy>=1.21.0",
        "opencv-python>=4.8.0",
        "mss>=9.0.1",
        "pyautogui>=0.9.54",
        "pyyaml>=6.0",
        "gymnasium>=0.29.0",
        "tensorboard>=2.14.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
